"""The connected tier, as a sample: draft a weekly SMS brief a cooperative could send to farmers who opted in.

Runs where there IS internet (the cooperative's office), never on the farmer's phone. Gemini + Google Search drafts
items on three topics tied to Noor's decision (funding, meeting other farmers / training, the coffee market); every
item must carry a source URL that the search actually returned, or it is dropped. A person (the extension officer)
reviews the drafts before anything is sent. The page shows the result as a dated sample.

  python3 data/briefing.py --env ../whatsapp-agent/cdk/.env      -> app/briefing.sample.json
"""
import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "app", "briefing.sample.json")
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"

TOPICS = {
    "funding": ("Funding", "Pesa na ruzuku",
                "Grants, loans, input subsidies or funding calls that smallholder coffee farmers or coffee cooperatives "
                "in Kenya (ideally Nyeri or Central Kenya) can apply to now. Only ones open now or with a future deadline."),
    "meet": ("Meet other farmers", "Kutana na wakulima",
             "Upcoming farmer field days, coffee trainings, cooperative meetings or agricultural shows in or near Nyeri "
             "County, Kenya, that a smallholder coffee farmer could attend (organiser, place, date)."),
    "market": ("Coffee market", "Soko la kahawa",
               "This month's coffee market news a Kenyan smallholder should know: Nairobi Coffee Exchange auction prices, "
               "cherry payment rates announced by cooperatives in Central Kenya, or changes to coffee marketing rules."),
}

SEARCH = """Today is {today}. Search the web: {q}
List what you find as short bullet points. For each: what it is, who runs it, the date or deadline, and where.
Only things you found in today's search results; never invent a date, amount or organiser. Say "nothing found" if so."""

FORMAT = """Turn these search notes into at most 3 SMS brief items for a smallholder coffee farmer in Nyeri, Kenya.
Use ONLY facts in the notes. For source_url pick the matching URL from SOURCES (copy it exactly); if none matches,
skip the item. Return ONLY a JSON array:
[{{"title": "...", "sms_en": "max 150 characters, plain words, include the date or deadline if any",
   "sms_sw": "the same in Kiswahili, max 150 characters", "date": "", "publisher": "", "source_url": ""}}]
NOTES:
{notes}
SOURCES:
{sources}"""


def call(k, text, search):
    body = {"contents": [{"parts": [{"text": text}]}], "generationConfig": {"temperature": 0.2}}
    if search:
        body["tools"] = [{"google_search": {}}]
    d = json.load(urlopen(Request(f"{URL}?key={k}", data=json.dumps(body).encode(),
                                  headers={"Content-Type": "application/json"}), timeout=240))
    c = d["candidates"][0]
    return "".join(p.get("text", "") for p in c.get("content", {}).get("parts", [])), c.get("groundingMetadata", {})


def key(env):
    k = os.environ.get("GOOGLE_GENAI_API_KEY")
    if not k and env:
        k = next((l.split("=", 1)[1].strip().strip('"') for l in open(env) if l.startswith("GOOGLE_GENAI_API_KEY=")), None)
    if not k:
        sys.exit("set GOOGLE_GENAI_API_KEY or pass --env")
    return k


def resolve(u):
    for m in ("HEAD", "GET"):
        try:
            with urlopen(Request(u, method=m, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r:
                if "vertexaisearch" not in r.geturl():
                    return r.geturl()
        except Exception as e:
            h = getattr(e, "headers", None)
            loc = h.get("Location") if h else None
            if loc:
                return loc
    return u


def topic(k, name):
    notes, meta = call(k, SEARCH.format(today=date.today().isoformat(), q=TOPICS[name][2]), search=True)
    grounded = [resolve(w["web"]["uri"]) for w in meta.get("groundingChunks", []) if w.get("web")]
    items = []
    if grounded:
        out, _ = call(k, FORMAT.format(notes=notes, sources="\n".join(grounded)), search=False)
        m = re.search(r"\[.*\]", out, re.S)
        try:
            items = json.loads(m.group(0)) if m else []
        except ValueError:
            items = []
    kept = []
    for it in items:
        if str(it.get("source_url", "")) in grounded:          # must be a page the search actually returned
            it["sms_en"], it["sms_sw"] = str(it.get("sms_en", ""))[:160], str(it.get("sms_sw", ""))[:160]
            kept.append(it)
    return name, {"label": TOPICS[name][:2], "items": kept, "dropped_unsourced": len(items) - len(kept),
                  "grounding": grounded[:8]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env")
    a = ap.parse_args()
    k = key(a.env)
    with ThreadPoolExecutor(3) as ex:
        res = dict(ex.map(lambda n: topic(k, n), TOPICS))
    out = {"_about": "SAMPLE weekly brief drafted with Gemini + Google Search. Every item had a source the search "
                     "returned; a person reviews before anything is sent. Dates and deadlines go stale: check before use.",
           "generated": date.today().isoformat(), "topics": res}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for n, t in res.items():
        print(f"\n## {t['label'][0]}  (kept {len(t['items'])}, dropped {t['dropped_unsourced']} without a matching source)")
        for it in t["items"]:
            print(f"- {it['sms_en']}\n  {it['sms_sw']}\n  {it.get('publisher', '')} · {it['source_url']}")
    print(f"\n-> {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
