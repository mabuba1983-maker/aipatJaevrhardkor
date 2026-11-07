/* Measures the REAL CPU share of the web trainer's worker loop: the same source the page runs, in a fake worker environment, with the real model weights.
 * usage: node tools/measure_throttle.js <engine_full.js> <seconds per setting> <pct> [<pct> ...] */
const fs = require('fs'), vm = require('vm');
const E = require(process.argv[2]), secs = +process.argv[3], pcts = process.argv.slice(4).map(Number);
const src = fs.readFileSync(__dirname + '/ui_trainer.js', 'utf8');
const corpus = fs.readFileSync(__dirname + '/../android/app/src/main/assets/train.txt', 'utf8');
(async () => {
  for (const pct of pcts) {
    const msgs = []; const g = { importScripts() {}, postMessage: m => msgs.push(m), performance, setTimeout, console, Math, Float32Array, Promise, Object, Map };
    g.self = g; vm.createContext(g); vm.runInContext(src, g);
    const P = {}; for (const [k, v] of Object.entries(E.params())) P[k] = v.slice();
    g.onmessage({ data: { type: 'init', P, D: E.dims(), chars: E.chars, corpus } });
    g.onmessage({ data: { type: 'start', pct } });
    const c0 = process.cpuUsage(), t0 = Date.now(); await new Promise(r => setTimeout(r, secs * 1000));
    const cpu = process.cpuUsage(c0), wall = (Date.now() - t0) * 1000; g.onmessage({ data: { type: 'stop' } }); await new Promise(r => setTimeout(r, 3500));
    const prog = msgs.filter(m => m.type === 'progress').pop();
    console.log(`asked ${pct}% -> measured CPU share of one core: ${((cpu.user + cpu.system) / wall * 100).toFixed(1)}%  (steps so far ${prog ? prog.steps : 0})`);
  }
  process.exit(0);
})();
