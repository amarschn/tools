# Prototype dependencies

JSXGraph 1.13.3 is vendored here from its npm distribution under the MIT license.
Keep `LICENSE.MIT` with `jsxgraphcore.js`.

Source: `https://cdn.jsdelivr.net/npm/jsxgraph@1.13.3/distrib/jsxgraphcore.js`

SHA-256: `4e196b10dc77e22ec0eda897e0271636edf8dadd91d76cc2cf2e136c61c35537`

Three.js 0.180.0 and OrbitControls are loaded from the repository's existing
`tools/thread-visualizer-sizer/vendor/three-0.180.0/` files, with their existing
MIT license. This experiment reuses those bytes. If adopted by the tipping
tool, promote the dependency into a shared vendor directory and update both
tools together.
