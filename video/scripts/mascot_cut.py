"""Cuts the flame mascot out of its white background (soft edge), drops the beige floor shadow (redrawn as a soft ellipse
in the rig), and makes a mouthless copy (smile painted over with the face yellow) for lip-sync. Writes body.png, body_nomouth.png, rig.json."""
import numpy as np, json
from PIL import Image, ImageFilter
D = r"C:\Users\hussein\Downloads\cedrus-video\mascot"
im = np.asarray(Image.open(D + r"\flame_source.jpg").convert("RGB")).astype(np.float32)
r, g, b = im[..., 0], im[..., 1], im[..., 2]
mx, mn = im.max(-1), im.min(-1); sat = (mx - mn) / np.maximum(mx, 1)
H, W = r.shape; yy = np.arange(H)[:, None].repeat(W, 1)
dark = mx < 120                                   # eyes / mouth
shadow = (sat < 0.55) & (yy > 560)               # beige floor shadow
a = np.clip((sat - 0.25) / 0.2, 0, 1); a[dark] = 1; a[shadow] = 0
alpha = Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
rgba = np.dstack([im.astype(np.uint8), np.asarray(alpha)])
# mouth: dark pixels in the smile band
ys, xs = np.where(dark[388:425, 362:422]); ys += 388; xs += 362
mbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
ey, ex = np.where(dark[330:400, 300:470]); 
nom = rgba.copy(); face = np.median(im[mbox[1]-14:mbox[1]-6, mbox[0]:mbox[2]].reshape(-1, 3), 0).astype(np.uint8)
x0, y0, x1, y1 = mbox[0]-4, mbox[1]-4, mbox[2]+5, mbox[3]+5
nom[y0:y1, x0:x1, :3] = face
bb = Image.fromarray(rgba).getbbox(); pad = 10
crop = (max(0, bb[0]-pad), max(0, bb[1]-pad), min(W, bb[2]+pad), min(H, bb[3]+pad))
Image.fromarray(rgba).crop(crop).save(D + r"\body.png"); Image.fromarray(nom).crop(crop).save(D + r"\body_nomouth.png")
json.dump({"crop": crop, "mouth": [mbox[0]-crop[0], mbox[1]-crop[1], mbox[2]-crop[0], mbox[3]-crop[1]], "face": face.tolist(),
           "size": [crop[2]-crop[0], crop[3]-crop[1]]}, open(D + r"\rig.json", "w"))
print(crop, mbox, face)
