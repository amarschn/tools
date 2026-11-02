#!/usr/bin/env python3
"""Derive HVAC design conditions from public NOAA hourly observations.

Reads NOAA ISD-Lite hourly files (US government data, no copyright) and writes
the climate tables used by tools/hvac-load-calculator/:

  data/stations.json   design temperatures, humidity, degree days, and hourly
                       temperature bins for each usable station
  data/zips.txt        US ZIP code centroids from the Census ZCTA gazetteer

The statistics follow the definitions in ASHRAE Handbook Fundamentals Chapter
14: a 99% heating dry bulb is the temperature exceeded in 99% of the hours of
the year, a 1% cooling dry bulb is exceeded in 1% of them, and the mean
coincident wet bulb is the average wet bulb during hours near that dry bulb.
No ASHRAE table is read or copied; every number is computed from observations.

Run from the repository root. Downloads are cached outside the repository:

    python3 scripts/build_hvac_climate.py --cache /path/to/cache
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import datetime as dt
import gzip
import io
import json
import math
import statistics
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "tools" / "hvac-load-calculator" / "data"
HISTORY_URL = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"
# The www.ncei.noaa.gov/pub path now returns an HTML file browser with status 200,
# so the archive is read from NOAA's public bucket on AWS Open Data.
LITE_URL = "https://noaa-isd-pds.s3.amazonaws.com/isd-lite/data/{y}/{id}-{y}.gz"
ZCTA_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2023_Gazetteer/2023_Gaz_zcta_national.zip"
)
FIRST_YEAR, LAST_YEAR = 2011, 2025
MIN_GOOD_YEARS = 8
MIN_HOURS_PER_YEAR = 7000
MIN_STATIONS = 500
OUTLIER_F = 65.0
COUNTRIES = {"US", "CA", "RQ", "VQ", "GQ", "AQ"}
BIN_LOW_F, BIN_WIDTH_F = -40, 5
USER_AGENT = "transparent.tools climate builder (https://transparent.tools)"


def fetch(url: str, path: Path, attempts: int = 4) -> bool:
    """Download url to path once. Returns False for a missing file.

    A gzip target must start with the gzip magic bytes, because hosts can answer
    a data URL with an HTML page and status 200.
    """
    must_be_gzip = path.suffix == ".gz"
    if path.exists():
        if path.stat().st_size == 0:
            return False
        if not must_be_gzip or path.open("rb").read(2) == b"\x1f\x8b":
            return True
        path.unlink()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read()
            if must_be_gzip and data[:2] != b"\x1f\x8b":
                raise OSError(f"{url} did not return gzip data")
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_bytes(data)
            tmp.replace(path)
            return True
        except urllib.error.HTTPError as err:
            if err.code == 404:
                path.write_bytes(b"")
                return False
            time.sleep(2 ** attempt)
        except OSError:
            time.sleep(2 ** attempt)
    return False


def pws_kpa(t_c: float) -> float:
    """Saturation vapor pressure over water or ice (Magnus form), kPa."""
    if t_c >= 0:
        return 0.61094 * math.exp(17.625 * t_c / (243.04 + t_c))
    return 0.61121 * math.exp(22.587 * t_c / (273.86 + t_c))


def wet_bulb_c(t_c: float, td_c: float, p_kpa: float) -> float:
    """Thermodynamic wet bulb from dry bulb and dew point, by bisection."""
    pw = pws_kpa(td_c)
    w = 0.621945 * pw / (p_kpa - pw)
    low, high = td_c, t_c
    for _ in range(30):
        wb = 0.5 * (low + high)
        ps = pws_kpa(wb)
        ws = 0.621945 * ps / (p_kpa - ps)
        w_calc = ((2501 - 2.326 * wb) * ws - 1.006 * (t_c - wb)) / (
            2501 + 1.86 * t_c - 4.186 * wb
        )
        if w_calc > w:
            high = wb
        else:
            low = wb
    return 0.5 * (low + high)


def to_f(t_c: float) -> float:
    return t_c * 9 / 5 + 32


def percentile(sorted_values: list[float], fraction: float) -> float:
    """Linear-interpolated percentile of an already sorted list."""
    position = fraction * (len(sorted_values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    return sorted_values[lower] + (position - lower) * (
        sorted_values[upper] - sorted_values[lower]
    )


def read_year(path: Path, tz_hours: float) -> list[tuple]:
    """Parse one ISD-Lite file into (local datetime, T °C, Td °C or None)."""
    rows = []
    raw = gzip.decompress(path.read_bytes()).decode("ascii", "ignore")
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[4] == "-9999":
            continue
        try:
            stamp = dt.datetime(
                int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
            ) + dt.timedelta(hours=tz_hours)
        except ValueError:
            continue
        rows.append(
            (stamp, int(parts[4]) / 10, None if parts[5] == "-9999" else int(parts[5]) / 10)
        )
    return rows


def summarize(station: dict, cache: Path) -> dict | None:
    """Compute design statistics for one station, or None if data are thin."""
    sid = station["id"]
    tz = station["lon"] / 15.0  # solar-time offset, enough to bracket a day
    p_kpa = 101.325 * (1 - 2.25577e-5 * station["elev_m"]) ** 5.2559
    good_years = []
    rows = []
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        path = cache / f"{sid}-{year}.gz"
        if not path.exists() or path.stat().st_size == 0:
            continue
        try:
            year_rows = read_year(path, tz)
        except (OSError, EOFError, ValueError):
            continue
        months = {r[0].month for r in year_rows}
        if len(year_rows) >= MIN_HOURS_PER_YEAR and len(months) == 12:
            good_years.append(year)
            rows.extend(year_rows)
    if len(good_years) < MIN_GOOD_YEARS:
        return None

    # Some stations log bursts of bad readings, such as -76 °F in San Diego. Drop
    # any hour more than 65 °F from the median for its calendar month, a margin
    # wide enough to keep real arctic outbreaks and chinook swings.
    by_month: dict = {}
    for stamp, t_c, _ in rows:
        by_month.setdefault(stamp.month, []).append(to_f(t_c))
    medians = {month: statistics.median(values) for month, values in by_month.items()}
    rows = [r for r in rows if abs(to_f(r[1]) - medians[r[0].month]) <= OUTLIER_F]

    temps = sorted(to_f(r[1]) for r in rows)
    n_years = len(good_years)
    t996, t99 = percentile(temps, 0.004), percentile(temps, 0.01)
    t1, t04 = percentile(temps, 0.99), percentile(temps, 0.996)

    # Mean coincident wet bulb: hours within 1 °F of the 1% dry bulb.
    near = [r for r in rows if r[2] is not None and abs(to_f(r[1]) - t1) <= 1.0]
    if len(near) < 20:
        near = [r for r in rows if r[2] is not None and abs(to_f(r[1]) - t1) <= 2.5]
    if len(near) < 10:
        return None
    mcwb = statistics.fmean(to_f(wet_bulb_c(r[1], r[2], p_kpa)) for r in near)

    # 1% dew point with its mean coincident dry bulb, for dehumidification.
    with_dew = [r for r in rows if r[2] is not None]
    dews = sorted(to_f(r[2]) for r in with_dew)
    dp1 = percentile(dews, 0.99)
    dp_near = [to_f(r[1]) for r in with_dew if abs(to_f(r[2]) - dp1) <= 1.0]
    mcdb = statistics.fmean(dp_near) if dp_near else t1

    # Monthly means, degree days, daily range in the hottest month.
    days: dict = {}
    for stamp, t_c, _ in rows:
        days.setdefault(stamp.date(), []).append(to_f(t_c))
    month_means: dict = {m: [] for m in range(1, 13)}
    hdd = [0.0] * 12
    cdd = [0.0] * 12
    ranges: dict = {m: [] for m in range(1, 13)}
    for day, values in days.items():
        if len(values) < 18:
            continue
        mean_t = statistics.fmean(values)
        month_means[day.month].append(mean_t)
        ranges[day.month].append(max(values) - min(values))
    if not all(month_means[m] for m in month_means):
        return None
    days_in_month = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    for m in range(1, 13):
        hdd[m - 1] = days_in_month[m - 1] * statistics.fmean(
            max(0.0, 65 - t) for t in month_means[m]
        )
        cdd[m - 1] = days_in_month[m - 1] * statistics.fmean(
            max(0.0, t - 65) for t in month_means[m]
        )
    monthly = [statistics.fmean(month_means[m]) for m in range(1, 13)]
    hottest = max(range(1, 13), key=lambda m: monthly[m - 1])
    daily_range = statistics.fmean(ranges[hottest])

    # The cold a heat pump must survive in an ordinary year: the median across
    # years of each year's fifth-coldest hour. Stray bad readings cannot set it.
    temps_by_year: dict = {}
    for stamp, t_c, _ in rows:
        temps_by_year.setdefault(stamp.year, []).append(to_f(t_c))
    lows = [
        sorted(temps_by_year[y])[4] for y in good_years if len(temps_by_year.get(y, [])) > 4
    ]

    # Average hours per year in each 5 °F bin; scale for missing observations.
    counts: dict = {}
    for t_f in temps:
        index = math.floor((t_f - BIN_LOW_F) / BIN_WIDTH_F)
        counts[index] = counts.get(index, 0) + 1
    scale = 8766.0 * n_years / len(temps) / n_years
    first, last = min(counts), max(counts)
    bins = [round(counts.get(i, 0) * scale) for i in range(first, last + 1)]

    return {
        "id": sid,
        "n": station["name"],
        "s": station["state"],
        "c": station["ctry"],
        "la": round(station["lat"], 3),
        "lo": round(station["lon"], 3),
        "el": round(station["elev_m"] * 3.28084),
        "yrs": n_years,
        "h996": round(t996, 1),
        "h99": round(t99, 1),
        "c1": round(t1, 1),
        "c04": round(t04, 1),
        "wb": round(mcwb, 1),
        "dp": round(dp1, 1),
        "dpdb": round(mcdb, 1),
        "dr": round(daily_range, 1),
        "hm": hottest,
        "lo_typ": round(statistics.median(lows), 1),
        "tm": [round(t, 1) for t in monthly],
        "hdd": [round(v) for v in hdd],
        "cdd": [round(v) for v in cdd],
        "b0": BIN_LOW_F + first * BIN_WIDTH_F,
        "b": bins,
    }


def load_stations(cache: Path) -> list[dict]:
    history = cache / "isd-history.csv"
    if not fetch(HISTORY_URL, history):
        sys.exit("Could not download the NOAA station list.")
    stations = []
    with history.open(newline="", encoding="utf-8", errors="ignore") as handle:
        for row in csv.DictReader(handle):
            try:
                lat, lon, elev = float(row["LAT"]), float(row["LON"]), float(row["ELEV(M)"])
            except (ValueError, KeyError):
                continue
            usaf, wban = row["USAF"], row["WBAN"]
            if (
                row["CTRY"] not in COUNTRIES
                or usaf == "999999"
                or lat == 0
                or lon == 0
                or not (-999 < elev < 6000)
                or row["BEGIN"] > f"{FIRST_YEAR + 6}0101"
                or row["END"] < f"{LAST_YEAR - 2}0101"
            ):
                continue
            stations.append(
                {
                    "id": f"{usaf}-{wban}",
                    "name": row["STATION NAME"].strip().title(),
                    "state": row["STATE"].strip(),
                    "ctry": row["CTRY"].strip(),
                    "lat": lat,
                    "lon": lon,
                    "elev_m": elev,
                }
            )
    return stations


def build_zips(cache: Path) -> int:
    """Write 'ZIP lat lon' rows, delta-free and compact, from the gazetteer."""
    archive = cache / "zcta.zip"
    if not fetch(ZCTA_URL, archive):
        sys.exit("Could not download the Census ZCTA gazetteer.")
    with zipfile.ZipFile(archive) as bundle:
        name = next(n for n in bundle.namelist() if n.endswith(".txt"))
        text = io.TextIOWrapper(bundle.open(name), encoding="utf-8", errors="ignore")
        reader = csv.reader(text, delimiter="\t")
        next(reader)
        rows = []
        for row in reader:
            cells = [c.strip() for c in row]
            rows.append(f"{cells[0]} {float(cells[-2]):.2f} {float(cells[-1]):.2f}")
    rows.sort()
    (OUT_DIR / "zips.txt").write_text("\n".join(rows) + "\n", encoding="ascii")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=32)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"ZIP centroids: {build_zips(args.cache)}", flush=True)
    stations = load_stations(args.cache)
    print(f"Candidate stations: {len(stations)}", flush=True)

    jobs = [
        (LITE_URL.format(y=y, id=s["id"]), args.cache / f"{s['id']}-{y}.gz")
        for s in stations
        for y in range(FIRST_YEAR, LAST_YEAR + 1)
    ]
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for done, _ in enumerate(pool.map(lambda j: fetch(*j), jobs), 1):
            if done % 2000 == 0:
                print(f"  downloaded {done}/{len(jobs)}", flush=True)

    with cf.ProcessPoolExecutor() as pool:
        results = pool.map(summarize, stations, [args.cache] * len(stations), chunksize=8)
        summaries = [r for r in results if r]
    if len(summaries) < MIN_STATIONS:
        sys.exit(f"Only {len(summaries)} usable stations, so the old table was kept.")
    summaries.sort(key=lambda s: s["id"])
    years_used = max(s["yrs"] for s in summaries)
    payload = {
        "source": "NOAA ISD-Lite hourly observations",
        "period": f"{FIRST_YEAR}-{LAST_YEAR}",
        "most_years_used": years_used,
        "bin_width_f": BIN_WIDTH_F,
        "stations": summaries,
    }
    out = OUT_DIR / "stations.json"
    out.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(summaries)} stations, {out.stat().st_size / 1e3:.0f} kB", flush=True)


if __name__ == "__main__":
    main()
