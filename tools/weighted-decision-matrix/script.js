document.addEventListener('DOMContentLoaded', () => {
    // --- STATE ---
    let state = {
        criteria: [
            { id: Date.now(), name: 'Price', weight: 40 },
            { id: Date.now() + 1, name: 'Features', weight: 30 },
            { id: Date.now() + 2, name: 'Usability', weight: 20 },
            { id: Date.now() + 3, name: 'Support', weight: 10 },
        ],
        options: [
            { id: Date.now() + 4, name: 'Product A' },
            { id: Date.now() + 5, name: 'Product B' },
            { id: Date.now() + 6, name: 'Product C' },
        ],
        scores: {} // { 'optionId_criterionId': score }
    };

    // --- DOM ELEMENTS ---
    const criteriaList = document.getElementById('criteria-list');
    const optionsList = document.getElementById('options-list');
    const addCriterionBtn = document.getElementById('add-criterion');
    const addOptionBtn = document.getElementById('add-option');
    const matrixContainer = document.getElementById('matrix-container');
    const resultsList = document.getElementById('results-list');

    // --- RENDER FUNCTIONS ---
    function renderCriteria() {
        criteriaList.innerHTML = '';
        state.criteria.forEach(criterion => {
            const div = document.createElement('div');
            div.className = 'criterion-item input-row';
            div.innerHTML = `
                <div class="input-group">
                    <input type="text" placeholder="Criterion Name" value="${criterion.name}" data-id="${criterion.id}" data-type="criterion-name">
                </div>
                <div class="input-group">
                    <input type="number" placeholder="Weight" value="${criterion.weight}" data-id="${criterion.id}" data-type="criterion-weight" min="0">
                </div>
                <button class="button-icon-secondary" data-id="${criterion.id}" data-type="remove-criterion">&times;</button>
            `;
            criteriaList.appendChild(div);
        });
    }

    function renderOptions() {
        optionsList.innerHTML = '';
        state.options.forEach(option => {
            const div = document.createElement('div');
            div.className = 'option-item input-row';
            div.innerHTML = `
                <div class="input-group">
                    <input type="text" placeholder="Option Name" value="${option.name}" data-id="${option.id}" data-type="option-name">
                </div>
                <button class="button-icon-secondary" data-id="${option.id}" data-type="remove-option">&times;</button>
            `;
            optionsList.appendChild(div);
        });
    }

    function renderMatrix() {
        if (state.criteria.length === 0 || state.options.length === 0) {
            matrixContainer.innerHTML = '<p class="placeholder-text">Add criteria and options to build the matrix.</p>';
            return;
        }

        let headHTML = '<th>Options</th>';
        state.criteria.forEach(c => headHTML += `<th>${c.name} (w: ${c.weight}%)</th>`);
        headHTML += '<th>Total Score</th>';

        let bodyHTML = '';
        state.options.forEach(o => {
            bodyHTML += `<tr><td class="option-name-col">${o.name}</td>`;
            state.criteria.forEach(c => {
                const scoreKey = `${o.id}_${c.id}`;
                const score = state.scores[scoreKey] || 0;
                bodyHTML += `<td><input type="number" min="0" max="10" value="${score}" data-option-id="${o.id}" data-criterion-id="${c.id}"></td>`;
            });
            bodyHTML += `<td class="total-score" id="total-score-${o.id}">0</td>`;
            bodyHTML += '</tr>';
        });

        matrixContainer.innerHTML = `
            <table id="decision-matrix">
                <thead><tr>${headHTML}</tr></thead>
                <tbody>${bodyHTML}</tbody>
            </table>
        `;
    }

    function renderResults(calculatedResults) {
        if (calculatedResults.length === 0) {
            resultsList.innerHTML = '<p class="placeholder-text">Results will be ranked here.</p>';
            return;
        }

        resultsList.innerHTML = '';
        calculatedResults.forEach((result, index) => {
            const div = document.createElement('div');
            div.className = `result-item ${index === 0 ? 'winner' : ''}`;
            div.innerHTML = `
                <span class="result-rank">#${index + 1}</span>
                <span class="result-name">${result.name}</span>
                <span class="result-score">${result.totalScore.toFixed(2)}</span>
            `;
            resultsList.appendChild(div);
        });
    }

    // --- CALCULATION ---
    function calculate() {
        const totalWeight = state.criteria.reduce((sum, c) => sum + (parseFloat(c.weight) || 0), 0);
        if (totalWeight === 0) {
            renderResults([]);
            return;
        };

        const results = state.options.map(option => {
            let totalScore = 0;
            state.criteria.forEach(criterion => {
                const scoreKey = `${option.id}_${criterion.id}`;
                const score = parseFloat(state.scores[scoreKey]) || 0;
                const weight = parseFloat(criterion.weight) || 0;
                totalScore += score * (weight / totalWeight);
            });
            
            // Update the total score in the matrix table
            const totalScoreCell = document.getElementById(`total-score-${option.id}`);
            if (totalScoreCell) {
                totalScoreCell.textContent = totalScore.toFixed(2);
            }

            return { id: option.id, name: option.name, totalScore };
        });

        results.sort((a, b) => b.totalScore - a.totalScore);
        renderResults(results);
    }

    // --- EVENT HANDLERS ---
    function handleStateChange(e) {
        const id = e.target.dataset.id;
        const type = e.target.dataset.type;

        if (type === 'criterion-name') {
            const criterion = state.criteria.find(c => c.id == id);
            criterion.name = e.target.value;
        } else if (type === 'criterion-weight') {
            const criterion = state.criteria.find(c => c.id == id);
            criterion.weight = parseFloat(e.target.value) || 0;
        } else if (type === 'option-name') {
            const option = state.options.find(o => o.id == id);
            option.name = e.target.value;
        } else if (type === 'remove-criterion') {
            state.criteria = state.criteria.filter(c => c.id != id);
        } else if (type === 'remove-option') {
            state.options = state.options.filter(o => o.id != id);
        }
        
        render();
    }

    function handleMatrixInputChange(e) {
        const optionId = e.target.dataset.optionId;
        const criterionId = e.target.dataset.criterionId;
        const scoreKey = `${optionId}_${criterionId}`;
        state.scores[scoreKey] = parseFloat(e.target.value) || 0;
        calculate();
    }

    addCriterionBtn.addEventListener('click', () => {
        state.criteria.push({ id: Date.now(), name: '', weight: 10 });
        render();
    });

    addOptionBtn.addEventListener('click', () => {
        state.options.push({ id: Date.now(), name: '' });
        render();
    });

    // --- MAIN RENDER & INIT ---
    function render() {
        renderCriteria();
        renderOptions();
        renderMatrix();
        calculate();
    }
    
    // Use event delegation for dynamic elements
    document.getElementById('inputs-card').addEventListener('input', handleStateChange);
    document.getElementById('inputs-card').addEventListener('click', handleStateChange);
    document.getElementById('outputs-card').addEventListener('input', handleMatrixInputChange);

    // Initial render
    render();
});
