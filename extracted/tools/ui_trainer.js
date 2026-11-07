/* Nuwaa web trainer: back-propagation through time for the same 2-layer GRU the page runs, plus the Web Worker that trains in the background at the CPU
 * share the user picks. Mirror of nuwaa/lm/gru.py (equations, gate order [r|z|n], layout). Verified against numpy and by finite differences (tests/test_web.py). */
function makeTrainer(P, D, FA) {
  const Em = D.E, H = D.H, V = D.V, H3 = 3 * H, names = ['PE', 'Wx1', 'Wh1', 'b1', 'Wx2', 'Wh2', 'b2', 'Wo', 'bo'];
  const G = {}, M = {}, W = {}; for (const k of names) { G[k] = new FA(P[k].length); M[k] = new FA(P[k].length); W[k] = new FA(P[k].length); }
  let t = 0;
  const sg = x => 1 / (1 + Math.exp(-x));
  function cellF(gx, hp, Wh) {
    const tmp = new FA(2 * H); for (let j = 0; j < 2 * H; j++) tmp[j] = gx[j];
    for (let q = 0; q < H; q++) { const hv = hp[q]; if (hv === 0) continue; const o = q * H3; for (let j = 0; j < 2 * H; j++) tmp[j] += hv * Wh[o + j]; }
    const r = new FA(H), z = new FA(H), rh = new FA(H), an = new FA(H), n = new FA(H), h = new FA(H);
    for (let j = 0; j < H; j++) { r[j] = sg(tmp[j]); z[j] = sg(tmp[H + j]); rh[j] = r[j] * hp[j]; an[j] = gx[2 * H + j]; }
    for (let q = 0; q < H; q++) { const v = rh[q]; if (v === 0) continue; const o = q * H3 + 2 * H; for (let j = 0; j < H; j++) an[j] += v * Wh[o + j]; }
    for (let j = 0; j < H; j++) { n[j] = Math.tanh(an[j]); h[j] = (1 - z[j]) * hp[j] + z[j] * n[j]; }
    return { r, z, n, rh, h, hp };
  }
  function cellB(c, dh, Wh, GWh) {   // returns { dgx (3H), dhp }
    const dgx = new FA(H3), dhp = new FA(H), drh = new FA(H);
    for (let j = 0; j < H; j++) { const dz = dh[j] * (c.n[j] - c.hp[j]), dn = dh[j] * c.z[j]; dhp[j] = dh[j] * (1 - c.z[j]); dgx[H + j] = dz * c.z[j] * (1 - c.z[j]); dgx[2 * H + j] = dn * (1 - c.n[j] * c.n[j]); }
    for (let q = 0; q < H; q++) {          // candidate part: d(rh) = Wh_n @ da_n ; dWh_n += rh (x) da_n
      const o = q * H3 + 2 * H, rq = c.rh[q]; let s = 0;
      for (let j = 0; j < H; j++) { const d = dgx[2 * H + j]; GWh[o + j] += rq * d; s += Wh[o + j] * d; }
      drh[q] = s;
    }
    for (let q = 0; q < H; q++) { dgx[q] = drh[q] * c.hp[q] * c.r[q] * (1 - c.r[q]); dhp[q] += drh[q] * c.r[q]; }
    for (let q = 0; q < H; q++) {          // gates r,z: dWh_rz += h (x) da_rz ; dh += Wh_rz @ da_rz
      const o = q * H3, hv = c.hp[q]; let s = 0;
      for (let j = 0; j < 2 * H; j++) { const d = dgx[j]; GWh[o + j] += hv * d; s += Wh[o + j] * d; }
      dhp[q] += s;
    }
    return { dgx, dhp };
  }
  /** Mean cross-entropy (nats per character) of ids[1..] given ids[..-1], from a zero state. With grad=true the gradients are left in G. */
  function lossAndGrad(ids, grad = true) {
    const T = ids.length - 1; if (grad) for (const k of names) G[k].fill(0);
    const c1 = [], c2 = [], probs = []; let h1 = new FA(H), h2 = new FA(H), loss = 0;
    for (let s = 0; s < T; s++) {
      const id = ids[s], g1 = new FA(H3); for (let j = 0; j < H3; j++) g1[j] = P.b1[j];
      for (let q = 0; q < Em; q++) { const ev = P.PE[id * Em + q], o = q * H3; for (let j = 0; j < H3; j++) g1[j] += ev * P.Wx1[o + j]; }
      const a = cellF(g1, h1, P.Wh1); h1 = a.h; c1.push(a);
      const g2 = new FA(H3); for (let j = 0; j < H3; j++) g2[j] = P.b2[j];
      for (let q = 0; q < H; q++) { const hv = h1[q]; if (hv === 0) continue; const o = q * H3; for (let j = 0; j < H3; j++) g2[j] += hv * P.Wx2[o + j]; }
      const b = cellF(g2, h2, P.Wh2); b.x = h1; h2 = b.h; c2.push(b);
      const p = new FA(V); for (let j = 0; j < V; j++) p[j] = P.bo[j];
      for (let q = 0; q < H; q++) { const hv = h2[q]; if (hv === 0) continue; const o = q * V; for (let j = 0; j < V; j++) p[j] += hv * P.Wo[o + j]; }
      let mx = -1e300; for (let j = 0; j < V; j++) if (p[j] > mx) mx = p[j];
      let sum = 0; for (let j = 0; j < V; j++) { p[j] = Math.exp(p[j] - mx); sum += p[j]; } for (let j = 0; j < V; j++) p[j] /= sum;
      loss -= Math.log(p[ids[s + 1]] + 1e-9); if (grad) probs.push(p);
    }
    if (!grad) return loss / T;
    let dh1n = new FA(H), dh2n = new FA(H);
    for (let s = T - 1; s >= 0; s--) {
      const dl = probs[s]; dl[ids[s + 1]] -= 1; for (let j = 0; j < V; j++) dl[j] /= T;
      const h2s = c2[s].h, dh2 = new FA(H); for (let q = 0; q < H; q++) dh2[q] = dh2n[q];
      for (let q = 0; q < H; q++) { const hv = h2s[q], o = q * V; let sm = 0; for (let j = 0; j < V; j++) { G.Wo[o + j] += hv * dl[j]; sm += P.Wo[o + j] * dl[j]; } dh2[q] += sm; }
      for (let j = 0; j < V; j++) G.bo[j] += dl[j];
      const r2 = cellB(c2[s], dh2, P.Wh2, G.Wh2); dh2n = r2.dhp;
      const x2 = c2[s].x, dx = new FA(H); for (let j = 0; j < H3; j++) G.b2[j] += r2.dgx[j];
      for (let q = 0; q < H; q++) { const xv = x2[q], o = q * H3; let sm = 0; for (let j = 0; j < H3; j++) { G.Wx2[o + j] += xv * r2.dgx[j]; sm += P.Wx2[o + j] * r2.dgx[j]; } dx[q] = sm; }
      const dh1 = new FA(H); for (let q = 0; q < H; q++) dh1[q] = dh1n[q] + dx[q];
      const r1 = cellB(c1[s], dh1, P.Wh1, G.Wh1); dh1n = r1.dhp;
      for (let j = 0; j < H3; j++) G.b1[j] += r1.dgx[j];
      const id = ids[s]; for (let q = 0; q < Em; q++) { const ev = P.PE[id * Em + q], o = q * H3; let sm = 0; for (let j = 0; j < H3; j++) { G.Wx1[o + j] += ev * r1.dgx[j]; sm += P.Wx1[o + j] * r1.dgx[j]; } G.PE[id * Em + q] += sm; }
    }
    return loss / T;
  }
  function adam(lr, clip = 1) {
    let n2 = 0; for (const k of names) { const g = G[k]; for (let i = 0; i < g.length; i++) n2 += g[i] * g[i]; }
    const sc = n2 > clip * clip ? clip / Math.sqrt(n2) : 1; t++; const c1 = 1 - Math.pow(.9, t), c2 = 1 - Math.pow(.999, t);
    for (const k of names) { const g = G[k], m = M[k], v = W[k], p = P[k];
      for (let i = 0; i < g.length; i++) { const gi = g[i] * sc; m[i] = .9 * m[i] + .1 * gi; v[i] = .999 * v[i] + .001 * gi * gi; p[i] -= lr * (m[i] / c1) / (Math.sqrt(v[i] / c2) + 1e-8); } }
  }
  return { lossAndGrad, adam, evalLoss: ids => lossAndGrad(ids, false), grads: G, names };
}

