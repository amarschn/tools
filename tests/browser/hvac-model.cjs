// Property test for the house model: thousands of random edits must never leave a gap,
// an overlap, or a room outside the shell. Needs no browser:
//   node tests/browser/hvac-model.cjs
const assert = require('assert');
const M = require('../../tools/hvac-load-calculator/app/model.js');

let seed = 12345;
const rand = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
const pick = (list) => list[Math.floor(rand() * list.length)];

let edits = 0;
for (let trial = 0; trial < 60; trial++) {
  const model = M.create({ area: 800 + rand() * 3000, stories: 1 + Math.floor(rand() * 3), aspect: 1 + rand() });
  assert.deepStrictEqual(M.check(model), [], 'fresh model is valid');
  for (let step = 0; step < 150; step++) {
    const level = Math.floor(rand() * model.stories);
    const walls = M.interiorWalls(model, level);
    const action = rand();
    if (action < 0.3) {
      const room = pick(M.roomsOf(model, level));
      const axis = rand() < 0.5 ? 'v' : 'h';
      M.splitRoom(model, level, room.id, axis, axis === 'v' ? room.x + room.w * rand() : room.y + room.h * rand());
    } else if (action < 0.6 && walls.length) {
      const wall = pick(walls);
      M.moveWall(model, level, wall, wall.at + (rand() - 0.5) * 30, walls.map((w) => w.at));
    } else if (action < 0.7 && walls.length) {
      M.removeWall(model, level, pick(walls));
    } else if (action < 0.85) {
      const side = pick(['N', 'E', 'S', 'W']);
      const here = side === 'E' ? model.w : side === 'S' ? model.d : 0;
      M.moveShell(model, side, here + (rand() - 0.5) * 24);
    } else if (action < 0.9) {
      M.scaleToArea(model, 600 + rand() * 4000);
    } else if (action < 0.95) {
      const side = pick(['N', 'E', 'S', 'W']);
      M.addOpening(model, level, side, rand() * M.sideLength(model, side), pick(['window', 'door']));
    } else if (model.openings.length) {
      const o = pick(model.openings);
      if (rand() < 0.5) M.moveOpening(model, o, rand() * 100); else M.resizeOpening(model, o, rand() * 30, pick([-1, 0, 1]));
    }
    edits += 1;
    const problems = M.check(model);
    assert.deepStrictEqual(problems, [], `trial ${trial}, step ${step}`);
    model.openings.forEach((o) => {
      const len = M.sideLength(model, o.side);
      assert(o.pos - o.width / 2 >= -1e-9 && o.pos + o.width / 2 <= len + 1e-9, 'opening stays on its wall');
    });
    // Glass handed to the engine must equal the glass drawn.
    const rooms = M.toEngineRooms(model);
    const engineGlass = rooms.reduce((a, r) => a + Object.values(r.windows).reduce((x, y) => x + y, 0), 0);
    assert(Math.abs(engineGlass - M.glassArea(model)) < 1e-6, 'all glass reaches the engine');
    const totalWall = rooms.reduce((a, r) => a + Object.values(r.walls).reduce((x, y) => x + y, 0), 0);
    assert(Math.abs(totalWall - model.stories * 2 * (model.w + model.d)) < 1e-6, 'exterior wall length matches the shell');
  }
}
console.log(`PASS: ${edits} random edits kept the model valid`);
