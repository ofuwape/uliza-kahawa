"""Train the tiny on-device intent classifier and export it for the phone (models/model.json).

Model: hashed word + character n-gram features -> multinomial logistic regression (softmax). Weights are
quantized to int8 so the whole model is a few hundred KB and runs in plain JavaScript on a feature phone.
The exact same normalisation + hashing lives in app/model.js (tested against model.json's "selftest").

Data: models/examples.py (synthetic, hand-written) + typo augmentation; out-of-scope "none" examples are real
MASSIVE utterances (data/raw/massive). Metrics come from 5-fold cross-validation; the "not sure" threshold is
picked on those out-of-fold predictions. Standard library only.

  python3 models/train.py
"""
import base64
import json
import math
import os
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "models"))
from examples import EXAMPLES, NEAR_NONE  # noqa: E402

D = 1 << 14                      # hash buckets
SEED = 7
EPOCHS, LR, L2 = 40, 0.6, 1e-6
NONE = "none"
MASSIVE_SKIP = {"weather_query"}  # "will it rain" overlaps spray timing; keep it out of the negatives
OUT = os.path.join(ROOT, "models", "model.json")
REPORT = os.path.join(ROOT, "models", "report.md")


# ---------------------------------------------------------------- features (mirrored in app/model.js)
def normalize(text):
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))   # ĩ ũ -> i u (Kikuyu), é -> e
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def fnv1a(s):
    h = 0x811C9DC5
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def features(text):
    words = normalize(text).split()
    grams = ["w:" + w for w in words] + ["b:" + a + "_" + b for a, b in zip(words, words[1:])]
    for w in words:
        p = "#" + w + "#"
        for n in (2, 3, 4):
            grams += ["c:" + p[i:i + n] for i in range(len(p) - n + 1)]
    idx = sorted({fnv1a(g) % D for g in grams})
    v = 1.0 / math.sqrt(len(idx)) if idx else 0.0
    return idx, v


# ---------------------------------------------------------------- data
# Question frames farmers wrap around a topic. MASSIVE's off-topic set is full of "tell me about X", so without these
# the frame itself reads as off-topic ("tell me about leaf rust" fell below the threshold).
FRAMES = ["tell me about ", "what about ", "info on ", "help with ", "question about ", "i need help with ",
          "nieleze kuhusu ", "naomba habari ya ", "msaada na ", "swali kuhusu ", "nisaidie na ", "habari ya "]


def typo(s, rnd):
    if len(s) < 5:
        return s
    i = rnd.randrange(1, len(s) - 1)
    op = rnd.choice(("drop", "swap", "double"))
    if op == "drop":
        return s[:i] + s[i + 1:]
    if op == "swap":
        return s[:i] + s[i + 1] + s[i] + s[i + 2:]
    return s[:i] + s[i] + s[i:]


def massive(locale, n, rnd, skip_utts=()):
    path = os.path.join(ROOT, "data", "raw", "massive", f"{locale}.jsonl")
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    rows = [r["utt"] for r in rows if r["intent"] not in MASSIVE_SKIP and r["utt"] not in skip_utts]
    rnd.shuffle(rows)
    return rows[:n]


GEMINI = os.path.join(ROOT, "models", "examples_gemini.json")


def gemini_examples():
    if not os.path.exists(GEMINI):
        return []
    g = json.load(open(GEMINI, encoding="utf-8"))["examples"]
    return [(t, k) for k, ts in g.items() for t in ts if k in EXAMPLES]


def load(rnd):
    hand = [(t, k) for k, ts in EXAMPLES.items() for t in ts]
    neg = [(t, NONE) for t in massive("sw-KE", 200, rnd) + massive("en-US", 200, rnd)]
    near = [(t, NONE) for t in NEAR_NONE]
    rnd.shuffle(near)
    neg = near + neg          # near misses first, so the held-out split keeps most of them in training
    return hand, gemini_examples(), neg


# ---------------------------------------------------------------- model
class Softmax:
    def __init__(self, labels):
        self.labels = labels
        self.K = len(labels)
        self.W = defaultdict(lambda: [0.0] * self.K)
        self.b = [0.0] * self.K

    def scores(self, idx, v):
        s = list(self.b)
        for f in idx:
            w = self.W.get(f)
            if w:
                for k in range(self.K):
                    s[k] += w[k] * v
        return s

    @staticmethod
    def softmax(s):
        m = max(s)
        e = [math.exp(x - m) for x in s]
        z = sum(e)
        return [x / z for x in e]

    def fit(self, X, y, rnd, weights):
        order = list(range(len(X)))
        for ep in range(EPOCHS):
            rnd.shuffle(order)
            lr = LR / (1 + ep * 0.15)
            for i in order:
                idx, v = X[i]
                p = self.softmax(self.scores(idx, v))
                p[y[i]] -= 1.0
                g = weights[y[i]]
                for k in range(self.K):
                    self.b[k] -= lr * g * p[k]
                for f in idx:
                    w = self.W[f]
                    for k in range(self.K):
                        w[k] -= lr * (g * p[k] * v + L2 * w[k])

    def predict(self, idx, v):
        p = self.softmax(self.scores(idx, v))
        k = max(range(self.K), key=p.__getitem__)
        return k, p[k]


