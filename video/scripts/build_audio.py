"""Builds vo.wav (narration placed on the film timeline), mouth.json (per-frame lip-sync levels), and the final mix:
Scott Buckley 'Hymn To The Dawn' edited to 2:00 in three phrases, ducked under the voice, loudness-normalised to -16 LUFS."""
import subprocess, json, sys, numpy as np
sys.path.insert(0, r"C:\Users\hussein\Downloads\cedrus-video\scripts")
from timeline import VO, FILM
FF = r"C:\Users\hussein\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"
W = r"C:\Users\hussein\Downloads\cedrus-video\work"
SR = 48000
track = np.zeros(int(FILM * SR) + SR, np.float32)
for f, a, b, at in VO:
    raw = subprocess.run([FF, "-loglevel", "error", "-i", rf"{W}\vo\{f}.mp3", "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)[int(a * SR): None if b is None else int(b * SR)].copy()
    n = int(0.02 * SR); x[:n] *= np.linspace(0, 1, n); x[-n:] *= np.linspace(1, 0, n)
    i = int(at * SR); track[i:i + len(x)] += x
track = track[:int(FILM * SR)]
# lip-sync: RMS per 1/30 s frame -> 0 closed / 1 small / 2 big
hop = SR // 30; fr = track[: len(track) // hop * hop].reshape(-1, hop); rms = np.sqrt((fr ** 2).mean(1))
ref = np.percentile(rms[rms > 1e-3], 90) if (rms > 1e-3).any() else 1
lvl = np.where(rms < ref * 0.12, 0, np.where(rms < ref * 0.45, 1, 2))
for i in range(1, len(lvl) - 1):   # no single-frame flicker
    if lvl[i - 1] == lvl[i + 1] != lvl[i]: lvl[i] = lvl[i - 1]
json.dump(lvl.tolist(), open(rf"{W}\mouth.json", "w"))
subprocess.run([FF, "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", rf"{W}\vo.wav"], input=track.tobytes())
# music edit: three phrases with 3 s crossfades -> about 119 s, then ducking + loudnorm
fc = (f"[1:a]atrim=0:47,asetpts=PTS-STARTPTS[m1];[1:a]atrim=221:273,asetpts=PTS-STARTPTS[m2];[1:a]atrim=378:404.5,asetpts=PTS-STARTPTS[m3];"
      f"[m1][m2]acrossfade=d=3:c1=tri:c2=tri[m12];[m12][m3]acrossfade=d=3:c1=tri:c2=tri,afade=t=in:d=1.5,afade=t=out:st={FILM-3}:d=3,atrim=0:{FILM},aresample={SR},volume=0.9[mus];"
      f"[0:a]aresample={SR},asplit[v1][v2];[mus][v1]sidechaincompress=threshold=0.015:ratio=10:attack=30:release=450:makeup=1[duck];"
      f"[duck][v2]amix=inputs=2:weights='1 1.6':normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,aresample={SR}[out]")
subprocess.run([FF, "-y", "-loglevel", "error", "-i", rf"{W}\vo.wav", "-i", rf"{W}\hymn.mp3", "-filter_complex", fc, "-map", "[out]", "-c:a", "pcm_s16le", rf"{W}\mix.wav"], check=True)
print("frames", len(lvl), "talk frames", int((lvl > 0).sum()))
