"""Check the fixed answer list and build the file the app ships (answers/answers.built.json).

Checks: every sms fits one SMS (<=160 chars, after filling prices) and one USSD screen (<=182); both languages
present; every cited source file exists. Fills {arabica} / {price_month} from the World Bank Pink Sheet in
data/raw/prices/ (standard library xlsx read). Standard library only.

  python3 answers/build.py
"""
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "answers", "answers.json")
OUT = os.path.join(ROOT, "answers", "answers.built.json")
ADVISORY = os.path.join(ROOT, "data", "raw", "advisory")
PINK = os.path.join(ROOT, "data", "raw", "prices", "CMO-Historical-Data-Monthly.xlsx")
SMS, USSD = 160, 182
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def arabica_latest(path):
    """(USD/kg as text, 'Mon YYYY') for the last month with an Arabica value, from the 'Monthly Prices' sheet."""
    z = zipfile.ZipFile(path)
    strings = [("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))
               for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS)]
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid = next(s.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
               for s in (wb.find("m:sheets", NS) or []) if s.get("name") == "Monthly Prices")
    target = next(r.get("Target") or "" for r in rels if r.get("Id") == rid)
    sheet = ET.fromstring(z.read("xl/" + target.lstrip("/").replace("xl/", "")))

    def val(c):
        v = c.find("m:v", NS)
        if v is None:
            return None
        return strings[int(v.text)] if c.get("t") == "s" else v.text

    col, last = None, None
    for row in sheet.iter(f"{{{NS['m']}}}row"):
        cells = {re.sub(r"\d", "", c.get("r") or ""): val(c) for c in row.findall("m:c", NS)}
        if col is None:
            col = next((k for k, v in cells.items() if v and v.strip().startswith("Coffee, Arabica")), None)
            continue
        month, price = cells.get("A"), cells.get(col)
        if month and re.match(r"^\d{4}M\d{2}$", month) and price not in (None, "", "…"):
            try:
                last = (month, float(price))
            except ValueError:
                pass
    if not last:
        raise RuntimeError("no Arabica price found")
    y, m = last[0].split("M")
    return f"US${last[1]:.2f}/kg", f"{MONTHS[int(m) - 1]} {y}"


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    fills = {}
    try:
        fills["arabica"], fills["price_month"] = arabica_latest(PINK)
    except Exception as e:
        print(f"price: {e} (run data/fetch.py --only pinksheet)")
        fills = {"arabica": "US$?/kg", "price_month": "?"}
    print(f"price fill: Arabica {fills['arabica']} ({fills['price_month']})")

    problems = []
    items = data["intents"] + [data["fallback"]]
    for it in items:
        for lang in data["languages"]:
            for kind in ("sms", "more"):
                if kind not in it:
                    continue
                if lang not in it[kind]:
                    problems.append(f"{it['id']}.{kind} missing {lang}")
                    continue
                it[kind][lang] = it[kind][lang].format(**fills)
            if "sms" in it and lang in it["sms"]:
                n = len(it["sms"][lang])
                if n > SMS:
                    problems.append(f"{it['id']}.sms.{lang} is {n} chars (> {SMS})")
        for s in it.get("source", []):
            f = os.path.normpath(os.path.join(ADVISORY, s["file"]))
            if not os.path.exists(f):
                problems.append(f"{it['id']}: source file missing {s['file']}")

    width = max(len(i["id"]) for i in items)
    for it in items:
        print(f"  {it['id']:{width}}  sms en {len(it['sms']['en']):3}  sw {len(it['sms']['sw']):3}"
              f"  sources {len(it.get('source', []))}  {'-> person' if it.get('ask_person') else ''}")
    data["filled"] = fills
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if problems:
        print("\nPROBLEMS:\n  " + "\n  ".join(problems))
        return 1
    print(f"\nok: {len(data['intents'])} intents + fallback -> {os.path.relpath(OUT, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
