"""Would a simpler tool do the same job? Compare an SMS keyword menu (the usual non-AI approach) with the small model
on messages neither has seen.

Keyword menu: each topic has a list of keywords (Kiswahili + English, written generously, with sight of our examples,
which favours it); a message gets the topic with the most keyword hits, nothing on zero hits or a tie.
Model: the same pipeline as train.py, trained on the Gemini examples + 80% of the off-topic set (the hand-written
examples and the rest of the off-topic set are held out), with the exported threshold.

Test sets:
  clean      the 258 hand-written examples (different authors from the training data)
  typos      the same messages with 1-2 seeded typos each (how people really type on a keypad)
  off-topic  held-out MASSIVE messages + 300 real Kikuyu sentences (FLORES-200): any answer is wrong

  python3 models/baseline.py      -> prints the table and writes models/baseline.md
"""
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "models"))
import train as T  # noqa: E402
from examples import EXAMPLES  # noqa: E402

KEYWORDS = {
    "leaf_rust": "kutu rust unga powder machungwa orange chungwa njano yellow spots madoa".split(),
    "cbd": "cbd meusi nyeusi black jeusi kuoza rotting rot mummified".split(),
    "berry_borer": "tundu matundu holes hole borer mashimo mdudu beetle wadudu insects bugs".split(),
    "spray_timing": "dawa spray nyunyiza kunyunyiza copper shaba fungicide lini when".split(),
    "yield_drop": "mavuno yield yamepungua kidogo less fewer haizai producing dropped".split(),
    "fertilizer_weeds": "mbolea fertilizer manure samadi magugu weeds weeding palilia mulch matandazo udongo soil".split(),
    "pruning": "pogoa kupogoa prune pruning stump stumping matawi branches mizee old".split(),
    "harvest": "chuma kuchuma pick picking ripe nyekundu red mavuno harvest".split(),
    "quality": "daraja grade quality ubora sort sorting panga chafu clean".split(),
    "price": "bei price pesa money bob shillings broker mnunuzi buyer malipo payment pay sell uuze".split(),
    "varieties": "ruiru batian aina variety varieties miche seedlings kinga resistant".split(),
    "ask_person": "afisa officer mtu person someone nipigie call ongea talk expert mtaalamu".split(),
}


def keyword(text):
    words = set(T.normalize(text).split())
    hits = {k: len(words & set(v)) for k, v in KEYWORDS.items()}
    best = max(hits.values())
    top = [k for k, n in hits.items() if n == best]
    return top[0] if best > 0 and len(top) == 1 else None


def evaluate(predict, rows):
    """rows: (text, gold or None for off-topic) -> right / wrong / not answered"""
    right = wrong = none = 0
    for text, gold in rows:
        p = predict(text)
        if p is None:
            none += 1
        elif gold is not None and p == gold:
            right += 1
        else:
            wrong += 1
    return right, wrong, none


def main():
    rnd = random.Random(T.SEED)
    hand, gem, neg = T.load(rnd)
    labels = list(EXAMPLES) + [T.NONE]
    cut = int(len(neg) * 0.8)
    print("training the comparison model (Gemini examples + 80% off-topic) ...")
    m = T.train(gem + neg[:cut], labels, random.Random(T.SEED))
    thr = json.load(open(os.path.join(ROOT, "models", "model.json")))["threshold"]

    def model(text):
        k, c = m.predict(*T.features(text))
        return labels[k] if labels[k] != T.NONE and c >= thr else None

    def options(text):
        """The 'did you mean' topics the product would offer (same rule as app/channels.js), or []."""
        p = m.softmax(m.scores(*T.features(text)))
        top = sorted(((p[i], labels[i]) for i in range(len(labels))), reverse=True)[:3]
        if top[0][1] == T.NONE or (top[0][1] != T.NONE and top[0][0] >= thr):
            return []
        c = [l for q, l in top if l not in (T.NONE, "ask_person") and q >= 0.15 and q >= top[0][0] / 3]
        return c if c and top[0][0] >= 0.3 else []

    trnd = random.Random(99)
    clean = [(t, k) for t, k in hand]
    typos = [(T.typo(T.typo(t, trnd), trnd) if len(t) > 8 else T.typo(t, trnd), k) for t, k in hand]
    flores = [l.strip() for l in open(os.path.join(ROOT, "data/raw/flores/dev/kik_Latn.dev"), encoding="utf-8")][:300]
    off = [(t, None) for t, _ in neg[cut:]] + [(t, None) for t in flores]

    rows = []
    for name, data in (("clean", clean), ("typos", typos), ("off-topic", off)):
        for who, f in (("keyword menu", keyword), ("small model", model)):
            r, w, n = evaluate(f, data)
            # model only: unanswered messages where "did you mean" offers the right topic (one tap away)
            tap = sum(1 for t, g in data if g and f(t) is None and g in options(t)) if who == "small model" else None
            rows.append((name, who, len(data), r, w, n, tap))

    lines = ["# Would a keyword SMS menu do the same job?", "",
             "Same unseen messages for both. Off-topic rows: every answer is a wrong answer.", "",
             "| test set | tool | messages | right | WRONG | not answered | of which 'did you mean' offers the right topic |",
             "|---|---|---|---|---|---|---|"]
    for name, who, n, r, w, x, tap in rows:
        lines.append(f"| {name} | {who} | {n} | {r} ({r / n:.0%}) | {w} ({w / n:.0%}) | {x} ({x / n:.0%}) | "
                     f"{'n/a' if tap is None else f'{tap} ({tap / n:.0%})'} |")
    get = {(n, w): (r, wr, tap) for n, w, _, r, wr, _, tap in rows}
    for name, data in (("clean", clean), ("typos", typos)):
        kr, kw, _ = get[(name, "keyword menu")]
        mr, mw, mt = get[(name, "small model")]
        n = len(data)
        lines.append(f"\n**{name}:** right answer directly or in one tap: small model {(mr + mt) / n:.0%} vs keyword menu "
                     f"{kr / n:.0%}; wrong answers: {mw / n:.0%} vs {kw / n:.0%}.")
    lines += ["", "The keyword lists were written with sight of the examples, which favours the keyword menu. The model never",
              "saw the hand-written messages. 'Not answered' is the safe outcome (the question goes to a person);",
              "'wrong' is the costly one (a confident answer about the wrong problem)."]
    out = "\n".join(lines)
    print(out)
    open(os.path.join(ROOT, "models", "baseline.md"), "w").write(out + "\n")


if __name__ == "__main__":
    main()
