"""Parity: the JS classifier (app/model.js, run in Node) must give the same label + confidence as the Python
exported-model inference (models/kikuyu.py Exported) on a mixed sample. Run: python3 tests/parity.py"""
import json, os, random, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "models"))
from examples import EXAMPLES
from kikuyu import Exported
m = Exported(os.path.join(ROOT, "models", "model.json"))
texts = [t for ts in EXAMPLES.values() for t in ts]
texts += [l.strip() for l in open(os.path.join(ROOT, "data/raw/flores/dev/kik_Latn.dev"), encoding="utf-8")][:40]
texts += ["Mathangũ ma kahawa marĩ na mũtu", "BEI YA KAHAWA LEO??", "set an alarm", "", "é ü ñ ok"]
js = r"""
const M=require('./app/model.js');const fs=require('fs');
const m=M.load(JSON.parse(fs.readFileSync('models/model.json')));
const t=JSON.parse(fs.readFileSync(0));process.stdout.write(JSON.stringify(t.map(x=>{const r=m.predict(x);return [r.label,r.confidence]})));
"""
out = json.loads(subprocess.run(["node", "-e", js], input=json.dumps(texts), capture_output=True, text=True, cwd=ROOT, check=True).stdout)
bad = 0
for t, (lj, cj) in zip(texts, out):
    lp, cp = m.predict(t)
    if lp != lj or abs(cp - cj) > 1e-6:
        bad += 1; print("MISMATCH", repr(t), lp, cp, lj, cj)
print(f"parity: {len(texts) - bad}/{len(texts)} identical")
sys.exit(1 if bad else 0)
