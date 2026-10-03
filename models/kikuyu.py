"""The less-supported language test (Kikuyu), run against the EXPORTED int8 model (models/model.json), so it also
checks the export the phone uses.

1. In-scope: hand-written Kiswahili examples machine-translated to Kikuyu by Gemini (build time; UNVERIFIED by a
   Kikuyu speaker, so treat results as indicative). Cached in models/kikuyu_test.json.
2. Off-topic: 300 real Kikuyu sentences from FLORES-200 (news / wiki): the model must NOT answer them.

  python3 models/kikuyu.py --env ../whatsapp-agent/cdk/.env      # translate once, then evaluate
"""
import argparse
import base64
import json
import math
import os
import re
import sys
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "models"))
from examples import EXAMPLES  # noqa: E402
from train import features  # noqa: E402

MODEL_FILE = os.path.join(ROOT, "models", "model.json")
TEST = os.path.join(ROOT, "models", "kikuyu_test.json")
FLORES = os.path.join(ROOT, "data", "raw", "flores", "dev", "kik_Latn.dev")
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"


class Exported:
    """Same maths as app/model.js: int8 weights * scale, softmax."""
    def __init__(self, path):
        m = json.load(open(path))
        self.labels, self.K, self.thr, self.scale, self.b = m["labels"], len(m["labels"]), m["threshold"], m["scale"], m["bias"]
        raw = base64.b64decode(m["W_int8_b64"])
        self.W = [x - 256 if x > 127 else x for x in raw]

    def predict(self, text):
        idx, v = features(text)
        s = list(self.b)
        for f in idx:
            base = f * self.K
            for k in range(self.K):
                s[k] += self.W[base + k] * self.scale * v
        mx = max(s)
        e = [math.exp(x - mx) for x in s]
        z = sum(e)
        k = max(range(self.K), key=lambda i: e[i])
        return self.labels[k], e[k] / z


def translate(env):
    k = os.environ.get("GOOGLE_GENAI_API_KEY")
    if not k and env:
        k = next((l.split("=", 1)[1].strip().strip('"') for l in open(env) if l.startswith("GOOGLE_GENAI_API_KEY=")), None)
    if not k:
        sys.exit("set GOOGLE_GENAI_API_KEY or pass --env")
    sw = {i: [t for t in ts if not re.search(r"[a-z]+ing\b|\bmy\b|\bthe\b", t)][:6] for i, ts in EXAMPLES.items()}
    prompt = ("Translate each farmer message into Gikuyu (Kikuyu) as a farmer in Nyeri would text it. Keep the meaning. "
              "Return ONLY a JSON object with the same keys, each a list of translations in the same order.\n"
              + json.dumps(sw, ensure_ascii=False))
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}}
    d = json.load(urlopen(Request(f"{URL}?key={k}", data=json.dumps(body).encode(),
                                  headers={"Content-Type": "application/json"}), timeout=300))
    out = json.loads("".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"]))
    json.dump({"_about": "Gemini 2.5 Pro translations of hand-written Kiswahili examples. UNVERIFIED by a Kikuyu speaker.",
               "source_sw": sw, "kikuyu": out}, open(TEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env")
    a = ap.parse_args()
    if not os.path.exists(TEST):
        translate(a.env)
    m = Exported(MODEL_FILE)
    kik = json.load(open(TEST, encoding="utf-8"))["kikuyu"]
    rows = [(t, i) for i, ts in kik.items() for t in ts]
    right = wrong = unsure = 0
    misses = []
    for t, i in rows:
        lab, c = m.predict(t)
        if lab != "none" and c >= m.thr:
            if lab == i:
                right += 1
            else:
                wrong += 1
                misses.append((t, i, lab, round(c, 2)))
        else:
            unsure += 1
    fl = [l.strip() for l in open(FLORES, encoding="utf-8")][:300]
    false_ans = [(t, *m.predict(t)) for t in fl]
    false_ans = [(t, l, c) for t, l, c in false_ans if l != "none" and c >= m.thr]

    # self-test: exported model agrees with the training-time predictions stored in model.json
    st = json.load(open(MODEL_FILE))["selftest"]
    agree = sum(1 for s in st if m.predict(s["text"])[0] == s["label"])

    n = len(rows)
    lines = ["", "## Kikuyu (less-supported language)", "",
             f"- In-scope: {n} Kikuyu messages (Gemini translations of our Kiswahili examples, unverified): right {right}, "
             f"wrong {wrong}, not sure {unsure} -> answered accuracy {right / max(1, right + wrong):.0%}, coverage "
             f"{(right + wrong) / max(1, n):.0%}.",
             f"- Off-topic: {len(fl)} real Kikuyu sentences (FLORES-200): answered by mistake {len(false_ans)} "
             f"({len(false_ans) / len(fl):.1%}).",
             "- The model never saw Kikuyu in training; it only catches words shared with Kiswahili / English (e.g. "
             "kahawa / kahũa, loanwords). The safe failure is 'not sure', which sends the question to a person.",
             f"- Export check: the int8 model reproduces {agree}/{len(st)} stored predictions."]
    if misses:
        lines += ["", "Wrong Kikuyu answers:"] + [f"- \"{t}\" ({i}) -> {l} @ {c}" for t, i, l, c in misses[:10]]
    print("\n".join(lines))
    rep = os.path.join(ROOT, "models", "report.md")
    body = open(rep).read().split("\n## Kikuyu")[0].rstrip()
    open(rep, "w").write(body + "\n" + "\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
