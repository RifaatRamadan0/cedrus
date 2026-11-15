"""Tiny ElevenLabs helper. Reads key from halftime/.env, never prints it."""
import json, sys, urllib.request, pathlib
env = pathlib.Path(r"C:\Users\hussein\Downloads\halftime\.env").read_text(encoding="utf8")
KEY = next(l.split("=",1)[1].strip().strip('"').strip("'") for l in env.splitlines() if l.startswith("ELEVENLABS_API_KEY="))
def call(path, body=None, method=None):
    req = urllib.request.Request("https://api.elevenlabs.io"+path, data=None if body is None else json.dumps(body).encode(),
        headers={"xi-api-key": KEY, "Content-Type": "application/json"}, method=method or ("POST" if body is not None else "GET"))
    with urllib.request.urlopen(req, timeout=600) as r: return r.read()
if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "voices":
        d = json.loads(call("/v1/voices"))
        for v in d["voices"]: print(v["voice_id"], v["name"], v.get("category"), json.dumps(v.get("labels",{})))
    elif cmd == "models":
        for m in json.loads(call("/v1/models")): print(m["model_id"], m.get("can_do_text_to_speech"))
    elif cmd == "sub":
        d = json.loads(call("/v1/user/subscription")); print(d.get("tier"), d.get("character_count"), d.get("character_limit"))
    elif cmd == "tts":  # tts voice_id model out.mp3 text [stability style]
        vid, model, out, text = sys.argv[2:6]
        st = float(sys.argv[6]) if len(sys.argv) > 6 else 0.4
        sty = float(sys.argv[7]) if len(sys.argv) > 7 else 0.45
        vs = {"stability": st, "similarity_boost": 0.8, "style": sty, "use_speaker_boost": True}
        if model == "eleven_v3": vs = {"stability": st}
        body = {"text": text, "model_id": model, "voice_settings": vs}
        pathlib.Path(out).write_bytes(call(f"/v1/text-to-speech/{vid}?output_format=mp3_44100_128", body)); print("ok", out)
