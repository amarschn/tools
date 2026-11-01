"""Reviewed October 2026 wood stiffness and strength along the grain.

Every wood species already had density, bending strength and bending modulus from
USDA Wood Handbook Table 5-3a. This batch adds three properties the same chapter
supports, so wood can sit on the main Ashby charts. Earlier records stay
byte-for-byte: each species gains values through a new reference record beside it.
The tables are transcriptions of the pinned chapter. See
docs/wood-2026-10-batch-review.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from builder.import_reference_tables import obs, record  # noqa: E402

DATE = "2026-10-31"
LEDGER = "wood-2026-10.json"
SOURCE = "usda-wood-mechanical"
FILENAME = "usda-wood-mechanical.pdf"
SHA256 = "7f4b2a07f15f8eee6413b1432ef98963f0fd341a97aef770762bebc167f236a2"

SHEAR_CORRECTION = 1.10
GREEN_TO_12_PERCENT = {"hardwood": 1.32, "softwood": 1.13}

# Table 5-3a, 12% moisture rows: material, PDF page, printed row, bending modulus
# in MPa, compression parallel to grain in kPa.
TABLE_5_3A = [
    ("wood-red-alder", 4, "Alder, red", "9,500", "40,100"),
    ("wood-white-ash", 4, "Ash: White", "12,000", "51,100"),
    ("wood-american-beech", 4, "Beech, American", "11,900", "50,300"),
    ("wood-yellow-birch", 4, "Birch: Yellow", "13,900", "56,300"),
    ("wood-black-cherry", 4, "Cherry, black", "10,300", "49,000"),
    ("wood-western-redcedar", 7, "Cedar: Western redcedar", "7,700", "31,400"),
    ("wood-coast-douglas-fir", 7, "Douglas-fir: Coast", "13,400", "49,900"),
    ("wood-balsam-fir", 7, "Fir: Balsam", "10,000", "36,400"),
    ("wood-eastern-white-pine", 7, "Pine: Eastern white", "8,500", "33,100"),
    ("wood-loblolly-pine", 7, "Pine: Loblolly", "12,300", "49,200"),
    ("wood-black-ash", 4, "Ash: Black", "11,000", "41,200"),
    ("wood-blue-ash", 4, "Ash: Blue", "9,700", "48,100"),
    ("wood-green-ash", 4, "Ash: Green", "11,400", "48,800"),
    ("wood-oregon-ash", 4, "Ash: Oregon", "9,400", "41,600"),
    ("wood-bigtooth-aspen", 4, "Aspen: Bigtooth", "9,900", "36,500"),
    ("wood-quaking-aspen", 4, "Aspen: Quaking", "8,100", "29,300"),
    ("wood-american-basswood", 4, "Basswood, American", "10,100", "32,600"),
    ("wood-paper-birch", 4, "Birch: Paper", "11,000", "39,200"),
    ("wood-sweet-birch", 4, "Birch: Sweet", "15,000", "58,900"),
    ("wood-butternut", 4, "Butternut", "8,100", "36,200"),
    ("wood-american-chestnut", 4, "Chestnut, American", "8,500", "36,700"),
    ("wood-balsam-poplar", 4, "Cottonwood: Balsam poplar", "7,600", "27,700"),
    ("wood-black-cottonwood", 4, "Cottonwood: Black", "8,800", "31,000"),
    ("wood-eastern-cottonwood", 4, "Cottonwood: Eastern", "9,400", "33,900"),
    ("wood-american-elm", 4, "Elm: American", "9,200", "38,100"),
    ("wood-rock-elm", 4, "Elm: Rock", "10,600", "48,600"),
    ("wood-slippery-elm", 4, "Elm: Slippery", "10,300", "43,900"),
    ("wood-hackberry", 4, "Hackberry", "8,200", "37,500"),
    ("wood-bitternut-hickory", 5, "Hickory, pecan: Bitternut", "12,300", "62,300"),
    ("wood-nutmeg-hickory", 5, "Hickory, pecan: Nutmeg", "11,700", "47,600"),
    ("wood-pecan", 5, "Hickory, pecan: Pecan", "11,900", "54,100"),
    ("wood-water-hickory", 5, "Hickory, pecan: Water", "13,900", "59,300"),
    ("wood-mockernut-hickory", 5, "Hickory, true: Mockernut", "15,300", "61,600"),
    ("wood-pignut-hickory", 5, "Hickory, true: Pignut", "15,600", "63,400"),
    ("wood-shagbark-hickory", 5, "Hickory, true: Shagbark", "14,900", "63,500"),
    ("wood-shellbark-hickory", 5, "Hickory, true: Shellbark", "13,000", "55,200"),
    ("wood-black-locust", 5, "Locust, black", "14,100", "70,200"),
    ("wood-cucumbertree", 5, "Magnolia: Cucumbertree", "12,500", "43,500"),
    ("wood-southern-magnolia", 5, "Magnolia: Southern", "9,700", "37,600"),
    ("wood-bigleaf-maple", 5, "Maple: Bigleaf", "10,000", "41,000"),
    ("wood-black-maple", 5, "Maple: Black", "11,200", "46,100"),
    ("wood-red-maple", 5, "Maple: Red", "11,300", "45,100"),
    ("wood-silver-maple", 5, "Maple: Silver", "7,900", "36,000"),
    ("wood-sugar-maple", 5, "Maple: Sugar", "12,600", "54,000"),
    ("wood-black-oak", 5, "Oak, red: Black", "11,300", "45,000"),
    ("wood-cherrybark-oak", 5, "Oak, red: Cherrybark", "15,700", "60,300"),
    ("wood-laurel-oak", 5, "Oak, red: Laurel", "11,700", "48,100"),
    ("wood-northern-red-oak", 5, "Oak, red: Northern red", "12,500", "46,600"),
    ("wood-pin-oak", 5, "Oak, red: Pin", "11,900", "47,000"),
    ("wood-scarlet-oak", 5, "Oak, red: Scarlet", "13,200", "57,400"),
    ("wood-southern-red-oak", 5, "Oak, red: Southern red", "10,300", "42,000"),
    ("wood-water-oak", 5, "Oak, red: Water", "13,900", "46,700"),
    ("wood-willow-oak", 6, "Oak, red: Willow", "13,100", "48,500"),
    ("wood-bur-oak", 6, "Oak, white: Bur", "7,100", "41,800"),
    ("wood-chestnut-oak", 6, "Oak, white: Chestnut", "11,000", "47,100"),
    ("wood-live-oak", 6, "Oak, white: Live", "13,700", "61,400"),
    ("wood-overcup-oak", 6, "Oak, white: Overcup", "9,800", "42,700"),
    ("wood-post-oak", 6, "Oak, white: Post", "10,400", "45,300"),
    ("wood-swamp-chestnut-oak", 6, "Oak, white: Swamp chestnut", "12,200", "50,100"),
    ("wood-swamp-white-oak", 6, "Oak, white: Swamp white", "14,100", "59,300"),
    ("wood-white-oak", 6, "Oak, white: White", "12,300", "51,300"),
    ("wood-sassafras", 6, "Sassafras", "7,700", "32,800"),
    ("wood-sweetgum", 6, "Sweetgum", "11,300", "43,600"),
    ("wood-american-sycamore", 6, "Sycamore, American", "9,800", "37,100"),
    ("wood-black-tupelo", 6, "Tupelo: Black", "8,300", "38,100"),
    ("wood-water-tupelo", 6, "Tupelo: Water", "8,700", "40,800"),
    ("wood-black-walnut", 6, "Walnut, black", "11,600", "52,300"),
    ("wood-black-willow", 6, "Willow, black", "7,000", "28,300"),
    ("wood-yellow-poplar", 6, "Yellow-poplar", "10,900", "38,200"),
    ("wood-baldcypress", 6, "Baldcypress", "9,900", "43,900"),
    ("wood-atlantic-white-cedar", 6, "Cedar: Atlantic white", "6,400", "32,400"),
    ("wood-eastern-redcedar", 6, "Cedar: Eastern redcedar", "6,100", "41,500"),
    ("wood-incense-cedar", 6, "Cedar: Incense", "7,200", "35,900"),
    ("wood-northern-white-cedar", 6, "Cedar: Northern white", "5,500", "27,300"),
    ("wood-port-orford-cedar", 7, "Cedar: Port-Orford", "11,700", "43,100"),
    ("wood-yellow-cedar", 7, "Cedar: Yellow", "9,800", "43,500"),
    ("wood-california-red-fir", 7, "Fir: California red", "10,300", "37,600"),
    ("wood-grand-fir", 7, "Fir: Grand", "10,800", "36,500"),
    ("wood-noble-fir", 7, "Fir: Noble", "11,900", "42,100"),
    ("wood-pacific-silver-fir", 7, "Fir: Pacific silver", "12,100", "44,200"),
    ("wood-subalpine-fir", 7, "Fir: Subalpine", "8,900", "33,500"),
    ("wood-white-fir", 7, "Fir: White", "10,300", "40,000"),
    ("wood-eastern-hemlock", 7, "Hemlock: Eastern", "8,300", "37,300"),
    ("wood-mountain-hemlock", 7, "Hemlock: Mountain", "9,200", "44,400"),
    ("wood-western-hemlock", 7, "Hemlock: Western", "11,300", "49,000"),
    ("wood-western-larch", 7, "Larch, western", "12,900", "52,500"),
    ("wood-jack-pine", 7, "Pine: Jack", "9,300", "39,000"),
    ("wood-lodgepole-pine", 7, "Pine: Lodgepole", "9,200", "37,000"),
    ("wood-longleaf-pine", 7, "Pine: Longleaf", "13,700", "58,400"),
    ("wood-pitch-pine", 7, "Pine: Pitch", "9,900", "41,000"),
    ("wood-pond-pine", 8, "Pine: Pond", "12,100", "52,000"),
    ("wood-ponderosa-pine", 8, "Pine: Ponderosa", "8,900", "36,700"),
    ("wood-red-pine", 8, "Pine: Red", "11,200", "41,900"),
    ("wood-sand-pine", 8, "Pine: Sand", "9,700", "47,700"),
    ("wood-shortleaf-pine", 8, "Pine: Shortleaf", "12,100", "50,100"),
    ("wood-slash-pine", 8, "Pine: Slash", "13,700", "56,100"),
    ("wood-spruce-pine", 8, "Pine: Spruce", "8,500", "39,000"),
    ("wood-sugar-pine", 8, "Pine: Sugar", "8,200", "30,800"),
    ("wood-virginia-pine", 8, "Pine: Virginia", "10,500", "46,300"),
    ("wood-western-white-pine", 8, "Pine: Western white", "10,100", "34,700"),
    ("wood-redwood", 8, "Redwood: Old-growth", "9,200", "42,400"),
    ("wood-black-spruce", 8, "Spruce: Black", "11,100", "41,100"),
    ("wood-engelmann-spruce", 8, "Spruce: Engelmann", "8,900", "30,900"),
    ("wood-red-spruce", 8, "Spruce: Red", "11,400", "38,200"),
    ("wood-sitka-spruce", 8, "Spruce: Sitka", "10,800", "38,700"),
    ("wood-white-spruce", 8, "Spruce: White", "9,600", "35,700"),
    ("wood-tamarack", 8, "Tamarack", "11,300", "49,400"),
]

# Table 5-7 (PDF page 26), tensile strength parallel to grain in kPa, tested green.
TABLE_5_7 = [
    ("wood-american-beech", "Beech, American", "86,200"),
    ("wood-sugar-maple", "Maple, sugar", "108,200"),
    ("wood-overcup-oak", "Oak: Overcup", "77,900"),
    ("wood-pin-oak", "Oak: Pin", "112,400"),
    ("wood-balsam-poplar", "Poplar, balsam", "51,000"),
    ("wood-sweetgum", "Sweetgum", "93,800"),
    ("wood-black-willow", "Willow, black", "73,100"),
    ("wood-yellow-poplar", "Yellow-poplar", "109,600"),
    ("wood-baldcypress", "Baldcypress", "58,600"),
    ("wood-port-orford-cedar", "Cedar: Port-Orford", "78,600"),
    ("wood-western-redcedar", "Cedar: Western redcedar", "45,500"),
    ("wood-california-red-fir", "Fir: California red", "77,900"),
    ("wood-pacific-silver-fir", "Fir: Pacific silver", "95,100"),
    ("wood-western-hemlock", "Hemlock, western", "89,600"),
    ("wood-western-larch", "Larch, western", "111,700"),
    ("wood-eastern-white-pine", "Pine: Eastern white", "73,100"),
    ("wood-loblolly-pine", "Pine: Loblolly", "80,000"),
    ("wood-ponderosa-pine", "Pine: Ponderosa", "57,900"),
    ("wood-virginia-pine", "Pine: Virginia", "94,500"),
    ("wood-engelmann-spruce", "Spruce: Engelmann", "84,800"),
    ("wood-sitka-spruce", "Spruce: Sitka", "59,300"),
]

EXCLUDED = [
    {"id": "table-5-7-cedar-elm", "reason": "Cedar elm has no Table 5-3a row, so the catalog has no such species and no density to pair with."},
    {"id": "table-5-7-douglas-fir-interior-north", "reason": "The catalog keeps Coast Douglas-fir; a regional population is not that material."},
    {"id": "table-5-7-redwood", "reason": "Table 5-7 prints virgin and young growth. The catalog keeps old-growth redwood, and the chapter does not state that the two old-growth labels are the same population."},
    {"id": "table-5-3a-perpendicular-to-grain", "reason": "Compression and tension across the grain are a different direction and are not comparable with the isotropic values on the same axes."},
]


def import_wood(source_dir: Path) -> tuple[list, dict]:
    """Build one along-the-grain reference record per species."""
    if hashlib.sha256((source_dir / FILENAME).read_bytes()).hexdigest() != SHA256:
        raise ValueError(f"{FILENAME}: source differs from the reviewed snapshot")
    existing = {r["id"]: r for r in json.loads((ROOT / "curated/materials.json").read_text())["materials"]}
    tensile = {mid: (row, raw) for mid, row, raw in TABLE_5_7}
    records = []
    for mid, page, row, modulus, compression in TABLE_5_3A:
        grade = existing[mid]
        subgroup = grade["family"][1]
        where = f"Table 5-3a, {row}, 12% MC"
        along = {"moisture_content_1": 0.12, "orientation": "L"}
        values = [
            obs("youngs_modulus", modulus, SOURCE, page, where, "Static bending modulus of elasticity, plus 10%",
                method="Bending modulus raised 10% to remove shear deflection, as Table 5-3a footnote c and Table 5-1 footnote a direct",
                conditions={**along, "material_state": "Small clear specimens; 12% moisture content. Approximates the along-grain modulus EL from the printed bending modulus."},
                basis="computed", factor=SHEAR_CORRECTION * 1e6, raw_unit="MPa, bending, before the 10% correction"),
            obs("compressive_strength", compression, SOURCE, page, where, "Compression parallel to grain",
                method="Maximum crushing strength, Table 5-3a footnote a",
                conditions={**along, "material_state": "Small clear specimens; 12% moisture content; loaded along the grain."},
                basis="reference", factor=1000, raw_unit="kPa"),
        ]
        if mid in tensile:
            printed, raw = tensile.pop(mid)
            factor = GREEN_TO_12_PERCENT[subgroup]
            values.append(
                obs("tensile_strength", raw, SOURCE, 26, f"Table 5-7, {printed}", "Tensile strength parallel to grain, tested green",
                    method=f"Green value raised {round((factor - 1) * 100)}% to 12% moisture, the {subgroup} average in Table 5-7 footnote a",
                    conditions={**along, "material_state": "Clear, straight-grained specimens tested green. The 12% value is the chapter's average adjustment, not a measurement on this species."},
                    basis="computed", factor=factor * 1000, raw_unit="kPa, green, before the moisture adjustment"))
        records.append(record(mid + "-along-grain", grade["name"] + " — along the grain", "variant", mid, grade["family"],
                              "Along-grain stiffness and strength from Wood Handbook Chapter 5.",
                              aliases=[], condition="supplier reference state", observations=values))
    if tensile:
        raise ValueError(f"Table 5-7 rows with no species: {sorted(tensile)}")
    ledger = {
        "date": DATE,
        "added_materials": 0,
        "added_observations": sum(len(r["observations"]) for r in records),
        "material_ids": [],
        "authored_ids": [r["id"] for r in records],
        "extended_material_ids": [r["parent_id"] for r in records],
        "source_ids": [SOURCE],
        "excluded": EXCLUDED,
    }
    return records, ledger


def main() -> None:
    """Rebuild only this batch, preserving every earlier curated record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    records, ledger = import_wood(args.source_dir)
    path = ROOT / "curated/materials.json"
    data = json.loads(path.read_text())
    remaining = {r["id"]: r for r in records}
    data["materials"] = [remaining.pop(r["id"], r) for r in data["materials"]] + list(remaining.values())
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    ledger_path = ROOT / "curated" / LEDGER
    ledger_text = json.dumps(ledger, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if path.read_text() != text or ledger_path.read_text() != ledger_text:
            raise ValueError("Curated data differs from the reviewed wood batch")
    else:
        path.write_text(text)
        ledger_path.write_text(ledger_text)
    print(f"{'Checked' if args.check else 'Applied'} {len(records)} species and {ledger['added_observations']} observations.")


if __name__ == "__main__":
    main()
