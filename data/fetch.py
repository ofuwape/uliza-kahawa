"""Pull every dataset this project uses into data/raw/ and record what was pulled in data/manifest.json.

Standard library only. Re-runnable: existing files are skipped unless --force.
Setting: Nyeri County, Kenya (arabica coffee). Languages: Kiswahili, English (Kikuyu tested separately).

  python3 data/fetch.py              # everything automatic
  python3 data/fetch.py --only power,wdi
  python3 data/fetch.py --list       # what it pulls + the manual downloads
"""
import argparse
import hashlib
import io
import json
import os
import sys
import tarfile
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
MANIFEST = os.path.join(HERE, "manifest.json")

LAT, LON = -0.42, 36.95            # Nyeri town, Kenya
COUNTRY = "KEN"

UA = {"User-Agent": "hacknation-smallai-fetch/1.0"}


def get(url, timeout=120):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


# ---------------------------------------------------------------- sources
def massive():
    """MASSIVE 1.1 (Amazon, CC BY 4.0): intent-labelled utterances; keep the Swahili + English locales."""
    blob = get("https://amazon-massive-nlu-dataset.s3.amazonaws.com/amazon-massive-dataset-1.1.tar.gz", 600)
    out = {}
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as t:
        for m in t.getmembers():
            name = os.path.basename(m.name)
            if name in ("sw-KE.jsonl", "en-US.jsonl"):
                f = t.extractfile(m)
                if f:
                    out[f"massive/{name}"] = f.read()
    return out


def flores():
    """FLORES-200 (Meta, CC BY-SA 4.0): the same sentences in Kikuyu, Kiswahili and English (dev + devtest),
    to measure how the tool fares in the less-supported language."""
    blob = get("https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz", 600)
    out = {}
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as t:
        for m in t.getmembers():
            parts = m.name.split("/")
            if len(parts) >= 3 and parts[-2] in ("dev", "devtest") and parts[-1].split(".")[0] in ("kik_Latn", "swh_Latn", "eng_Latn"):
                f = t.extractfile(m)
                if f:
                    out[f"flores/{parts[-2]}/{parts[-1]}"] = f.read()
    return out


def power():
    """NASA POWER daily rain + temperature at Nyeri (no registration)."""
    url = ("https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR,T2M,RH2M"
           f"&community=AG&latitude={LAT}&longitude={LON}&start=20160101&end=20260930&format=CSV")
    return {"power/nyeri_daily.csv": get(url, 300)}


def pinksheet():
    """World Bank Commodity Price Data (Pink Sheet), monthly: Arabica + Robusta reference prices (CC BY 4.0).
    The file URL changes with each update, so read the current link off the commodity-markets page."""
    import re
    page = get("https://www.worldbank.org/en/research/commodity-markets").decode("utf-8", "replace")
    links = re.findall(r'https://thedocs\.worldbank\.org[^"]*CMO-Historical-Data-Monthly\.xlsx', page)
    url = links[0] if links else ("https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/"
                                  "related/CMO-Historical-Data-Monthly.xlsx")
    return {"prices/CMO-Historical-Data-Monthly.xlsx": get(url, 300)}


def wfp():
    """WFP food prices for Kenya via HDX (her maize + beans); resource URL looked up through the CKAN API."""
    meta = json.loads(get("https://data.humdata.org/api/3/action/package_show?id=wfp-food-prices-for-kenya"))
    res = [r for r in meta["result"]["resources"] if r.get("format", "").upper() == "CSV"]
    if not res:
        raise RuntimeError("no CSV resource on the HDX dataset")
    return {"prices/wfp_food_prices_ken.csv": get(res[0]["url"], 300)}


WDI = {  # World Bank indicators for the problem-is-real numbers (country + year attached)
    "IT.NET.USER.ZS": "internet users, % of population",
    "IT.CEL.SETS.P2": "mobile subscriptions per 100 people",
    "SL.AGR.EMPL.ZS": "employment in agriculture, % of total",
    "SP.RUR.TOTL.ZS": "rural population, %",
}


def wdi():
    """World Bank WDI for Kenya: internet use, mobile subscriptions, agriculture jobs, rural share."""
    out = {}
    for code in WDI:
        url = f"https://api.worldbank.org/v2/country/{COUNTRY}/indicator/{code}?format=json&per_page=100"
        out[f"wdi/{COUNTRY}_{code}.json"] = get(url)
    return out