/* ---- Web Worker glue: runs only inside a worker; the page builds the worker from this very file ---- */
if (typeof importScripts === 'function') {
  let T = null, P = null, D = null, idm = new Map(), pairs = [], heldIds = [], extra = [], run = false, pct = 40, steps = 0, lr = 1e-3, ema = null, best = Infinity, snap = null, rollbacks = 0, startHeld = 0, stepMs = 0;
  const enc = s => { const a = []; for (const ch of s) a.push(idm.has(ch) ? idm.get(ch) : 1); return a; };
  const copyP = () => { const o = {}; for (const k in P) o[k] = P[k].slice(); return o; };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  onmessage = e => {
    const m = e.data;
    if (m.type === 'init') {
      P = m.P; D = m.D; T = makeTrainer(P, D, Float32Array); idm = new Map(m.chars.map((c, i) => [c, i]));
      const all = m.corpus.split('\n').filter(l => l.length > 6).map(l => l.replace('\t', '\n') + '\n');
      pairs = all.filter((_, i) => i % 53 !== 7); const held = all.filter((_, i) => i % 53 === 7).slice(0, 10); heldIds = enc('\n' + held.join(''));
      best = T.evalLoss(heldIds); startHeld = best; snap = copyP(); postMessage({ type: 'ready', held: best / Math.LN2, pairs: pairs.length });
    } else if (m.type === 'start') { pct = m.pct; if (!run) { run = true; loop(); } }
    else if (m.type === 'pct') pct = m.pct;
    else if (m.type === 'stop') run = false;
    else if (m.type === 'extra') { extra.push(m.text); if (extra.length > 60) extra.shift(); }
  };
  async function loop() {
    while (run) {
      const t0 = performance.now(); let s = '\n';
      while (s.length < 100) s += (extra.length && Math.random() < .2) ? extra[Math.floor(Math.random() * extra.length)] : pairs[Math.floor(Math.random() * pairs.length)];
      const loss = T.lossAndGrad(enc(s.slice(0, 128))); T.adam(lr); steps++; ema = ema === null ? loss : .98 * ema + .02 * loss;
      const busy = performance.now() - t0; stepMs = stepMs ? (stepMs * 9 + busy) / 10 : busy;
      if (steps % 40 === 0) {
        const h = T.evalLoss(heldIds);
        if (h <= best) { best = h; snap = copyP(); const out = copyP(); postMessage({ type: 'weights', P: out, held: h / Math.LN2 }, Object.values(out).map(a => a.buffer)); }
        else if (h > best * 1.03) { for (const k in P) P[k].set(snap[k]); lr = Math.max(lr * .5, 1e-4); rollbacks++; }
      }
      if (steps % 3 === 0) postMessage({ type: 'progress', steps, loss: ema / Math.LN2, held: best / Math.LN2, startHeld: startHeld / Math.LN2, rollbacks, stepMs, lr });
      const work = performance.now() - t0, pc = Math.min(100, Math.max(5, pct)); await sleep(pc < 100 ? work * (100 - pc) / pc : 0);   // everything counts, the measurement included
    }
    for (const k in P) P[k].set(snap[k]);              // always end on the best state: pressing stop can never leave the model worse
    const out = copyP(); postMessage({ type: 'stopped', P: out, held: best / Math.LN2, startHeld: startHeld / Math.LN2, steps }, Object.values(out).map(a => a.buffer));
  }
}
if (typeof module !== 'undefined') module.exports = { makeTrainer };
