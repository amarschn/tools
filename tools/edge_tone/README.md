# Whistle Acoustics Explorer

An interactive, browser-based tool for analyzing the physics of whistles, flutes, and other resonant instruments. This application visualizes the relationship between a resonator's natural frequencies and the edge-tones produced by a jet of air, allowing users to find the "locking" conditions where a stable musical note is produced.

This project runs entirely in the browser using Pyodide to execute the core physics calculations, which were originally part of a Python Flask backend.

## ✨ Features

* **Two Resonator Models:** Analyze both `Pipe (Open-Closed)` models (like flutes) and `Helmholtz` resonators (like blowing over a bottle).
* **Interactive Visualization:** A Plotly.js chart shows the resonator's modes and the jet's edge-tone stages, with clear markers at the points where they intersect and "lock-in".
* **Real-time Parameter Control:** Adjust parameters like temperature, jet thickness, and resonator geometry to see the effects on the acoustics instantly.
* **Preset Configurations:** Quickly load parameters for common examples like a "Tin Whistle" or "Bottle Blow".
* **Serverless Architecture:** Runs 100% on the client-side, making it easy to host on static services like GitHub Pages.

## 🚀 How to Run

No server or complex setup is required!

1.  Clone or download this repository.
2.  Ensure the three main files are in the same directory:
    * `index.html`
    * `main.py`
    * `whistle_acoustics.py`
3.  Open the `index.html` file in a modern web browser (like Chrome, Firefox, or Edge).

The application will take a moment to initialize the Pyodide (Python) runtime, after which it will be fully interactive.

### Deploying to GitHub Pages

1.  Push the project folder (containing `index.html`, `main.py`, and `whistle_acoustics.py`) to a new GitHub repository.
2.  In the repository settings, go to the "Pages" section.
3.  Under "Build and deployment", select the source as "Deploy from a branch".
4.  Choose the main branch and the `/ (root)` folder, then save.
5.  Your site will be live at `https://<your-username>.github.io/<your-repo-name>/` in a few minutes.

## 🛠️ Technology Stack

* **Frontend:** HTML, Tailwind CSS
* **Visualization:** Plotly.js
* **Core Logic:** Python 3, running in the browser via **Pyodide**.
* **Original Concept:** This app was converted from a Python Flask web server application to a fully static, client-side application.

## 📁 File Structure

```
.
├── index.html              # The main application page, contains all UI and JavaScript logic.
├── main.py                 # The main Python script called by JavaScript. It handles data sanitization and orchestrates the acoustic calculations.
└── whistle_acoustics.py    # The core Python library containing the physics formulas for sound speed, resonance, and locking conditions.
```

## 🔬 Acoustic Principles

The tool is based on the interaction between two phenomena:

1.  **Resonator Modes:** Every hollow object has natural frequencies at which the air inside it prefers to vibrate. These are shown as dashed horizontal lines on the plot.
2.  **Edge Tones:** When a jet of air strikes a sharp edge (the "labium"), it creates oscillating tones whose frequency depends on the speed of the jet. These are shown as dotted diagonal lines.

A stable musical note is produced only when the edge-tone frequency **matches** one of the resonator's modes. The visualization helps find the exact jet speeds where this "locking" occurs.