def faostat():
    """FAOSTAT coffee (green) area / yield / production for Kenya, from the public Africa bulk file (API needs a login)."""
    import csv
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(get("https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Africa.zip", 300)))
    name = next(n for n in z.namelist() if n.endswith(".csv") and "Flags" not in n and "Symboles" not in n
                and "AreaCodes" not in n and "ItemCodes" not in n and "Elements" not in n)
    rows = csv.reader(io.TextIOWrapper(z.open(name), encoding="latin-1"))
    head = next(rows)
    ia, ii = head.index("Area"), head.index("Item")
    keep = [head] + [r for r in rows if r[ia] == "Kenya" and r[ii].lower().startswith("coffee")]
    buf = io.StringIO()
    csv.writer(buf).writerows(keep)
    return {"faostat/kenya_coffee_qcl.csv": buf.getvalue().encode()}


# The brief's own link for each source (Annex B + section 7.3); the download URLs above are the direct files behind them.
BRIEF_LINKS = {
    "massive": "https://github.com/alexa/massive",
    "flores": "https://github.com/facebookresearch/flores",
    "power": "https://power.larc.nasa.gov/",
    "pinksheet": "(not in the brief; World Bank Commodity Price Data, our addition for coffee prices)",
    "wfp": "https://data.humdata.org/dataset/global-wfp-food-prices",
    "wdi": "https://data.worldbank.org/",
    "faostat": "https://www.fao.org/faostat",
}

SOURCES = {"massive": massive, "flores": flores, "power": power, "pinksheet": pinksheet, "wfp": wfp, "wdi": wdi, "faostat": faostat}

# Pulled by hand (login, click-through terms, or large); put the files in data/raw/<folder>/ and note them in README.
MANUAL = [
    ("leaf/jmuben", "JMuBEN (Kenyan arabica coffee leaves, CC BY 4.0): https://data.mendeley.com/datasets/t2r6rszp5c/1 ; "
                    "JMuBEN2: https://data.mendeley.com/datasets/tgv3zb82nd/1 (paper doi 10.1016/j.dib.2021.107142); leaf model"),
    ("leaf/bracol", "BRACOL (Brazilian arabica, brief link): https://data.mendeley.com/datasets/yy2k5y8mxg/1 ; leaf model"),
    ("leaf/plantdoc", "PlantDoc (brief link): https://github.com/pratikkayal/PlantDoc-Dataset ; no coffee class, field-vs-studio gap only"),
    ("advisory", "KALRO Coffee Research Institute: https://www.kalro.org/coffee/ (open in a browser); papers: "
                 "doi 10.12966/jra.03.02.2014 (CBD + leaf rust management, Kenya), doi 10.33495/jacr_v11i2.23.114 (coffee pests, Kenya); "
                 "CABI PlantwisePlus farmer factsheets: https://plantwiseplusknowledgebank.org/ (search coffee leaf rust, berry borer)"),
    ("figures", "GSMA Mobile Gender Gap (brief link): https://www.gsma.com/r/gender-gap/ ; Global Findex (brief link): "
                "https://www.worldbank.org/en/publication/globalfindex ; copy the Kenya figures, cite, don't redistribute"),
]


# ---------------------------------------------------------------- run
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated: " + ",".join(SOURCES))
    ap.add_argument("--force", action="store_true", help="re-download files that already exist")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        for k, f in SOURCES.items():
            print(f"{k:10} {(f.__doc__ or '').strip()}\n           brief: {BRIEF_LINKS[k]}")
        print("\nmanual:")
        for folder, note in MANUAL:
            print(f"  data/raw/{folder}/  {note}")
        return 0

    names = a.only.split(",") if a.only else list(SOURCES)
    manifest = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    failed = []
    for n in names:
        if n not in SOURCES:
            sys.exit(f"unknown source {n}")
        print(f"[{n}] …", flush=True)
        try:
            files = SOURCES[n]()
        except Exception as e:
            print(f"[{n}] FAILED: {e}")
            failed.append(n)
            continue
        for rel, data in files.items():
            path = os.path.join(RAW, rel)
            if os.path.exists(path) and not a.force:
                print(f"  skip {rel} (exists)")
                continue
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
            manifest[rel] = {"source": n, "brief_link": BRIEF_LINKS[n], "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                             "pulled_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            print(f"  {rel}  {len(data) / 1e6:.1f} MB")
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    print("\nmanual downloads:" + "".join(f"\n  data/raw/{d}/  {n}" for d, n in MANUAL))
    if failed:
        print(f"\nfailed: {', '.join(failed)} (re-run with --only {','.join(failed)}, or pull by hand)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
