// On-device intent classifier: the exact maths of models/train.py (normalise, FNV-1a hashed n-grams, int8 softmax).
// Runs in any browser (KaiOS included) and in Node for the parity test. No dependencies, no network after load.
(function (root) {
  function normalize(text) {
    return String(text || '').toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9]+/g, ' ').trim();
  }

  function fnv1a(s) {
    const bytes = new TextEncoder().encode(s);
    let h = 0x811c9dc5;
    for (let i = 0; i < bytes.length; i++) {
      h ^= bytes[i];
      h = Math.imul(h, 0x01000193) >>> 0;
    }
    return h >>> 0;
  }

  function features(text, D) {
    const words = normalize(text).split(' ').filter(Boolean);
    const grams = words.map(w => 'w:' + w);
    for (let i = 0; i + 1 < words.length; i++) grams.push('b:' + words[i] + '_' + words[i + 1]);
    for (const w of words) {
      const p = '#' + w + '#';
      for (const n of [2, 3, 4]) for (let i = 0; i + n <= p.length; i++) grams.push('c:' + p.slice(i, i + n));
    }
    const idx = [...new Set(grams.map(g => fnv1a(g) % D))].sort((a, b) => a - b);
    return {idx, v: idx.length ? 1 / Math.sqrt(idx.length) : 0};
  }

  function load(model) {
    const bin = typeof atob === 'function' ? atob(model.W_int8_b64) : Buffer.from(model.W_int8_b64, 'base64').toString('binary');
    const W = new Int8Array(bin.length);
    for (let i = 0; i < bin.length; i++) W[i] = bin.charCodeAt(i) << 24 >> 24;
    const K = model.labels.length;
    return {
      labels: model.labels, threshold: model.threshold, none: model.none, bytes: W.length,
      // -> {label, confidence, answered, top: [{label, p}...]}
      predict(text) {
        const {idx, v} = features(text, model.D);
        const s = model.bias.slice();
        for (const f of idx) {
          const base = f * K;
          for (let k = 0; k < K; k++) s[k] += W[base + k] * model.scale * v;
        }
        const mx = Math.max(...s);
        const e = s.map(x => Math.exp(x - mx));
        const z = e.reduce((a, b) => a + b, 0);
        const top = e.map((x, k) => ({label: model.labels[k], p: x / z})).sort((a, b) => b.p - a.p);
        const best = top[0];
        return {label: best.label, confidence: best.p, top: top.slice(0, 3),
                answered: best.label !== model.none && best.p >= model.threshold};
      },
    };
  }

  const api = {normalize, fnv1a, features, load};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.SmallModel = api;
})(this);
