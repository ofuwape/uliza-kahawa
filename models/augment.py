"""Build-time only: generate extra SYNTHETIC training messages per intent with Gemini (never used in the app).

For each intent: the answer it maps to + our hand-written examples -> ~40 new short farmer messages
(Kiswahili, English, mixed / Sheng with typos, SMS style). Saved to models/examples_gemini.json and labelled
as Gemini-generated in the report. The hand-written examples stay the held-out check.

  python3 models/augment.py --env ../whatsapp-agent/cdk/.env
"""
import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "models"))
from examples import EXAMPLES  # noqa: E402

MODEL = "gemini-2.5-pro"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
OUT = os.path.join(ROOT, "models", "examples_gemini.json")
ANSWERS = json.load(open(os.path.join(ROOT, "answers", "answers.json"), encoding="utf-8"))

PROMPT = """You write realistic SMS messages from smallholder coffee farmers in Nyeri County, Kenya, for training a
tiny intent classifier. Intent: "{label}". The answer they will get: "{answer}".

Examples already written (do not repeat them): {examples}

Write 40 NEW messages a farmer might send that should get this answer: 15 in Kiswahili, 10 in English, 15 mixed
Kiswahili/English or Sheng as people really text (no accents, short forms, some spelling mistakes). 2 to 12 words
each, varied wording, no numbering. Output ONLY a JSON array of strings."""


def key(env_path):
    k = os.environ.get("GOOGLE_GENAI_API_KEY")
    if not k and env_path and os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("GOOGLE_GENAI_API_KEY="):
                k = line.split("=", 1)[1].strip().strip('"')
    if not k:
        sys.exit("set GOOGLE_GENAI_API_KEY or pass --env")
    return k


def gen(k, intent):
    it = next(i for i in ANSWERS["intents"] if i["id"] == intent)
    body = {"contents": [{"parts": [{"text": PROMPT.format(label=it["label"], answer=it["sms"]["en"],
                                                           examples=json.dumps(EXAMPLES[intent], ensure_ascii=False))}]}],
            "generationConfig": {"temperature": 0.9, "responseMimeType": "application/json"}}
    req = Request(f"{URL}?key={k}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    d = json.load(urlopen(req, timeout=180))
    text = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])
    items = json.loads(re.search(r"\[.*\]", text, re.S).group(0))
    seen = {e.lower() for e in EXAMPLES[intent]}
    return intent, [s.strip() for s in items if isinstance(s, str) and s.strip() and s.lower() not in seen]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env")
    a = ap.parse_args()
    k = key(a.env)
    with ThreadPoolExecutor(6) as ex:
        res = dict(ex.map(lambda i: gen(k, i), EXAMPLES))
    json.dump({"_about": "Gemini 2.5 Pro generated, SYNTHETIC, build time only. Spot-checked, not verified by farmers.",
               "examples": res}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for i, v in res.items():
        print(f"{i:18} {len(v):3}  e.g. {v[:3]}")


if __name__ == "__main__":
    main()
