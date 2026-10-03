"""Build-time research helper: find the advisory SOURCES behind each answer with Gemini + Google Search.

Never part of the app (the app is offline). For each intent it asks for Kenyan / FAO guidance a smallholder can
act on, with the publishing organization, and lists the grounding sources (redirects resolved to real URLs).
A person then opens each source, saves the PDF or page to data/raw/advisory/, and writes the final answer.

  GOOGLE_GENAI_API_KEY=... python3 data/research.py              # all intents -> data/advisory-leads.md
  python3 data/research.py --env ../whatsapp-agent/cdk/.env --only rust
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen

MODEL = "gemini-2.5-pro"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "advisory-leads.md")

CONTEXT = ("Smallholder arabica coffee farmer in Nyeri County, Kenya, who delivers cherry to a cooperative factory. "
           "Prefer KALRO Coffee Research Institute (Ruiru), the Agriculture and Food Authority Coffee Directorate, "
           "FAO, CABI PlantwisePlus, or peer reviewed studies. ")

INTENTS = {
    "rust": "How to recognise coffee leaf rust and what a smallholder should do about it, including when to spray and what with.",
    "cbd": "How to recognise coffee berry disease (CBD) and how and when smallholders should control it.",
    "borer": "How to recognise coffee berry borer and antestia bug damage and what smallholders should do.",
    "yellow-leaves": "Common causes of yellowing coffee leaves (nutrient deficiency, drought, waterlogging) and what to do, including fertiliser timing.",
    "spray-timing": "How rainfall and the short and long rains in Kenya affect when to apply copper fungicide and fertiliser on coffee.",
    "harvest": "When and how to pick coffee cherry for best quality (ripeness, picking only red cherry, sorting before delivery).",
    "quality": "What lowers the quality grade and price of delivered coffee cherry and how a smallholder can avoid it.",
    "yield-drop": "The most common reasons a smallholder's coffee yield drops from one season to the next, and how to tell which one it is.",
    "pruning": "When and how smallholders should prune or stump old coffee bushes to restore yield.",
    "price": "How Kenyan coffee cooperatives set the payment rate for cherry, how it relates to the Nairobi Coffee Exchange, and how a farmer can check it.",
    "inputs": "Where a smallholder coffee farmer in Kenya can get approved fungicides, fertiliser and seedlings, and how to avoid fake inputs.",
}

PROMPT = """{context}
Question: {q}

Answer in at most 6 short bullet points of practical guidance, each followed by [organization]. Then a line
"SOURCES:" listing the documents you relied on (title, organization, year). If the guidance differs by source or
you are not sure, say so. Do not invent product names, doses or dates; leave a dose out rather than guess."""


def key(env_path):
    k = os.environ.get("GOOGLE_GENAI_API_KEY")
    if not k and env_path and os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("GOOGLE_GENAI_API_KEY="):
                k = line.split("=", 1)[1].strip().strip('"')
    if not k:
        sys.exit("set GOOGLE_GENAI_API_KEY or pass --env")
    return k


def resolve(u):
    """Grounding links are Google redirects; follow them to the real page (GET, since some reject HEAD)."""
    for method in ("HEAD", "GET"):
        try:
            with urlopen(Request(u, method=method, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r:
                if "vertexaisearch" not in r.geturl():
                    return r.geturl()
        except Exception as e:
            loc = getattr(e, "headers", None) and e.headers.get("Location")
            if loc:
                return loc
    return u


def ask(k, name, q):
    body = {"contents": [{"parts": [{"text": PROMPT.format(context=CONTEXT, q=q)}]}],
            "tools": [{"google_search": {}}], "generationConfig": {"temperature": 0.2}}
    req = Request(f"{URL}?key={k}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        d = json.load(urlopen(req, timeout=180))
    except Exception as e:
        return name, q, f"ERROR: {e}", []
    c = d.get("candidates", [{}])[0]
    text = "".join(p.get("text", "") for p in c.get("content", {}).get("parts", []))
    chunks = c.get("groundingMetadata", {}).get("groundingChunks", [])
    srcs = []
    for ch in chunks:
        w = ch.get("web", {})
        if w.get("uri"):
            srcs.append((w.get("title", ""), resolve(w["uri"])))
    return name, q, text.strip(), srcs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated intent keys: " + ",".join(INTENTS))
    ap.add_argument("--env", help="path to a .env holding GOOGLE_GENAI_API_KEY")
    a = ap.parse_args()
    k = key(a.env)
    names = a.only.split(",") if a.only else list(INTENTS)
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda n: ask(k, n, INTENTS[n]), names))
    if a.only and os.path.exists(OUT):        # merge: keep earlier sections for intents not re-run
        old = open(OUT).read().split("\n## ")[1:]
        keep = {sec.split("\n")[0]: sec for sec in old}
        res = [(n, INTENTS[n], None, None) if n not in names else next(r for r in res if r[0] == n)
               for n in INTENTS if n in keep or n in names]
    out = ["# Advisory leads (Gemini + Google Search, build time only)", "",
           "Leads, not answers: open every source, save it to data/raw/advisory/, and write the final answer from",
           "the source itself. Sections with no grounding sources may be from memory: do not use them as is.", ""]
    for name, q, text, srcs in res:
        if text is None:
            out += ["## " + keep[name].rstrip(), ""]
            continue
        out += [f"## {name}", f"_Q: {q}_", "", text, "", "Grounding sources:" if srcs else "Grounding sources: NONE"]
        out += [f"- {t}: {u}" for t, u in dict.fromkeys(srcs)]
        out.append("")
    open(OUT, "w").write("\n".join(out))
    print("\n".join(out))
    print(f"\nsaved {OUT}")


if __name__ == "__main__":
    main()
