"""Extract normalized bearing rows from official NTN catalog section PDFs.

This maintainer script is intentionally not part of the runtime dependency set.
It requires ``pypdf`` and the five section PDFs downloaded from NTN catalog
No. 2203/E. The generated JSON remains reviewable and is validated by the
repository test suite before it can be used by the browser tool.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader

SOURCE_URLS = {
    "deep_groove_ball": "https://www.ntnglobal.com/en/products/catalog/pdf/2203E_b02.pdf",
    "angular_contact_ball": "https://www.ntnglobal.com/en/products/catalog/pdf/2203E_b04.pdf",
    "cylindrical_roller": "https://www.ntnglobal.com/en/products/catalog/pdf/2203E_b06.pdf",
    "tapered_roller": "https://www.ntnglobal.com/en/products/catalog/pdf/2203E_b07.pdf",
    "spherical_roller": "https://www.ntnglobal.com/en/products/catalog/pdf/2203E_b08.pdf",
}


def _page_lines(path: Path, first: int, last: int) -> Iterable[tuple[int, list[str]]]:
    """Yield one-indexed page numbers and extracted lines for an inclusive range."""
    reader = PdfReader(path)
    for page_number in range(first, last + 1):
        text = reader.pages[page_number - 1].extract_text() or ""
        yield page_number, text.splitlines()


def _speed(tokens: list[str], index: int) -> tuple[float, int]:
    """Parse a speed whose thousands group may be a separate PDF text token."""
    if (
        index + 1 < len(tokens)
        and re.fullmatch(r"\d{1,2}", tokens[index])
        and re.fullmatch(r"\d{3}", tokens[index + 1])
    ):
        return float(tokens[index] + tokens[index + 1]), index + 2
    return float(tokens[index]), index + 1


def _rating(tokens: list[str], index: int) -> tuple[float, int]:
    """Parse a kN rating whose leading thousands digit may be separated."""
    if (
        index + 1 < len(tokens)
        and re.fullmatch(r"\d", tokens[index])
        and re.fullmatch(r"\d{3}", tokens[index + 1])
    ):
        return float(tokens[index] + tokens[index + 1]), index + 2
    return float(tokens[index]), index + 1


def _skip_rating(tokens: list[str], index: int) -> int:
    """Advance over a numeric/grouped rating or an unavailable-value mark."""
    try:
        _, next_index = _rating(tokens, index)
        return next_index
    except ValueError:
        return index + 1


def _join_thousands(text: str) -> str:
    """Preserve PDF tokens; known grouped numbers are parsed by ``_speed``."""
    return text


def _numbers(tokens: Iterable[str]) -> list[float]:
    """Return tokens that are plain decimal numbers."""
    values = []
    for token in tokens:
        try:
            values.append(float(token))
        except ValueError:
            continue
    return values


def _clean_designation(token: str) -> str:
    """Remove PDF extraction marks while preserving catalog punctuation."""
    match = re.search(r"(?:4T-)?[A-Z0-9][A-Z0-9/.-]*", token)
    if not match:
        raise ValueError(f"Cannot normalize designation token {token!r}")
    return match.group(0)


def _standard_metric_bore(designation: str) -> float | None:
    """Return the nominal bore encoded by a standard two-digit bore code."""
    slash_match = re.search(r"/(\d+)$", designation)
    if slash_match:
        return float(slash_match.group(1))
    clean = re.sub(r"(?:JRX3|JRX|JR|EA|B)$", "", designation)
    match = re.search(r"(\d{2})$", clean)
    if not match:
        return None
    code = int(match.group(1))
    special = {0: 10.0, 1: 12.0, 2: 15.0, 3: 17.0}
    return special.get(code, code * 5.0)


def _record(
    designation: str,
    bearing_type: str,
    bore: float,
    outside_diameter: float,
    width: float,
    dynamic_kn: float,
    static_kn: float,
    grease_speed: float,
    oil_speed: float,
    mass: float,
    page: int,
    **factors: Any,
) -> dict[str, Any]:
    """Build one normalized catalog record in runtime SI units."""
    return {
        "designation": designation,
        "bearing_type": bearing_type,
        "bore_mm": bore,
        "outside_diameter_mm": outside_diameter,
        "width_mm": width,
        "dynamic_rating_n": dynamic_kn * 1000.0,
        "static_rating_n": static_kn * 1000.0,
        "grease_speed_rpm": grease_speed,
        "oil_speed_rpm": oil_speed,
        "mass_kg": mass,
        "manufacturer": "NTN",
        "catalog": "Ball and Roller Bearings, No. 2203/E",
        "source_url": SOURCE_URLS[bearing_type],
        "source_pdf_page": page,
        **factors,
    }


def extract_deep_groove(
    path: Path, maximum_bore: float = 200.0
) -> list[dict[str, Any]]:
    """Extract standard open deep-groove rows from catalog PDF pages B-22–B-39."""
    designation_pattern = re.compile(
        r"^(?:67\d{2}|68\d{2}(?:JR)?|69\d{2}(?:JRX)?|160\d{2}(?:JRX)?|"
        r"60\d{2}(?:JRX)?|62\d{2}|63\d{2}|64\d{2}|(?:60|62|63)/\d+)$"
    )
    rows = []
    for page, lines in _page_lines(path, 4, 12):
        header = next(line for line in lines if re.search(r"d \d+[–-]\d+ mm", line))
        bore = float(re.search(r"d (\d+)", header).group(1))
        for line in lines:
            stripped = _join_thousands(line.strip())
            if re.fullmatch(r"\d{1,3}", stripped) and int(stripped) >= bore:
                bore = float(stripped)
                continue
            stripped = re.sub(r"\b(60|62|63) / (\d+)\b", r"\1/\2", stripped)
            tokens = stripped.split()
            candidates = [
                (i, token, _standard_metric_bore(token))
                for i, token in enumerate(tokens)
                if designation_pattern.match(token)
            ]
            designation_choice = next(
                (
                    item
                    for item in candidates
                    if item[2] == bore
                    or (item[2] is not None and tokens and tokens[0] == f"{item[2]:g}")
                ),
                None,
            )
            designation_index = designation_choice[0] if designation_choice else None
            if designation_index is None:
                continue
            if designation_choice[2] is not None:
                bore = designation_choice[2]
            left = tokens[:designation_index]
            if len(left) > 8:
                try:
                    if not 10 <= float(left[7]) <= 18 and 10 <= float(left[8]) <= 18:
                        bore = float(left[0])
                        left = left[1:]
                except ValueError:
                    pass
            if len(left) < 10 or bore > maximum_bore:
                continue
            try:
                outside_diameter = float(left[0])
                width = float(left[1])
                dynamic_kn, field_index = _rating(left, 4)
                static_kn, field_index = _rating(left, field_index)
                field_index = _skip_rating(left, field_index)
                f0 = float(left[field_index])
                grease_speed, speed_index = _speed(left, field_index + 1)
                oil_speed, _ = _speed(left, speed_index)
                mass = _numbers(tokens[designation_index + 1 :])[-1]
            except (ValueError, IndexError):
                continue
            if outside_diameter <= bore or not 10 <= f0 <= 18:
                continue
            rows.append(
                _record(
                    tokens[designation_index],
                    "deep_groove_ball",
                    bore,
                    outside_diameter,
                    width,
                    dynamic_kn,
                    static_kn,
                    grease_speed,
                    oil_speed,
                    mass,
                    page,
                    f0=f0,
                    contact_angle_deg=0.0,
                    axial_capability="both_directions_moderate",
                )
            )
    return rows


def extract_angular_contact(
    path: Path, maximum_bore: float = 200.0
) -> list[dict[str, Any]]:
    """Extract single-row 30° and 40° angular-contact rows."""
    pattern = re.compile(r"^(?:79|70|72|73)\d{2}B?$")
    rows = []
    for page, lines in _page_lines(path, 3, 8):
        header = next(line for line in lines if re.search(r"d \d+[–-]\d+ mm", line))
        bore = float(re.search(r"d (\d+)", header).group(1))
        for line in lines:
            tokens = _join_thousands(line.strip()).split()
            if len(tokens) == 1 and re.fullmatch(r"\d{1,3}", tokens[0]):
                bore = float(tokens[0])
                continue
            designation_index = next(
                (i for i, token in enumerate(tokens) if pattern.match(token)), None
            )
            if designation_index is None:
                continue
            left = tokens[:designation_index]
            designation = tokens[designation_index]
            encoded_bore = _standard_metric_bore(designation)
            if encoded_bore is not None:
                bore = encoded_bore
            if left and float(left[0]) == bore and len(left) >= 11:
                left = left[1:]
            if len(left) < 10 or bore > maximum_bore:
                continue
            try:
                dynamic_kn, field_index = _rating(left, 5)
                static_kn, field_index = _rating(left, field_index)
                field_index = _skip_rating(left, field_index)
                grease_speed, index = _speed(left, field_index)
                oil_speed, _ = _speed(left, index)
                right_numbers = _numbers(tokens[designation_index + 1 :])
                mass = right_numbers[1]
                is_40_degree = designation.endswith("B")
                rows.append(
                    _record(
                        designation,
                        "angular_contact_ball",
                        bore,
                        float(left[0]),
                        float(left[1]),
                        dynamic_kn,
                        static_kn,
                        grease_speed,
                        oil_speed,
                        mass,
                        page,
                        e=1.14 if is_40_degree else 0.80,
                        y2=0.57 if is_40_degree else 0.76,
                        y0=0.26 if is_40_degree else 0.33,
                        contact_angle_deg=40.0 if is_40_degree else 30.0,
                        axial_capability="one_direction_pair_required",
                    )
                )
            except (ValueError, IndexError):
                continue
    return rows


def extract_cylindrical(
    path: Path, maximum_bore: float = 200.0
) -> list[dict[str, Any]]:
    """Extract the first-listed NU design from standard cylindrical tables."""
    rows = []
    for page, lines in _page_lines(path, 4, 12):
        header = next(line for line in lines if re.search(r"d \d+[–-]\d+ mm", line))
        bore = float(re.search(r"d (\d+)", header).group(1))
        for line in lines:
            tokens = _join_thousands(line.strip()).split()
            if len(tokens) == 1 and re.fullmatch(r"\d{1,3}", tokens[0]):
                bore = float(tokens[0])
                continue
            designation_index = next(
                (i for i, token in enumerate(tokens) if re.search(r"NU\d", token)),
                None,
            )
            if designation_index is None:
                continue
            left = tokens[:designation_index]
            designation = _clean_designation(tokens[designation_index])
            encoded_bore = _standard_metric_bore(designation)
            if encoded_bore is not None:
                bore = encoded_bore
            if left and float(left[0]) == bore and len(left) >= 10:
                left = left[1:]
            if len(left) < 9 or bore > maximum_bore:
                continue
            try:
                dynamic_kn, field_index = _rating(left, 4)
                static_kn, field_index = _rating(left, field_index)
                field_index = _skip_rating(left, field_index)
                grease_speed, index = _speed(left, field_index)
                oil_speed, _ = _speed(left, index)
                masses = _numbers(tokens[designation_index + 1 :])[-2:]
                rows.append(
                    _record(
                        designation,
                        "cylindrical_roller",
                        bore,
                        float(left[0]),
                        float(left[1]),
                        dynamic_kn,
                        static_kn,
                        grease_speed,
                        oil_speed,
                        masses[0],
                        page,
                        design="NU",
                        axial_capability="none_floating",
                    )
                )
            except (ValueError, IndexError):
                continue
    return rows


def extract_tapered(path: Path, maximum_bore: float = 200.0) -> list[dict[str, Any]]:
    """Extract metric single-row tapered roller rows and their load factors."""
    rows = []
    for page, lines in _page_lines(path, 5, 14):
        header = next(line for line in lines if re.search(r"d \d+[–-]\d+ mm", line))
        bore = float(re.search(r"d (\d+)", header).group(1))
        for line in lines:
            tokens = _join_thousands(line.strip()).split()
            if len(tokens) == 1 and re.fullmatch(r"\d{1,3}", tokens[0]):
                bore = float(tokens[0])
                continue
            if len(tokens) < 13:
                continue
            offset = 0
            try:
                if float(tokens[0]) < float(tokens[1]):
                    bore = float(tokens[0])
                    offset = 1
                left = tokens[offset:]
                if bore > maximum_bore:
                    continue
                dynamic_kn, field_index = _rating(left, 6)
                static_kn, field_index = _rating(left, field_index)
                field_index = _skip_rating(left, field_index)
                grease_speed, index = _speed(left, field_index)
                oil_speed, designation_index = _speed(left, index)
                designation = _clean_designation(left[designation_index])
                if not re.search(
                    r"(?:3(?:02|03|13|20|22|23|29|30|31|32))", designation
                ):
                    continue
                tail = _numbers(left[designation_index + 1 :])
                e_value, y2, y0, mass = tail[-4:]
                rows.append(
                    _record(
                        designation,
                        "tapered_roller",
                        bore,
                        float(left[0]),
                        float(left[1]),
                        dynamic_kn,
                        static_kn,
                        grease_speed,
                        oil_speed,
                        mass,
                        page,
                        e=e_value,
                        y2=y2,
                        y0=y0,
                        contact_angle_deg=None,
                        axial_capability="one_direction_pair_required",
                    )
                )
            except (ValueError, IndexError):
                continue
    return rows


def extract_spherical(path: Path, maximum_bore: float = 200.0) -> list[dict[str, Any]]:
    """Extract cylindrical-bore spherical roller rows and load factors."""
    rows = []
    for page, lines in _page_lines(path, 5, 15):
        header = next(
            line for line in lines if re.search(r"d [\d ]+[–-][\d ]+ mm", line)
        )
        bore = float(re.search(r"d ([\d ]+)[–-]", header).group(1).replace(" ", ""))
        if bore > maximum_bore:
            continue
        for line in lines:
            tokens = _join_thousands(line.strip()).split()
            if (
                len(tokens) == 1
                and re.fullmatch(r"\d{1,4}", tokens[0])
                and float(tokens[0]) >= bore
            ):
                bore = float(tokens[0])
                continue
            if len(tokens) < 13:
                continue
            try:
                offset = 0
                if float(tokens[0]) < float(tokens[1]):
                    bore = float(tokens[0])
                    offset = 1
                left = tokens[offset:]
                if bore > maximum_bore:
                    continue
                dynamic_kn, field_index = _rating(left, 5)
                static_kn, field_index = _rating(left, field_index)
                field_index = _skip_rating(left, field_index)
                grease_speed, index = _speed(left, field_index)
                oil_speed, designation_index = _speed(left, index)
                designation = _clean_designation(left[designation_index])
                if not re.match(r"(?:2(?:13|22|23|30|31|32|39|40|41))", designation):
                    continue
                tail = _numbers(left[designation_index + 1 :])
                e_value, y1, y2, y0, mass, _ = tail[-6:]
                rows.append(
                    _record(
                        designation,
                        "spherical_roller",
                        bore,
                        float(left[0]),
                        float(left[1]),
                        dynamic_kn,
                        static_kn,
                        grease_speed,
                        oil_speed,
                        mass,
                        page,
                        e=e_value,
                        y1=y1,
                        y2=y2,
                        y0=y0,
                        axial_capability="both_directions",
                    )
                )
            except (ValueError, IndexError):
                continue
    return rows


def main() -> None:
    """Extract, validate, checksum, and write the normalized catalog JSON."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--deep", type=Path, required=True)
    parser.add_argument("--angular", type=Path, required=True)
    parser.add_argument("--cylindrical", type=Path, required=True)
    parser.add_argument("--tapered", type=Path, required=True)
    parser.add_argument("--spherical", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum-bore", type=float, default=200.0)
    args = parser.parse_args()

    rows = [
        *extract_deep_groove(args.deep, args.maximum_bore),
        *extract_angular_contact(args.angular, args.maximum_bore),
        *extract_cylindrical(args.cylindrical, args.maximum_bore),
        *extract_tapered(args.tapered, args.maximum_bore),
        *extract_spherical(args.spherical, args.maximum_bore),
    ]
    unique = {}
    for row in rows:
        if not (
            5 <= row["bore_mm"] <= args.maximum_bore
            and row["bore_mm"] < row["outside_diameter_mm"]
            and 0 < row["width_mm"] < row["outside_diameter_mm"]
            and row["dynamic_rating_n"] > 0
            and row["static_rating_n"] > 0
            and 0.1 <= row["dynamic_rating_n"] / row["static_rating_n"] <= 10.0
            and row["grease_speed_rpm"] > 0
            and row["oil_speed_rpm"] > 0
            and row["mass_kg"] > 0
        ):
            raise ValueError(f"Implausible extracted row: {row}")
        key = (row["manufacturer"], row["designation"])
        if key in unique:
            raise ValueError(f"Duplicate catalog designation: {key}")
        unique[key] = row
    rows = sorted(
        unique.values(),
        key=lambda row: (
            row["bore_mm"],
            row["bearing_type"],
            row["outside_diameter_mm"],
            row["designation"],
        ),
    )
    encoded_rows = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    payload = {
        "schema_version": 2,
        "catalog_version": "NTN-2203E-2024-v2",
        "manufacturer": "NTN",
        "catalog": "Ball and Roller Bearings, No. 2203/E",
        "maximum_bore_mm": args.maximum_bore,
        "record_count": len(rows),
        "sha256": hashlib.sha256(encoded_rows).hexdigest(),
        "source_urls": SOURCE_URLS,
        "records": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} sourced records to {args.output}")


if __name__ == "__main__":
    main()