def train(data, labels, rnd, augment=True):
    L = {l: i for i, l in enumerate(labels)}
    rows = []
    for t, k in data:
        rows.append((t, k))
        if augment and k != NONE:
            rows += [(typo(t, rnd), k), (typo(typo(t, rnd), rnd), k), (rnd.choice(FRAMES) + t, k)]
    X = [features(t) for t, _ in rows]
    y = [L[k] for _, k in rows]
    cnt = Counter(y)
    weights = {c: len(y) / (len(cnt) * n) for c, n in cnt.items()}
    m = Softmax(labels)
    m.fit(X, y, rnd, weights)
    return m


# ---------------------------------------------------------------- evaluation
def crossval(data, labels, folds=5):
    rnd = random.Random(SEED)
    items = list(data)
    rnd.shuffle(items)
    by = defaultdict(list)
    for i, (t, k) in enumerate(items):
        by[k].append(i)
    fold_of = {}
    for k, ids in by.items():                      # stratified
        for j, i in enumerate(ids):
            fold_of[i] = j % folds
    oof = []
    for f in range(folds):
        tr = [items[i] for i in range(len(items)) if fold_of[i] != f]
        te = [items[i] for i in range(len(items)) if fold_of[i] == f]
        m = train(tr, labels, random.Random(SEED + f))
        for t, k in te:
            pk, conf = m.predict(*features(t))
            oof.append((t, k, labels[pk], conf))
        print(f"  fold {f + 1}/{folds} done", flush=True)
    return oof


def score(oof, thr):
    """Answered = top label is an intent and conf >= thr. Correct if answered right, or a 'none' was not answered."""
    inn = [r for r in oof if r[1] != NONE]
    out = [r for r in oof if r[1] == NONE]
    ans = lambda r: r[2] != NONE and r[3] >= thr
    right = sum(1 for r in inn if ans(r) and r[2] == r[1])
    wrong = sum(1 for r in inn if ans(r) and r[2] != r[1])
    deferred = sum(1 for r in inn if not ans(r))
    rejected = sum(1 for r in out if not ans(r))
    return {"in_scope": len(inn), "right": right, "wrong": wrong, "deferred": deferred,
            "out_scope": len(out), "rejected": rejected,
            "accuracy_answered": right / max(1, right + wrong), "coverage": (right + wrong) / max(1, len(inn)),
            "out_rejected": rejected / max(1, len(out))}


def pick_threshold(oof):
    """Lowest threshold that keeps wrong answers on in-scope questions <= 3% and false answers to 'none' <= 5%."""
    best = None
    for t in [x / 100 for x in range(20, 96, 2)]:
        s = score(oof, t)
        ok = s["accuracy_answered"] >= 0.97 and s["out_rejected"] >= 0.95
        if ok and best is None:
            best = (t, s)
    if best is None:
        t = 0.9
        best = (t, score(oof, t))
    return best


# ---------------------------------------------------------------- export
def export(m, labels, thr, metrics, n_train):
    scale = max((abs(x) for w in m.W.values() for x in w), default=1.0) / 127.0
    flat = bytearray(D * m.K)
    for f, w in m.W.items():
        for k in range(m.K):
            q = int(round(w[k] / scale))
            flat[f * m.K + k] = max(-127, min(127, q)) & 0xFF
    tests = ["majani yana unga wa njano chini", "bei ya kahawa leo", "set an alarm for six am", "my berries have holes"]
    selftest = []
    for t in tests:
        k, c = m.predict(*features(t))
        selftest.append({"text": t, "label": labels[k], "features": features(t)[0][:8]})
    model = {"version": "2026-10-03", "D": D, "labels": labels, "none": NONE, "threshold": thr,
             "features": "normalize: lowercase, NFKD, drop combining marks, [^a-z0-9]+ -> space; grams: w:word, "
                         "b:w1_w2, c:char n-grams n=2..4 of #word#; FNV-1a 32 over UTF-8 mod D; binary, L2-normalized",
             "scale": scale, "bias": m.b, "W_int8_b64": base64.b64encode(bytes(flat)).decode(),
             "layout": "row-major [feature][label], int8 two's complement", "trained_on": n_train,
             "metrics": metrics, "selftest": selftest}
    json.dump(model, open(OUT, "w"))
    return os.path.getsize(OUT)


