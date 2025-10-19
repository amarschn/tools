const loadingMessage = document.getElementById('loading');
const appDiv = document.getElementById('app');
const calcSelect = document.getElementById('calculation-select');
const calcName = document.getElementById('calc-name');
const calcDescription = document.getElementById('calc-description');
const latexOverviewDiv = document.getElementById('latex-overview');
const inputForm = document.getElementById('input-form');
const calculateBtn = document.getElementById('calculate-btn');
const resultsDiv = document.getElementById('results');
const handcalcsOutputDiv = document.getElementById('handcalcs-output');
const errorMessageDiv = document.getElementById('error-message');

let pyodide = null;
let handCalcsPy = null; // To hold the Python module proxy
let calculationManifest = {};
let currentCalcId = null;

// --- Pyodide Initialization ---
async function loadPyodideAndPackages() {
    try {
        pyodide = await loadPyodide();
        console.log("Pyodide loaded.");

        // Mount current directory to access local files
        // This might be necessary if running locally or in specific environments
        // await pyodide.mountNativeFS('.', '/mnt');

        // Install required Python packages
        await pyodide.loadPackage(["micropip"]);
        const micropip = pyodide.pyimport("micropip");
        await micropip.install(['pint', 'handcalcs', 'numpy', 'pandas', 'sympy']); // Add common handcalcs dependencies
        console.log("Required packages installed.");

        // Load the Python calculation file
        const response = await fetch('hand_calcs.py');
        const pythonCode = await response.text();
        handCalcsPy = pyodide.runPython(pythonCode); // Execute the script
                                                      // Now functions are in global scope

        // Fetch the calculation manifest from Python
        calculationManifest = await pyodide.globals.get('get_calculation_manifest')();
        console.log("Calculation Manifest:", calculationManifest);

        // Populate the dropdown
        populateCalculationSelector();

        // Setup initial UI based on the first calculation
        if (Object.keys(calculationManifest).length > 0) {
            calcSelect.value = Object.keys(calculationManifest)[0]; // Select the first one
            updateUIForSelectedCalc();
        }

        loadingMessage.style.display = 'none';
        appDiv.style.display = 'block';

    } catch (error) {
        loadingMessage.textContent = "Error loading Pyodide or Python code.";
        console.error("Pyodide/Python loading error:", error);
    }
}

// --- UI Population ---
function populateCalculationSelector() {
    calcSelect.innerHTML = ''; // Clear existing options
    for (const calcId in calculationManifest) {
        const option = document.createElement('option');
        option.value = calcId;
        option.textContent = calculationManifest[calcId].name;
        calcSelect.appendChild(option);
    }
    // Add event listener to update UI when selection changes
    calcSelect.addEventListener('change', updateUIForSelectedCalc);
}

function updateUIForSelectedCalc() {
    currentCalcId = calcSelect.value;
    if (!currentCalcId || !calculationManifest[currentCalcId]) return;

    const calcData = calculationManifest[currentCalcId];

    // Update general info
    calcName.textContent = calcData.name;
    calcDescription.textContent = calcData.description;

    // Render overview LaTeX
    latexOverviewDiv.textContent = calcData.latex_overview || ""; // Use textContent first
    renderMathJax(latexOverviewDiv); // Then typeset

    // Generate input fields
    inputForm.innerHTML = ''; // Clear previous inputs
    calcData.parameters_meta.forEach(param => {
        const div = document.createElement('div');
        div.style.marginBottom = '10px';

        const label = document.createElement('label');
        label.textContent = `${param.description} (${param.name}):`;
        label.htmlFor = `input-${param.name}`;

        const input = document.createElement('input');
        input.type = 'number';
        input.id = `input-${param.name}`;
        input.name = param.name;
        input.step = 'any'; // Allow decimals
        // You could add default values here if needed: input.value = param.default_value || '';

        const unitSpan = document.createElement('span');
        unitSpan.className = 'param-unit';
        unitSpan.textContent = `[${param.default_unit}]`; // Show expected unit

        div.appendChild(label);
        div.appendChild(input);
        div.appendChild(unitSpan);
        inputForm.appendChild(div);
    });

    // Clear previous results and errors
    resultsDiv.innerHTML = '';
    handcalcsOutputDiv.innerHTML = '';
    errorMessageDiv.textContent = '';
}


