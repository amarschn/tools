/* Use the production Python functions; this worker contains no second solver. */
let python;
async function initialize() {
    try {
        importScripts('https://cdn.jsdelivr.net/pyodide/v0.25.1/full/pyodide.js');
        python = await loadPyodide({indexURL:'https://cdn.jsdelivr.net/pyodide/v0.25.1/full/'});
        const response = await fetch(new URL('../../../pycalcs/stability.py', self.location.href));
        if (!response.ok) throw new Error('The stability solver could not load.');
        python.runPython(await response.text());
        python.runPython('import json');
        self.postMessage({type:'ready'});
    } catch (error) {
        self.postMessage({type:'fatal', message:error.message});
    }
}
self.onmessage = ({data}) => {
    if (!python || data.type !== 'solve') return;
    try {
        python.globals.set('_lab_inputs', JSON.stringify(data.inputs));
        const result = python.runPython(
            '_lab_equilibrium = evaluate_stability(**json.loads(_lab_inputs))\n' +
            'json.dumps({"equilibrium": _lab_equilibrium, "free_body": free_body_diagram(_lab_equilibrium)}, allow_nan=False)'
        );
        self.postMessage({type:'result', revision:data.revision, result:JSON.parse(result)});
    } catch (error) {
        self.postMessage({type:'error', revision:data.revision, message:error.message});
    }
};
initialize();
