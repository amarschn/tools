const { JSDOM } = require('jsdom');

(async () => {
    try {
        console.log("Loading jsdom...");
        const dom = await JSDOM.fromURL('http://localhost:8000/tools/rotor-balance/', {
            runScripts: "dangerously",
            resources: "usable",
            pretendToBeVisual: true
        });

        dom.window.console.log = (...args) => console.log('LOG:', ...args);
        dom.window.console.error = (...args) => console.error('ERR:', ...args);
        dom.window.console.warn = (...args) => console.warn('WARN:', ...args);

        // Wait a few seconds for Pyodide to load and run
        console.log("Waiting for Pyodide...");
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        const btnText = dom.window.document.getElementById('calculate-btn').textContent;
        console.log("Button text:", btnText);
        
        const results = dom.window.document.getElementById('results-display').innerHTML;
        console.log("Results HTML:", results);
        
    } catch (e) {
        console.error("Test failed:", e);
    }
})();
