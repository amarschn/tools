#!/usr/bin/env node
/*
 * Dump the frozen prototype corpus to JSON so the Python migration can read it.
 *
 * The corpus is a browser IIFE that builds its data procedurally. Executing it
 * is the only lossless way to read it; hand-parsing the JS would silently drift
 * from what the prototypes actually render.
 *
 * Output key order is stable, so repeated dumps are byte-identical.
 */

"use strict";

const path = require("path");

global.window = {};
require(path.join(__dirname, "..", "prototypes", "assets", "synthetic-corpus.js"));

const corpus = global.window.MaterialsPrototypeCorpus;
if (!corpus) {
  console.error("corpus did not attach to window");
  process.exit(1);
}

process.stdout.write(JSON.stringify(corpus, null, 2) + "\n");