def main():
    rnd = random.Random(SEED)
    hand, gem, neg = load(rnd)
    data = hand + gem + neg
    labels = list(EXAMPLES) + [NONE]
    n_int = len(hand) + len(gem)
    print(f"{len(hand)} hand-written + {len(gem)} Gemini intent examples ({len(EXAMPLES)} intents) + {len(neg)} MASSIVE 'none'")

    # Held-out check: train on Gemini examples + 80% of 'none', test on the hand-written examples it never saw.
    cut = int(len(neg) * 0.8)
    held = None
    if gem:
        mh = train(gem + neg[:cut], labels, random.Random(SEED))
        held = [(t, k, labels[pk], c) for t, k in hand + neg[cut:] for pk, c in [mh.predict(*features(t))]]
    print("5-fold cross-validation ...")
    oof = crossval(data, labels)
    thr, s = pick_threshold(oof)
    print(f"threshold {thr}: answered accuracy {s['accuracy_answered']:.1%}, coverage {s['coverage']:.1%}, "
          f"out-of-scope rejected {s['out_rejected']:.1%}")
    h = score(held, thr) if held else None
    if h:
        print(f"held-out (hand-written, never trained on): answered accuracy {h['accuracy_answered']:.1%}, "
              f"coverage {h['coverage']:.1%}, out-of-scope rejected {h['out_rejected']:.1%}")

    conf = defaultdict(Counter)
    for t, k, p, c in oof:
        conf[k][p if (p == NONE or c >= thr) else "not_sure"] += 1
    errors = [(t, k, p, round(c, 2)) for t, k, p, c in oof if k != p and c >= thr and p != NONE]

    print("training the final model on everything ...")
    m = train(data, labels, random.Random(SEED))
    size = export(m, labels, thr, s, len(data))
    print(f"model.json {size / 1024:.0f} KB")

    lines = ["# Text model report", "",
             f"Model: hashed word + char 2-4 gram features (D={D}) -> softmax, int8 weights. File: models/model.json "
             f"({size / 1024:.0f} KB).", "",
             f"Data: {len(hand)} hand-written + {len(gem)} Gemini-generated synthetic intent examples (Kiswahili, English, "
             f"mixed / Sheng / typos) + typo augmentation; {len(neg)} real out-of-scope utterances from MASSIVE sw-KE + "
             f"en-US + {len(NEAR_NONE)} hand-written farm near misses (other crops, livestock, antestia) as 'none'.", "",
             "## Held-out check (the honest number)", "",
             (f"Trained on the Gemini examples only, tested on the {len(hand)} hand-written ones (different authors, never "
              f"seen) + {len(neg) - cut} unseen MASSIVE messages: answered accuracy {h['accuracy_answered']:.1%}, coverage "
              f"{h['coverage']:.1%} (right {h['right']}, wrong {h['wrong']}, not sure {h['deferred']}), off-topic not "
              f"answered {h['out_rejected']:.1%}." if h else "n/a"), "",
             f"## 5-fold cross-validation (threshold {thr})", "",
             f"- In-scope questions: {s['in_scope']}; answered right {s['right']}, answered wrong {s['wrong']}, "
             f"sent to 'not sure' {s['deferred']}",
             f"- Accuracy when it answers: {s['accuracy_answered']:.1%}; coverage: {s['coverage']:.1%}",
             f"- Out-of-scope messages: {s['out_scope']}; correctly not answered {s['rejected']} ({s['out_rejected']:.1%})", "",
             "Threshold rule: the lowest confidence that keeps wrong answers <= 3% and answers to off-topic messages <= 5%; "
             "below it the farmer gets 'not sure, saved for the extension officer'.", "",
             "## Per intent (out-of-fold)", "", "| intent | n | right | not sure | wrong |", "|---|---|---|---|---|"]
    for k in labels:
        c = conf[k]
        n = sum(c.values())
        lines.append(f"| {k} | {n} | {c[k]} | {c['not_sure'] + (c[NONE] if k != NONE else 0)} | "
                     f"{n - c[k] - c['not_sure'] - (c[NONE] if k != NONE else 0)} |")
    lines += ["", "## Wrong answers above the threshold (out-of-fold)", ""]
    lines += [f"- \"{t}\" ({k}) -> {p} @ {c}" for t, k, p, c in errors[:30]] or ["- none"]
    lines += ["", "## Limits", "",
              "- Training questions are synthetic: written by the team, not collected from farmers. Real messages will be "
              "messier; the 'not sure' route is the safety net.",
              "- Kiswahili and English only in training. Kikuyu is tested separately (see below) and is expected to do worse.",
              "- Cross-validation on synthetic data overstates real-world accuracy."]
    open(REPORT, "w").write("\n".join(lines) + "\n")
    print(f"report -> {os.path.relpath(REPORT, ROOT)}")


if __name__ == "__main__":
    main()
