"""Reproduce pinned browser export dependencies without a runtime package manager.

Run from any directory. --archives accepts an existing directory containing
replicad.tgz, oc.tgz and pdf.tgz; every archive is integrity checked before use.
Only the selected single-thread runtime and PDF bundle are installed.
"""

import argparse
import base64
import hashlib
import io
import tarfile
import urllib.request
from pathlib import Path

PACKAGES = {
    "replicad": (
        "replicad",
        "1.1.0",
        "TJw32OTe6+HASPpfrLEjYUI66VvSmYC2F/za4iDFWIWo4RVYbiA62dmUbXUp8ZEqkIS//jK6TqrxnmFqX6cbkA==",
    ),
    "oc": (
        "replicad-opencascadejs",
        "1.1.0",
        "s0KHR5V+ivsOE4nZXfuoW70lW0/rldkb3ZDY34LpXOQRFLQN5qVydQm3BRo7boZPdFkkAZBERJ+NzB0DYxrivw==",
    ),
    "pdf": (
        "pdf-lib",
        "1.17.1",
        "V/mpyJAoTsN4cnP31vc0wfNA1+p20evqqnap0KLoRUN0Yk/p3wN52DOEsL4oBFcLdb76hlpKPtzJIgo67j/XLw==",
    ),
}

NOTICES = {
    "flatbush-ISC.txt": "https://unpkg.com/flatbush@4.5.0/LICENSE",
    "flatqueue-ISC.txt": "https://unpkg.com/flatqueue@2.0.3/LICENSE",
    "opentype-MIT.txt": "https://unpkg.com/opentype.js@1.3.4/LICENSE",
    "pako-MIT.txt": "https://unpkg.com/pako@1.0.11/LICENSE",
    "tslib-license.txt": "https://unpkg.com/tslib@1.14.1/LICENSE.txt",
    "upng-MIT.txt": "https://unpkg.com/@pdf-lib/upng@1.0.1/LICENSE",
    "standard-fonts-MIT.txt": "https://unpkg.com/@pdf-lib/standard-fonts@1.0.0/LICENSE.md",
    "OCCT-exception.txt": "https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/b8f597c677811d1f9f4d8a97f5ae2825c0353a42/OCCT_LGPL_EXCEPTION.txt",
    "OCCT-license.txt": "https://raw.githubusercontent.com/Open-Cascade-SAS/OCCT/b8f597c677811d1f9f4d8a97f5ae2825c0353a42/LICENSE_LGPL_21.txt",
    "rapidjson-license.txt": "https://raw.githubusercontent.com/Tencent/rapidjson/24b5e7a8b27f42fa16b96fc70aade9106cf7102f/license.txt",
    "freetype-license.txt": "https://raw.githubusercontent.com/freetype/freetype/de8b92dd7ec634e9e2b25ef534c54a3537555c11/docs/FTL.TXT",
    "emscripten-license.txt": "https://raw.githubusercontent.com/emscripten-core/emscripten/5.0.1/LICENSE",
    "cad-source-deps.json": "https://raw.githubusercontent.com/taucad/opencascade.js/ebd263f1/DEPS.json",
}


def main():
    """Download, check npm SHA-512 integrity, and copy an allowlist of assets."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path)
    parser.add_argument(
        "--notices-only",
        action="store_true",
        help="Download the pinned upstream license texts and source manifest.",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "tools/thread-visualizer-sizer/vendor"
    if args.notices_only:
        target = root / "notices"
        target.mkdir(parents=True, exist_ok=True)
        for filename, url in NOTICES.items():
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
            if not data or data.startswith(b"404"):
                raise ValueError("Missing notice: " + url)
            (target / filename).write_bytes(data)
            print(filename, len(data), "bytes")
        return
    for key, (name, version, integrity) in PACKAGES.items():
        archive = (
            (args.archives / (key + ".tgz")).read_bytes()
            if args.archives
            else urllib.request.urlopen(
                f"https://registry.npmjs.org/{name}/-/{name}-{version}.tgz", timeout=120
            ).read()
        )
        if base64.b64encode(hashlib.sha512(archive).digest()).decode() != integrity:
            raise ValueError("Integrity mismatch: " + name)
        target = root / (name + "-" + version)
        target.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
            for member in package.getmembers():
                filename = Path(member.name).name
                include = filename in ("LICENSE", "LICENSE.md")
                include |= (
                    key == "replicad"
                    and member.name.startswith("package/dist/")
                    and filename.endswith(".js")
                )
                include |= key == "oc" and filename in (
                    "replicad_single.js",
                    "replicad_single.wasm",
                )
                include |= key == "pdf" and filename == "pdf-lib.esm.min.js"
                if include and member.isfile():
                    data = package.extractfile(member).read()
                    (target / filename).write_bytes(data)
                    print(
                        f"{target.relative_to(root)} / {filename}: {len(data):,} bytes"
                    )


if __name__ == "__main__":
    main()
