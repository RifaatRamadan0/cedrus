"""Concats the composed parts, muxes the mix (AAC 192k, +faststart), writes contact.jpg (10 frames) and review frames every 10 s."""
import subprocess, sys
from PIL import Image
FF = r"C:\Users\hussein\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"
V = r"C:\Users\hussein\Downloads\cedrus-video"; W = V + r"\work"
# (file, first_frame, end_frame) in each file's own frame numbers -> spliced in order, re-encoded once
PIECES = [("fx_hook.mp4", 0, 345), ("p1.mp4", 345, 1200), ("p2.mp4", 0, 1200), ("p3a.mp4", 0, 180),
          ("fx_fore.mp4", 0, 360), ("p3b.mp4", 0, 330), ("fx_close.mp4", 0, 315)]
args = [FF, "-y", "-loglevel", "error"]; fc = ""
for i, (f, a0, a1) in enumerate(PIECES):
    args += ["-i", W + "\\" + f]; fc += f"[{i}:v]trim=start_frame={a0}:end_frame={a1},setpts=PTS-STARTPTS[v{i}];"
fc += "".join(f"[v{i}]" for i in range(len(PIECES))) + f"concat=n={len(PIECES)}:v=1:a=0[v]"
args += ["-i", W + r"\mix.wav", "-filter_complex", fc, "-map", "[v]", "-map", f"{len(PIECES)}:a", "-c:v", "libx264", "-profile:v", "high",
         "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", V + r"\CEDRUS_2min.mp4"]
subprocess.run(args, check=True)
tiles = []
for i, t in enumerate([2, 9, 14, 20, 26, 40, 58, 72, 92, 104, 118][:10] if False else [3, 15, 20, 26, 42, 58, 72, 91, 104, 118]):
    subprocess.run([FF, "-y", "-loglevel", "error", "-ss", str(t), "-i", V + r"\CEDRUS_2min.mp4", "-frames:v", "1", "-vf", "scale=640:-1", W + rf"\cs{i}.jpg"], check=True)
    tiles.append(Image.open(W + rf"\cs{i}.jpg"))
sheet = Image.new("RGB", (640 * 5, 360 * 2))
for i, im in enumerate(tiles): sheet.paste(im, ((i % 5) * 640, (i // 5) * 360))
sheet.save(V + r"\contact.jpg", quality=88); print("ok")
