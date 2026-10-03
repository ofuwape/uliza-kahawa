"""Record every fixed answer (Kiswahili + English) with ElevenLabs, small MP3s the app plays offline.

SYNTHETIC voice for the demo. In a real deployment a local extension officer records the same fixed texts
(no text-to-speech is needed then, which is what makes this work for languages TTS handles badly).
Reads answers/answers.built.json (run answers/build.py first). Re-runnable: existing files are kept unless --force.

  ELEVENLABS_API_KEY=... ELEVENLABS_VOICE_ID=... python3 answers/voice.py
  python3 answers/voice.py --env ../whatsapp-agent/cdk/.env
"""
import argparse
import json
import os
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILT = os.path.join(ROOT, "answers", "answers.built.json")
OUT = os.path.join(ROOT, "answers", "audio")
MODEL = "eleven_v3"                 # supports Kiswahili
FORMAT = "mp3_22050_32"             # small: ~4 KB per second of speech


def env(path):
    vals = {}
    if path and os.path.exists(path):
        for line in open(path):
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                vals[k] = v.strip().strip('"')
    get = lambda k: os.environ.get(k) or vals.get(k)
    return get("ELEVENLABS_API_KEY"), get("ELEVENLABS_VOICE_ID")


def tts(text, key, voice, lang):
    body = {"text": text, "model_id": MODEL, "language_code": lang}
    for n in range(3):
        req = Request(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format={FORMAT}",
                      data=json.dumps(body).encode(), method="POST",
                      headers={"xi-api-key": key, "Content-Type": "application/json"})
        try:
            return urlopen(req, timeout=120).read()
        except HTTPError as e:
            msg = e.read().decode()[:200]
            if e.code < 500 and e.code != 429:
                sys.exit(f"ElevenLabs {e.code}: {msg}")
            print(f"  retry ({e.code})")
        time.sleep(4 * (n + 1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    key, voice = env(a.env)
    if not key or not voice:
        sys.exit("need ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID (env or --env file)")
    data = json.load(open(BUILT, encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    index, total = {}, 0
    for it in data["intents"] + [data["fallback"]]:
        for lang in data["languages"]:
            name = f"{it['id']}.{lang}.mp3"
            path = os.path.join(OUT, name)
            if not os.path.exists(path) or a.force:
                mp3 = tts(it["sms"][lang], key, voice, lang)
                if not mp3:
                    print(f"  FAILED {name}")
                    continue
                open(path, "wb").write(mp3)
            size = os.path.getsize(path)
            total += size
            index.setdefault(it["id"], {})[lang] = f"audio/{name}"
            print(f"  {name:28} {size / 1024:5.1f} KB")
    json.dump({"_about": "ElevenLabs eleven_v3, SabiNau voice, synthetic demo voice. Texts = the sms answers.",
               "price_month": data.get("filled", {}).get("price_month"), "files": index},
              open(os.path.join(OUT, "index.json"), "w"), indent=1)
    print(f"{sum(len(v) for v in index.values())} files, {total / 1024:.0f} KB total -> answers/audio/")


if __name__ == "__main__":
    main()
