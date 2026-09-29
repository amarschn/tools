# Browser export libraries and source

This tool uses facilities provided by Open CASCADE Technology. Its CAD kernel
is a separately loaded, unmodified single-thread WebAssembly library. You may
replace or rebuild these library files; there is no integrity lock or server
dependency preventing use of a modified build.

| Component | Pinned release | License / notice |
|---|---|---|
| Replicad | 1.1.0 | [MIT](replicad-1.1.0/LICENSE) |
| Replicad OpenCascade.js | 1.1.0, single-thread | [LGPL 2.1](replicad-opencascadejs-1.1.0/LICENSE) |
| Open CASCADE Technology | 8.0.1 | [LGPL 2.1](notices/OCCT-license.txt) with [OCCT exception](notices/OCCT-exception.txt) |
| pdf-lib | 1.17.1 | [MIT](pdf-lib-1.17.1/LICENSE.md) |
| PDF.js (legacy browser build) | 6.3.289 | [Apache 2.0](pdfjs-dist-6.3.289/LICENSE) |
| Three.js and OrbitControls | 0.180.0 | [MIT](three-0.180.0/LICENSE) |

Bundled JavaScript dependencies retain their notices:
[Flatbush](notices/flatbush-ISC.txt), [Flatqueue](notices/flatqueue-ISC.txt),
[OpenType.js](notices/opentype-MIT.txt), [pako](notices/pako-MIT.txt),
[tslib](notices/tslib-license.txt), [UPNG](notices/upng-MIT.txt), and
[standard fonts](notices/standard-fonts-MIT.txt).
CAD build dependency notices include [RapidJSON](notices/rapidjson-license.txt),
[FreeType](notices/freetype-license.txt), and [Emscripten](notices/emscripten-license.txt).

## Source and rebuilding

The published library files are unmodified except for OrbitControls' `three`
import, rewritten to the local `./three.module.min.js` path by the installer.
The worker, viewer and model construction code live one directory above this file.

- [Replicad source at e4b05f67](https://github.com/sgenoud/replicad/tree/e4b05f67dc4e2393a876ce8c5064a9c93db05bf1), including `packages/replicad-opencascadejs/build-source` and its build scripts.
- [OpenCascade.js source/build tooling at ebd263f1](https://github.com/taucad/opencascade.js/tree/ebd263f1). The Replicad package uses `ghcr.io/taucad/opencascade.js:canary-ebd263f1-single-threaded`.
- [OCCT source at b8f597c6](https://github.com/Open-Cascade-SAS/OCCT/tree/b8f597c677811d1f9f4d8a97f5ae2825c0353a42). The [upstream dependency manifest](notices/cad-source-deps.json) pins the C++ kernel, FreeType, RapidJSON and Emscripten build inputs.
- [pdf-lib 1.17.1 source](https://github.com/Hopding/pdf-lib/tree/v1.17.1).
- [PDF.js 6.3.289 source](https://github.com/mozilla/pdf.js/tree/v6.3.289). Only the preview library and worker are loaded; the tool does not accept uploaded PDFs.
- [Three.js 0.180.0 source](https://github.com/mrdoob/three.js/tree/0af9729d0c143a86a1d725d6e2c3ad83301f3f34). The section cap in `thread-cad-viewer.js` adapts the [clipping-stencil example](https://github.com/mrdoob/three.js/blob/0af9729d0c143a86a1d725d6e2c3ad83301f3f34/examples/webgl_clipping_stencil.html), under the same MIT license and copyright notice linked above.

To reproduce the static assets from the repository root:

```sh
python3 scripts/vendor_thread_exports.py
python3 scripts/vendor_thread_exports.py --notices-only
```

The installer checks the npm archives against pinned SHA-512 values before
copying its allowlisted runtime files. `--archives PATH` allows offline reuse
of the downloaded archives (`replicad`, `oc`, `pdf`, `pdfjs`, and `three`).
`--package three` installs just the 3D viewer; `--package pdfjs` installs the PDF
preview dependency. No package manager runs on the public site.
To build a modified kernel, use the pinned Replicad build scripts and the
single-thread image above, then replace `replicad_single.js` and
`replicad_single.wasm` together. Keep their exports compatible with Replicad.
The LGPL library remains independently replaceable; generated STEP files are
the user's geometry, not copies of the CAD kernel.