// --- Calculation Logic ---
async function handleCalculation() {
    if (!currentCalcId || !pyodide) return;

    const calcData = calculationManifest[currentCalcId];
    const inputs = {};
    let formIsValid = true;

    // Collect input values
    calcData.parameters_meta.forEach(param => {
        const inputElement = document.getElementById(`input-${param.name}`);
        if (inputElement.value === '' || isNaN(parseFloat(inputElement.value))) {
            errorMessageDiv.textContent = `Error: Please enter a valid number for ${param.description}.`;
            formIsValid = false;
        }
        inputs[param.name] = inputElement.value; // Pass as string, Python will parse
    });

    if (!formIsValid) {
        resultsDiv.innerHTML = '';
        handcalcsOutputDiv.innerHTML = '';
        return;
    }

    // Clear previous results/errors
    resultsDiv.innerHTML = 'Calculating...';
    handcalcsOutputDiv.innerHTML = '';
    errorMessageDiv.textContent = '';

    try {
        // Call the Python function via Pyodide
        const runCalcFunc = pyodide.globals.get('run_calculation');
        const resultProxy = await runCalcFunc(currentCalcId, inputs); // Pass JS object
        const result = resultProxy.toJs({ dict_converter: Object.fromEntries }); // Convert PyProxy map to JS object
        resultProxy.destroy(); // Clean up proxy

        console.log("Result from Python:", result); // Debugging

        if (result.error) {
            errorMessageDiv.textContent = `Calculation Error: ${result.error}`;
            resultsDiv.innerHTML = '';
            handcalcsOutputDiv.innerHTML = '';
        } else {
            // Display results
            displayResults(result.results);

            // Display handcalcs LaTeX
            handcalcsOutputDiv.textContent = result.handcalcs_latex || "No detailed steps generated.";
            renderMathJax(handcalcsOutputDiv);
        }

    } catch (error) {
        console.error("Error calling Python calculation:", error);
        errorMessageDiv.textContent = `Error communicating with Python: ${error.message}`;
        resultsDiv.innerHTML = '';
        handcalcsOutputDiv.innerHTML = '';
    }
}

// --- Display Results ---
function displayResults(resultsData) {
    resultsDiv.innerHTML = ''; // Clear previous
    const ul = document.createElement('ul');
    ul.style.listStyle = 'none';
    ul.style.paddingLeft = '0';

    // Get the metadata for return values to display descriptions
    const returnMetas = calculationManifest[currentCalcId]?.returns_meta || [];
    const returnMetaMap = returnMetas.reduce((map, meta) => {
        map[meta.name] = meta;
        return map;
    }, {});


    for (const key in resultsData) {
        const resultItem = resultsData[key];
        const meta = returnMetaMap[key];
        const description = meta ? meta.description : key; // Use description from metadata if available

        const li = document.createElement('li');
        // Format the number nicely (e.g., fixed decimal places)
        const valueFormatted = Number(resultItem.value).toPrecision(5); // Adjust precision as needed
        li.innerHTML = `<strong>${description} (${key}):</strong> ${valueFormatted} ${resultItem.unit}`;
        ul.appendChild(li);
    }
    resultsDiv.appendChild(ul);
}

// --- MathJax Helper ---
function renderMathJax(element) {
    if (window.MathJax && element) {
        // Clear previous typesetting? Sometimes needed.
        // MathJax.typesetClear([element]);
        MathJax.typesetPromise([element]).catch((err) => console.error('MathJax typesetting error:', err));
    }
}

// --- Event Listeners ---
calculateBtn.addEventListener('click', handleCalculation);

// --- Start Loading ---
loadPyodideAndPackages();