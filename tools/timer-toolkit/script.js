document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const nav = {
        stopwatch: document.getElementById('nav-stopwatch'),
        countdown: document.getElementById('nav-countdown'),
        interval: document.getElementById('nav-interval'),
    };

    const panels = {
        stopwatch: document.getElementById('stopwatch-panel'),
        countdown: document.getElementById('countdown-panel'),
        interval: document.getElementById('interval-panel'),
    };

    // Stopwatch Elements
    const stopwatch = {
        display: document.getElementById('stopwatch-display'),
        startBtn: document.getElementById('stopwatch-start'),
        stopBtn: document.getElementById('stopwatch-stop'),
        resetBtn: document.getElementById('stopwatch-reset'),
        lapBtn: document.getElementById('stopwatch-lap'),
        lapsList: document.getElementById('stopwatch-laps'),
    };

    // Countdown Elements
    const countdown = {
        display: document.getElementById('countdown-display'),
        hoursInput: document.getElementById('countdown-hours'),
        minutesInput: document.getElementById('countdown-minutes'),
        secondsInput: document.getElementById('countdown-seconds'),
        startBtn: document.getElementById('countdown-start'),
        stopBtn: document.getElementById('countdown-stop'),
        resetBtn: document.getElementById('countdown-reset'),
    };

    // Interval Elements
    const interval = {
        display: document.getElementById('interval-display'),
        status: document.getElementById('interval-status'),
        roundDisplay: document.getElementById('interval-round-display'),
        workMinutesInput: document.getElementById('interval-work-minutes'),
        workSecondsInput: document.getElementById('interval-work-seconds'),
        restMinutesInput: document.getElementById('interval-rest-minutes'),
        restSecondsInput: document.getElementById('interval-rest-seconds'),
        roundsInput: document.getElementById('interval-rounds'),
        startBtn: document.getElementById('interval-start'),
        stopBtn: document.getElementById('interval-stop'),
        resetBtn: document.getElementById('interval-reset'),
    };

    // --- State Management ---
    let mainLoop;
    const state = {
        activePanel: 'stopwatch',
        stopwatch: {
            running: false,
            startTime: 0,
            elapsed: 0,
            laps: [],
        },
        countdown: {
            running: false,
            duration: 0,
            endTime: 0,
        },
        interval: {
            running: false,
            phase: 'idle', // idle, work, rest
            workTime: 0,
            restTime: 0,
            totalRounds: 0,
            currentRound: 0,
            endTime: 0,
        },
    };

    // --- Navigation ---
    function switchPanel(panelId) {
        state.activePanel = panelId;
        Object.values(nav).forEach(n => n.classList.remove('active'));
        Object.values(panels).forEach(p => p.classList.remove('active'));
        nav[panelId].classList.add('active');
        panels[panelId].classList.add('active');
    }

    nav.stopwatch.addEventListener('click', () => switchPanel('stopwatch'));
    nav.countdown.addEventListener('click', () => switchPanel('countdown'));
    nav.interval.addEventListener('click', () => switchPanel('interval'));

    // --- Formatting ---
    function formatTime(ms, showMilliseconds = true) {
        const totalSeconds = Math.floor(ms / 1000);
        const hours = Math.floor(totalSeconds / 3600).toString().padStart(2, '0');
        const minutes = Math.floor((totalSeconds % 3600) / 60).toString().padStart(2, '0');
        const seconds = (totalSeconds % 60).toString().padStart(2, '0');
        if (!showMilliseconds) return `${hours}:${minutes}:${seconds}`;
        const milliseconds = (ms % 1000).toString().padStart(3, '0');
        return `${hours}:${minutes}:${seconds}.${milliseconds}`;
    }
    
    function formatIntervalTime(ms) {
        const totalSeconds = Math.ceil(ms / 1000);
        const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
        const seconds = (totalSeconds % 60).toString().padStart(2, '0');
        return `${minutes}:${seconds}`;
    }

    // --- Main Update Loop ---
    function update() {
        if (state.stopwatch.running) {
            const now = performance.now();
            const elapsed = state.stopwatch.elapsed + (now - state.stopwatch.startTime);
            stopwatch.display.textContent = formatTime(elapsed);
        }

        if (state.countdown.running) {
            const now = performance.now();
            const remaining = state.countdown.endTime - now;
            if (remaining <= 0) {
                countdown.display.textContent = "00:00:00";
                stopCountdown(true); // Finished
            } else {
                countdown.display.textContent = formatTime(remaining, false);
            }
        }
        
        if (state.interval.running) {
            const now = performance.now();
            const remaining = state.interval.endTime - now;
            if (remaining <= 0) {
                handleIntervalTransition();
            } else {
                interval.display.textContent = formatIntervalTime(remaining);
            }
        }
    }

    function startMainLoop() {
        if (!mainLoop) {
            mainLoop = requestAnimationFrame(function loop() {
                update();
                mainLoop = requestAnimationFrame(loop);
            });
        }
    }

    function stopMainLoop() {
        if (mainLoop) {
            cancelAnimationFrame(mainLoop);
            mainLoop = null;
        }
    }
    
    function shouldStopMainLoop() {
        return !state.stopwatch.running && !state.countdown.running && !state.interval.running;
    }


    // --- Stopwatch Logic ---
    stopwatch.startBtn.addEventListener('click', () => {
        const sw = state.stopwatch;
        if (!sw.running) {
            sw.running = true;
            sw.startTime = performance.now();
            stopwatch.startBtn.disabled = true;
            stopwatch.stopBtn.disabled = false;
            startMainLoop();
        }
    });

    stopwatch.stopBtn.addEventListener('click', () => {
        const sw = state.stopwatch;
        if (sw.running) {
            sw.running = false;
            sw.elapsed += performance.now() - sw.startTime;
            stopwatch.startBtn.disabled = false;
            stopwatch.stopBtn.disabled = true;
            if (shouldStopMainLoop()) stopMainLoop();
        }
    });

    stopwatch.resetBtn.addEventListener('click', () => {
        const sw = state.stopwatch;
        sw.running = false;
        sw.elapsed = 0;
        sw.laps = [];
        stopwatch.display.textContent = formatTime(0);
        stopwatch.lapsList.innerHTML = '';
        stopwatch.startBtn.disabled = false;
        stopwatch.stopBtn.disabled = true;
        if (shouldStopMainLoop()) stopMainLoop();
    });

    stopwatch.lapBtn.addEventListener('click', () => {
        const sw = state.stopwatch;
        if (sw.running) {
            const now = performance.now();
            const totalElapsed = sw.elapsed + (now - sw.startTime);
            const lastLapTime = sw.laps.reduce((acc, lap) => acc + lap.time, 0);
            const lapTime = totalElapsed - lastLapTime;
            
            sw.laps.push({ time: lapTime, total: totalElapsed });

            const li = document.createElement('li');
            const lapNumber = `Lap ${sw.laps.length}`.padEnd(8, ' ');
            li.innerHTML = `<span>${lapNumber}</span> <span>${formatTime(lapTime)}</span>`;
            stopwatch.lapsList.prepend(li);
        }
    });

    // --- Countdown Logic ---
    function stopCountdown(finished = false) {
        const cd = state.countdown;
        cd.running = false;
        countdown.startBtn.disabled = false;
        countdown.stopBtn.disabled = true;
        setCountdownInputs(false);
        if (finished) {
            new Audio('data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU'+Array(300).join('123')).play(); // Simple beep
        }
        if (shouldStopMainLoop()) stopMainLoop();
    }
    
    function setCountdownInputs(disabled) {
        countdown.hoursInput.disabled = disabled;
        countdown.minutesInput.disabled = disabled;
        countdown.secondsInput.disabled = disabled;
    }

    countdown.startBtn.addEventListener('click', () => {
        const cd = state.countdown;
        const h = parseInt(countdown.hoursInput.value || 0, 10);
        const m = parseInt(countdown.minutesInput.value || 0, 10);
        const s = parseInt(countdown.secondsInput.value || 0, 10);
        const totalMs = (h * 3600 + m * 60 + s) * 1000;

        if (totalMs > 0 && !cd.running) {
            cd.running = true;
            cd.duration = totalMs;
            cd.endTime = performance.now() + totalMs;
            countdown.display.textContent = formatTime(totalMs, false);
            countdown.startBtn.disabled = true;
            countdown.stopBtn.disabled = false;
            setCountdownInputs(true);
            startMainLoop();
        }
    });

    countdown.stopBtn.addEventListener('click', () => stopCountdown());

    countdown.resetBtn.addEventListener('click', () => {
        stopCountdown();
        countdown.display.textContent = "00:00:00";
        countdown.hoursInput.value = '';
        countdown.minutesInput.value = '';
        countdown.secondsInput.value = '';
        setCountdownInputs(false);
    });
    
    // --- Interval Logic ---
    function resetInterval() {
        state.interval.running = false;
        state.interval.phase = 'idle';
        interval.status.textContent = 'IDLE';
        interval.display.textContent = '00:00';
        interval.roundDisplay.textContent = 'Round 0/0';
        interval.startBtn.disabled = false;
        interval.stopBtn.disabled = true;
        Object.values(interval).filter(el => el.tagName === 'INPUT').forEach(i => i.disabled = false);
        if (shouldStopMainLoop()) stopMainLoop();
    }
    
    function handleIntervalTransition() {
        const iv = state.interval;
        if (iv.phase === 'work') {
            if (iv.currentRound < iv.totalRounds) {
                iv.phase = 'rest';
                iv.endTime = performance.now() + iv.restTime;
                interval.status.textContent = 'REST';
                new Audio('data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU'+Array(150).join('123')).play();
            } else {
                resetInterval();
                interval.status.textContent = 'DONE!';
                new Audio('data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU'+Array(400).join('123')).play();
            }
        } else if (iv.phase === 'rest') {
            iv.currentRound++;
            iv.phase = 'work';
            iv.endTime = performance.now() + iv.workTime;
            interval.status.textContent = 'WORK';
            interval.roundDisplay.textContent = `Round ${iv.currentRound}/${iv.totalRounds}`;
            new Audio('data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU'+Array(150).join('456')).play();
        }
    }
    
    interval.startBtn.addEventListener('click', () => {
        const iv = state.interval;
        const workM = parseInt(interval.workMinutesInput.value || 0, 10);
        const workS = parseInt(interval.workSecondsInput.value || 0, 10);
        const restM = parseInt(interval.restMinutesInput.value || 0, 10);
        const restS = parseInt(interval.restSecondsInput.value || 0, 10);
        const rounds = parseInt(interval.roundsInput.value || 1, 10);
        
        iv.workTime = (workM * 60 + workS) * 1000;
        iv.restTime = (restM * 60 + restS) * 1000;
        iv.totalRounds = rounds;

        if (iv.workTime > 0 && rounds > 0 && !iv.running) {
            iv.running = true;
            iv.currentRound = 1;
            iv.phase = 'work';
            iv.endTime = performance.now() + iv.workTime;
            
            interval.status.textContent = 'WORK';
            interval.roundDisplay.textContent = `Round ${iv.currentRound}/${iv.totalRounds}`;
            interval.startBtn.disabled = true;
            interval.stopBtn.disabled = false;
            Object.values(interval).filter(el => el.tagName === 'INPUT').forEach(i => i.disabled = true);
            
            startMainLoop();
        }
    });

    interval.stopBtn.addEventListener('click', () => {
        state.interval.running = false;
        interval.startBtn.disabled = false;
        interval.stopBtn.disabled = true;
        // Keep state to allow resume, don't fully reset. For full reset, use the reset button.
        if(shouldStopMainLoop()) stopMainLoop();
    });

    interval.resetBtn.addEventListener('click', resetInterval);

    // --- Initial Setup ---
    switchPanel('stopwatch');
});
