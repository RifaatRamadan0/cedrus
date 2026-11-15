"""Writes CEDRUS_2min.srt from the narration timeline."""
import sys; sys.path.insert(0, r"C:\Users\hussein\Downloads\cedrus-video\scripts")
from timeline import VO
T = {"l1": "In 2025, Europe lived through its worst fire year on record... more than a million hectares burned. And the fires are expected to grow.",
 "l2": "But here's the catch. More dots on a fire map don't always mean more fire. Newer satellites see smaller fires than the old ones. Merge their counts naively, and Lebanon's fires look five times worse than they really were.",
 "l3": "This is CEDRUS. Using NASA FIRMS data, we learn how the new VIIRS sensors translate into the old MODIS scale, from the years both flew together... and build one consistent fire record, from 2000 to today.",
 "l4a": "Pick a region... like Lebanon, our home.", "l4b": "Every month is a tile. Click October 2024, and see how it compares to a normal October, with an honest trust label.",
 "l4c": "Switch between burning days and hotspots.", "l4d": "Draw any area.", "l4e": "See when the fire season runs.", "l4f": "And compare right now to normal, updated every day.",
 "l5": "And to help prevent the next fire: a seven-day fire-weather outlook... heat, dryness, wind and soil moisture, compared with what's normal for that place.",
 "l6": "We tested it in a sealed exam, on four regions the model had never seen. Our error: 11.6 percent... against 20.3 for a simple conversion.",
 "l7": "For forest teams, civil protection and researchers: a clearer fire history, from changing satellites. CEDRUS."}
D = {"l1": 10.56, "l2": 14.96, "l3": 15.76, "l5": 10.16, "l6": 11.04, "l7": 8.8}
keys = iter(["l4a", "l4b", "l4c", "l4d", "l4e", "l4f"])
def ts(x): h, r = divmod(x, 3600); m, s = divmod(r, 60); return f"{int(h):02}:{int(m):02}:{int(s):02},{int(round((s % 1) * 1000)):03}"
out = []
for n, (f, a, b, at) in enumerate(VO, 1):
    k = next(keys) if f == "l4" else f; dur = (b if b else 23.68) - a if f == "l4" else D[f]
    out.append(f"{n}\n{ts(at)} --> {ts(at + dur)}\n{T[k]}\n")
open(r"C:\Users\hussein\Downloads\cedrus-video\CEDRUS_2min.srt", "w", encoding="utf8").write("\n".join(out)); print(len(out))
