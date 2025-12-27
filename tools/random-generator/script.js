document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const toolButtons = document.querySelectorAll('.tool-btn');
    const resultDisplay = document.getElementById('resultDisplay');
    const textResultDisplay = document.getElementById('textResultDisplay');
    const controls = document.querySelectorAll('.controls');
    const historyList = document.getElementById('historyList');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');

    // --- State ---
    let currentTool = 'coin';
    let isAnimating = false;
    let history = [];
    const MAX_HISTORY = 20;
    let lastDieSides = 0;
    let originalDrawerList = [];
    let remainingDrawerList = [];

    // --- Templates for Dynamic Content ---
    const coinHTML = `
        <div class="coin-visual">
            <div class="coin-letter">?</div>
        </div>`;
    const toolIcons = {
        coin: '🪙',
        dice: '🎲',
        number: '#️⃣',
        list: '📜',
        card: '🃏',
        drawer: '📥'
    };

    const toolDetails = {
        coin: `
            <h4>Overview</h4>
            <p>This tool simulates a classic 50/50 coin flip, providing a random choice between two outcomes: Heads or Tails.</p>
            <h4>How to Use</h4>
            <p>Click the coin display or press the Enter key to flip the coin. The result is shown on the coin, in the text below, and added to the history.</p>
            <h4>Underlying Principles</h4>
            <p>The coin flip represents a binary choice with a uniform probability distribution, meaning each outcome has an equal chance of occurring.</p>
            <p><b>Formula:</b> <code>P(Heads) = P(Tails) = 1/2 = 0.5</code></p>
            <p>Computers cannot generate truly random numbers; instead, they use Pseudo-Random Number Generators (PRNGs). This tool utilizes the browser's built-in <code>Math.random()</code>, which produces a floating-point number between 0 (inclusive) and 1 (exclusive). To get a binary outcome, we check if the result is less than 0.5.</p>
            <h4>Applications & Fun Facts</h4>
            <ul>
                <li><strong>Decision Making:</strong> The quickest way to resolve a simple dilemma or break a tie.</li>
                <li><strong>Dynamical Bias:</strong> A 2007 paper by Diaconis, Holmes, and Montgomery demonstrated that a physically flipped coin has a slight bias (around 51%) of landing on the same side it started on. This digital version has no such physical bias.</li>
            </ul>
            <h4>References</h4>
            <ul>
                <li>MDN Web Docs: <a href="https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Math/random" target="_blank">Math.random()</a></li>
                <li>Wikipedia: <a href="https://en.wikipedia.org/wiki/Coin_flipping" target="_blank">Coin flipping</a></li>
            </ul>
        `,
        dice: `
            <h4>Overview</h4>
            <p>Rolls standard polyhedral dice used in tabletop role-playing games (RPGs) and other board games.</p>
            <h4>How to Use</h4>
            <p>Click a die button (D4, D6, etc.) to select it and perform an initial roll. Subsequently, click the main display or press Enter to re-roll the same die type.</p>
            <h4>Underlying Principles</h4>
            <p>Each die roll is an independent event with a uniform probability distribution across its faces. The probability of rolling any specific number is 1 divided by the number of sides (N).</p>
            <p><b>Formula:</b> <code>P(x) = 1 / N</code>, for <code>x ∈ {1, 2, ..., N}</code></p>
            <p>To map the <code>[0, 1)</code> output of the random number generator to an integer range, we use the formula: <code>roll = floor(random() * sides) + 1</code>. Multiplying by 'sides' scales the number, 'floor' converts it to an integer, and adding 1 shifts the range from <code>[0, N-1]</code> to <code>[1, N]</code>.</p>
            <h4>Applications & Fun Facts</h4>
            <ul>
                <li><strong>Gaming:</strong> The foundation of chance in games like Dungeons & Dragons, Warhammer, and many others.</li>
                <li><strong>History:</strong> Dice are one of the oldest known gaming implements, with some dating back to 3000 BC in Persia (modern-day Iran). They were often used for divination before becoming common for entertainment.</li>
                <li><strong>Perfect Solids:</strong> Most standard dice are based on the Platonic Solids, five polyhedra whose faces are all identical regular polygons, ensuring each face has an equal chance of landing up.</li>
            </ul>
            <h4>References</h4>
            <ul>
                <li>Wikipedia: <a href="https://en.wikipedia.org/wiki/Dice" target="_blank">Dice</a></li>
            </ul>
        `,
        number: `
            <h4>Overview</h4>
            <p>Generates a cryptographically-secure random integer within a specified inclusive range (minimum and maximum values included).</p>
            <h4>How to Use</h4>
            <p>Set your desired minimum and maximum values in the input fields. Click the display or press Enter to generate a new number.</p>
            <h4>Underlying Principles</h4>
            <p>This tool generalizes the principle of the dice roller to an arbitrary range. It maps the output of a random number generator to a specific integer set.</p>
            <p><b>Formula:</b> <code>result = floor(random() * (max - min + 1)) + min</code></p>
            <p>The <code>(max - min + 1)</code> part calculates the total number of possible integers in the range. The result of the multiplication is then shifted by adding the <code>min</code> value to set the lower bound of the range correctly.</p>
            <h4>Applications & Fun Facts</h4>
            <ul>
                <li><strong>Security:</strong> Generating random numbers is crucial for cryptography, from creating encryption keys to security tokens.</li>
                <li><strong>Simulations:</strong> Used in scientific and financial models (Monte Carlo simulations) to model random or unpredictable processes.</li>
                <li><strong>Human Randomness:</strong> Studies show humans are terrible at generating random numbers. We tend to avoid streaks (like picking the same number twice) even though they are statistically common, a phenomenon known as gambler's fallacy.</li>
            </ul>
        `,
        list: `
            <h4>Overview</h4>
            <p>Randomly selects a single item from a user-provided list. The original list is not modified, so the same item can be picked again on subsequent tries.</p>
            <h4>How to Use</h4>
            <p>Enter each item on a new line in the text box. Click the display or press Enter to randomly select one.</p>
            <h4>Underlying Principles</h4>
            <p>This method is known as <strong>"sampling with replacement."</strong> Each pick is an independent event, and every item in the list has an equal probability of being chosen on every single attempt.</p>
            <p><b>Formula:</b> <code>P(item) = 1 / N</code>, where N is the total number of items in the list.</p>
            <p>The algorithm simply generates a random integer to use as an index for the list array: <code>index = floor(random() * array.length)</code>.</p>
            <h4>Applications & Fun Facts</h4>
            <ul>
                <li><strong>Statistical Bootstrap:</strong> This concept is the foundation of "bootstrapping" in statistics, where repeatedly sampling with replacement from a dataset helps estimate the properties of a larger population.</li>
                <li><strong>Giveaways:</strong> A simple way to pick a winner from a list of entrants where one person could potentially win multiple times if their name was entered more than once.</li>
            </ul>
            <h4>References</h4>
            <ul>
                <li>Wikipedia: <a href="https://en.wikipedia.org/wiki/Bootstrapping_(statistics)" target="_blank">Bootstrapping (statistics)</a></li>
            </ul>
        `,
        card: `
            <h4>Overview</h4>
            <p>Draws one or more cards from a standard, shuffled 52-card deck. Each click re-shuffles and draws from a complete deck.</p>
            <h4>How to Use</h4>
            <p>Select the number of cards you wish to draw, then click the display or press Enter.</p>
            <h4>Underlying Principles</h4>
            <p>To guarantee a fair and unbiased shuffle, this tool uses the modern inside-out version of the <strong>Fisher-Yates Shuffle algorithm</strong> before drawing any cards.</p>
            <p>The algorithm works by iterating through the deck and, for each card, swapping it with another card from a random position earlier in the deck. This prevents the biases found in simpler shuffling methods (like sorting by a random number) and ensures that every possible permutation of the deck is equally likely.</p>
            <h4>Applications & Fun Facts</h4>
            <ul>
                <li><strong>Combinatorics:</strong> The number of possible unique arrangements of a 52-card deck is 52 factorial (52!), an astronomically large number (approximately 8 x 10<sup>67</sup>). It is virtually certain that no two randomly shuffled decks have ever produced the exact same order in human history.</li>
                <li><strong>Digital Gaming:</strong> This algorithm is fundamental to digital poker, solitaire, and any computer-based card game to ensure fair play.</li>
            </ul>
            <h4>References</h4>
            <ul>
                <li>Wikipedia: <a href="https://en.wikipedia.org/wiki/Fisher–Yates_shuffle" target="_blank">Fisher–Yates shuffle</a></li>
            </ul>
        `,
        drawer: `
            <h4>Overview</h4>
            <p>Randomly picks one item from a list and removes it from the pool, ensuring it cannot be picked again until the list is reset. This simulates drawing names from a hat.</p>
            <h4>How to Use</h4>
            <p>Enter items on new lines in the text box; the list of remaining items updates automatically. Click the display or press Enter to draw an item. Use the 'Reset List' button to start over with the original full list.</p>
            <h4>Underlying Principles</h4>
            <p>This method is known as <strong>"sampling without replacement."</strong> The probability of any given item being selected increases as the number of remaining items decreases.</p>
            <p><b>Formula (for any specific item):</b> <code>P(pick) = 1 / R</code>, where R is the number of remaining items.</p>
            <p>The algorithm generates a random index within the bounds of the *remaining* items list, selects the item at that index, and then permanently removes it from the list for all future draws using <code>Array.prototype.splice()</code>.</p>
            <h4>Applications & Fun Facts</h4>
            <ul>
                <li><strong>Fair Selection:</strong> This is the standard method for raffles, gift exchanges (like Secret Santa), or forming teams one by one, as it guarantees that every participant is chosen exactly once.</li>
                <li><strong>Lotteries:</strong> National and state lotteries use physical machines to perform sampling without replacement, drawing numbered balls from a drum one at a time.</li>
            </ul>
            <h4>References</h4>
            <ul>
                <li>Wikipedia: <a href="https://en.wikipedia.org/wiki/Sampling_(statistics)" target="_blank">Sampling (statistics)</a></li>
            </ul>
        `
    };
    
    // --- History Management ---
    function formatTime(date) {
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        return `${hours}:${minutes}:${seconds}`;
    }

    function renderHistory() {
        historyList.innerHTML = '';
        history.forEach(item => {
            const li = document.createElement('li');
            li.className = 'history-item';
            const timeString = formatTime(item.timestamp);
            li.innerHTML = `
                <div class="history-item-main">
                    <span class="history-item-icon">${toolIcons[item.tool]}</span>
                    <span class="history-item-text">${item.result}</span>
                </div>
                <span class="history-item-time">${timeString}</span>
            `;
            historyList.appendChild(li);
        });
    }

    function addToHistory(tool, result) {
        const timestamp = new Date();
        history.unshift({ tool, result, timestamp });
        if (history.length > MAX_HISTORY) {
            history.pop();
        }
        renderHistory();
    }

    function clearHistory() {
        history = [];
        renderHistory();
    }

    // --- Core Functions ---
    function clearDisplays() {
        resultDisplay.innerHTML = '';
        textResultDisplay.textContent = '';
        // Also clear any existing details
        const placeholders = document.querySelectorAll('.details-placeholder');
        placeholders.forEach(p => p.innerHTML = '');
    }

    function renderToolDetails(toolName) {
        const detailsContent = toolDetails[toolName];
        if (!detailsContent) return;

        const placeholder = document.querySelector(`#${toolName}-controls .details-placeholder`);
        if (!placeholder) return;

        const detailsEl = document.createElement('details');
        detailsEl.innerHTML = `
            <summary>About & Methodology</summary>
            <div class="details-content">
                ${detailsContent}
            </div>
        `;
        placeholder.appendChild(detailsEl);
    }

    function switchTool(toolName) {
        if (isAnimating) return;
        currentTool = toolName;
        lastDieSides = 0;
        clearDisplays();
        
        toolButtons.forEach(btn => btn.classList.toggle('active', btn.dataset.tool === toolName));
        controls.forEach(control => control.classList.toggle('active', control.id === `${toolName}-controls`));

        resultDisplay.className = 'result-display';
        resultDisplay.style.backgroundColor = 'var(--surface-color)';
        
        switch (toolName) {
            case 'coin':
                resultDisplay.classList.add('shape-round');
                resultDisplay.innerHTML = coinHTML;
                break;
            case 'dice':
                resultDisplay.classList.add('shape-square');
                resultDisplay.innerHTML = '🎲';
                textResultDisplay.textContent = 'Select a die below';
                break;
            case 'number':
                resultDisplay.classList.add('shape-rect');
                resultDisplay.textContent = '#';
                break;
            case 'list':
                resultDisplay.classList.add('shape-rect');
                resultDisplay.textContent = '📜';
                break;
            case 'card':
                resultDisplay.classList.add('shape-rect');
                resultDisplay.innerHTML = '🃏';
                textResultDisplay.textContent = 'Click to draw';
                break;
            case 'drawer':
                resultDisplay.classList.add('shape-rect');
                resultDisplay.innerHTML = '📥';
                textResultDisplay.textContent = 'Click to draw from list';
                initializeDrawer();
                break;
        }
        // Render the details for the newly selected tool
        renderToolDetails(toolName);
    }

    // --- Tool-Specific Actions ---
    function flipCoin() {
        if (isAnimating) return;
        isAnimating = true;

        const coinLetterElement = resultDisplay.querySelector('.coin-letter');
        if (!coinLetterElement) { isAnimating = false; return; }

        let spinCount = 0;
        const totalSpins = 3;
        const spinInterval = setInterval(() => {
            coinLetterElement.textContent = (spinCount % 2 === 0) ? 'H' : 'T';
            resultDisplay.style.backgroundColor = (spinCount % 2 === 0) ? '#ffd700' : '#c0c0c0';
            spinCount++;
            if (spinCount > totalSpins) {
                clearInterval(spinInterval);
                const result = Math.random() < 0.5 ? 'Heads' : 'Tails';
                coinLetterElement.textContent = result === 'Heads' ? 'H' : 'T';
                resultDisplay.style.backgroundColor = result === 'Heads' ? '#ffd700' : '#c0c0c0';
                textResultDisplay.textContent = result;
                addToHistory('coin', result);
                isAnimating = false;
            }
        }, 80);
    }

    function drawD6(roll) {
        resultDisplay.classList.add('result-display--pips');
        let pipsHTML = '';
        for (let i = 0; i < 9; i++) pipsHTML += `<div class="pip"></div>`;
        resultDisplay.innerHTML = `<div class="dice-pips-container pip-${roll}">${pipsHTML}</div>`;
    }

    function animateRoll(finalRoll, sides, resultText) {
        let intervalCount = 0;
        const totalIntervals = 10;
        const animationInterval = setInterval(() => {
            intervalCount++;
            const randomRoll = Math.floor(Math.random() * sides) + 1;
            if (sides === 6) {
                drawD6(randomRoll);
            } else {
                resultDisplay.textContent = randomRoll;
            }

            if (intervalCount >= totalIntervals) {
                clearInterval(animationInterval);
                if (sides === 6) {
                    drawD6(finalRoll);
                } else {
                    resultDisplay.textContent = finalRoll;
                }
                textResultDisplay.textContent = resultText;
                addToHistory('dice', resultText);
                isAnimating = false;
            }
        }, 50);
    }

    function rollDice(sides, targetButton) {
        if (isAnimating) return;
        isAnimating = true;
        lastDieSides = sides;

        if (targetButton) {
            document.querySelectorAll('.dice-btn').forEach(btn => btn.classList.remove('active'));
            targetButton.classList.add('active');
        }

        resultDisplay.className = 'result-display';
        switch (sides) {
            case 4: resultDisplay.classList.add('shape-d4'); break;
            case 6: resultDisplay.classList.add('shape-d6'); break;
            case 8: resultDisplay.classList.add('shape-d8'); break;
            case 10: resultDisplay.classList.add('shape-d10'); break;
            case 12: resultDisplay.classList.add('shape-d12'); break;
            case 20: resultDisplay.classList.add('shape-d20'); break;
            default: resultDisplay.classList.add('shape-square'); break;
        }
        
        const roll = Math.floor(Math.random() * sides) + 1;
        const resultText = `D${sides}: ${roll}`;
        
        clearDisplays();
        animateRoll(roll, sides, resultText);
    }

    function generateNumber() {
        const minInput = document.getElementById('minNumber');
        const maxInput = document.getElementById('maxNumber');
        let min = parseInt(minInput.value, 10);
        let max = parseInt(maxInput.value, 10);

        if (isNaN(min) || isNaN(max)) {
            resultDisplay.textContent = 'Err';
            textResultDisplay.textContent = 'Invalid Range';
            return;
        }
        if (min > max) {
            [min, max] = [max, min];
            minInput.value = min;
            maxInput.value = max;
        }
        const result = Math.floor(Math.random() * (max - min + 1)) + min;

        clearDisplays();
        resultDisplay.textContent = result;
        addToHistory('number', result);
    }

    function pickFromList() {
        const listInput = document.getElementById('listInput');
        const items = listInput.value.split('\n').map(item => item.trim()).filter(Boolean);

        if (items.length === 0) {
            resultDisplay.textContent = 'Err';
            textResultDisplay.textContent = 'List is empty';
            return;
        }
        const result = items[Math.floor(Math.random() * items.length)];
        clearDisplays();
        resultDisplay.textContent = result;
        addToHistory('list', result);
    }

    function drawCards() {
        const suits = { '♠': 'black', '♣': 'black', '♥': 'red', '♦': 'red' };
        const ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];
        const deck = [];
        for (const suit in suits) {
            for (const rank of ranks) {
                deck.push({ rank, suit, color: suits[suit] });
            }
        }

        for (let i = deck.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [deck[i], deck[j]] = [deck[j], deck[i]];
        }

        const count = parseInt(document.getElementById('cardCount').value, 10);
        if (isNaN(count) || count < 1 || count > 52) {
            resultDisplay.textContent = 'Err';
            textResultDisplay.textContent = 'Invalid card count';
            return;
        }

        const drawnCards = deck.slice(0, count);

        clearDisplays();

        const historyText = drawnCards.map(c => `${c.rank}${c.suit}`).join(', ');
        addToHistory('card', historyText);
        textResultDisplay.textContent = `Drawn ${count} card(s)`;

        let cardsHTML = '<div class="card-visual-wrapper">';
        drawnCards.forEach(card => {
            cardsHTML += `
                <div class="card-visual">
                    <div class="corner top-left">
                        <div class="card-rank ${card.color}">${card.rank}</div>
                        <div class="card-suit ${card.color}">${card.suit}</div>
                    </div>
                    <div class="suit-center card-suit ${card.color}">${card.suit}</div>
                    <div class="corner bottom-right">
                        <div class="card-rank ${card.color}">${card.rank}</div>
                        <div class="card-suit ${card.color}">${card.suit}</div>
                    </div>
                </div>
            `;
        });
        cardsHTML += '</div>';

        resultDisplay.innerHTML = cardsHTML;
    }

    function renderRemainingList() {
        const listEl = document.getElementById('drawerRemainingList');
        listEl.innerHTML = '';
        remainingDrawerList.forEach(item => {
            const li = document.createElement('li');
            li.textContent = item;
            listEl.appendChild(li);
        });
    }

    function initializeDrawer() {
        const drawerInput = document.getElementById('drawerInput');
        originalDrawerList = drawerInput.value.split('\n').map(item => item.trim()).filter(Boolean);
        remainingDrawerList = [...originalDrawerList];
        renderRemainingList();
    }

    function resetDrawer() {
        remainingDrawerList = [...originalDrawerList];
        renderRemainingList();
        resultDisplay.innerHTML = '📥';
        textResultDisplay.textContent = 'List has been reset';
    }

    function pickAndRemove() {
        if (remainingDrawerList.length === 0) {
            resultDisplay.textContent = 'EMPTY';
            textResultDisplay.textContent = 'Reset the list to draw again';
            return;
        }
        const randomIndex = Math.floor(Math.random() * remainingDrawerList.length);
        const pickedItem = remainingDrawerList.splice(randomIndex, 1)[0];

        clearDisplays();
        resultDisplay.textContent = pickedItem;
        addToHistory('drawer', pickedItem);
        renderRemainingList();
    }

    // --- Event Listeners ---
    toolButtons.forEach(btn => btn.addEventListener('click', () => switchTool(btn.dataset.tool)));

    resultDisplay.addEventListener('click', () => {
        if (currentTool === 'coin') flipCoin();
        if (currentTool === 'number') generateNumber();
        if (currentTool === 'list') pickFromList();
        if (currentTool === 'card') drawCards();
        if (currentTool === 'drawer') pickAndRemove();
        if (currentTool === 'dice' && lastDieSides > 0) rollDice(lastDieSides);
    });

    document.getElementById('dice-controls').addEventListener('click', (e) => {
        if (e.target.matches('.dice-btn')) rollDice(parseInt(e.target.dataset.sides, 10), e.target);
    });

    document.getElementById('drawerInput').addEventListener('input', initializeDrawer);
    document.getElementById('drawerResetBtn').addEventListener('click', resetDrawer);
    clearHistoryBtn.addEventListener('click', clearHistory);

    // Global keydown listener
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            if (document.activeElement.tagName === 'TEXTAREA') return;

            switch (currentTool) {
                case 'coin':
                    flipCoin();
                    break;
                case 'number':
                    generateNumber();
                    break;
                case 'list':
                    pickFromList();
                    break;
                case 'card':
                    drawCards();
                    break;
                case 'drawer':
                    pickAndRemove();
                    break;
                case 'dice':
                    if (lastDieSides > 0) rollDice(lastDieSides);
                    break;
            }
        }
    });

    // --- Initial Setup ---
    switchTool('coin');
});
