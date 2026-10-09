"""Render a perfectly still, mirror-clear lake (4K) from the shoreline band of docs/assets/lake.png.

The photo's sky and misty treeline are kept. Below the waterline the water is a mirror of them:
strongly reflective near the horizon, fading (Fresnel, n = 1.33) to dark clear water near the
viewer. The result is docs/assets/lake-still.jpg, used by the site's lake background.
"""
import numpy as np
from PIL import Image, ImageFilter

SRC, OUT = "docs/assets/lake.png", "docs/assets/lake-still.jpg"
W, H = 3840, 2160
SHORE = 114                                   # waterline row in the source photo
FOV_DEG = 22.0                                # a long lens: low, grazing view across the lake

photo = Image.open(SRC).convert("RGB")
band_h = round(SHORE * W / photo.width)      # keep the band's aspect ratio
sky = np.asarray(photo.crop((0, 0, photo.width, SHORE)).resize((W, band_h), Image.LANCZOS)).astype(np.float32) / 255

# Sky above the photo's top edge (what the near water reflects): the top rows, blurred sideways,
# deepening towards a cool dawn blue higher up.
top = np.asarray(photo.crop((0, 0, photo.width, 14)).resize((W, 1), Image.LANCZOS)).astype(np.float32)[0] / 255
top = np.asarray(Image.fromarray((top[None] * 255).astype(np.uint8).repeat(8, 0)).filter(ImageFilter.GaussianBlur(90))).astype(np.float32)[4] / 255
zenith = 0.55 * top + 0.45 * np.array([0.33, 0.39, 0.47], np.float32)

yh = band_h                                   # horizon row in the output
f = (H / 2) / np.tan(np.radians(FOV_DEG / 2))
pitch = np.arctan((H / 2 - yh) / f)

img = np.zeros((H, W, 3), np.float32)
img[:yh] = sky
ys = np.arange(yh, H)
v = 2 * yh - 1 - ys                           # mirrored row in the sky (mirror between rows yh-1 and yh)
refl = np.empty((len(ys), W, 3), np.float32)
inside = v >= 0
refl[inside] = sky[v[inside]]
beyond = -v[~inside].astype(np.float32)
t = (1 - np.exp(-beyond / 700.0))[:, None, None]
refl[~inside] = top[None] * (1 - t) + zenith[None] * t

# Soft clouds overhead, which a still lake reflects faintly: a few octaves of smooth noise,
# stretched sideways like real cloud banks and larger the higher they are.
rng_c = np.random.default_rng(11)
rows_c = int((~inside).sum())
clouds = np.zeros((rows_c, W), np.float32)
for octave, (gh, gw, amp) in enumerate([(4, 7, 1.0), (8, 16, 0.55), (16, 34, 0.3), (32, 70, 0.16)]):
    grid = rng_c.random((gh, gw)).astype(np.float32)
    layer = np.asarray(Image.fromarray((grid * 255).astype(np.uint8)).resize((W, rows_c), Image.BICUBIC)).astype(np.float32) / 255
    clouds += amp * (layer - 0.5)
clouds = np.clip(clouds / 1.4 + 0.5, 0, 1)
clouds = np.clip((clouds - 0.42) / 0.4, 0, 1) ** 1.6                    # wispy banks, mostly clear sky between
lift = (0.16 * clouds * (0.4 + 0.6 * t[:, :, 0]))[:, :, None]
refl[~inside] = refl[~inside] * (1 - lift) + (top[None] * 1.08 + 0.02) * lift
# soften the seam where the photo ends and the extended sky begins
seam = (v >= 0) & (v < 60)
w = (v[seam] / 60.0)[:, None, None]
refl[seam] = top[None] * (1 - w) + refl[seam] * w

# A mirror is crisp; let reflections soften very slightly with distance, as real water does.
soft = np.asarray(Image.fromarray((refl * 255).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.2))).astype(np.float32) / 255
k = np.clip((ys - yh) / (H - yh), 0, 1)[:, None, None] ** 0.8
refl = refl * (1 - k) + soft * k

# Fresnel reflectance for the angle each row is seen at.
angle = np.arctan((ys - H / 2) / f) + pitch
cos_i = np.sin(np.clip(angle, 1e-4, None))
R = (0.02 + 0.98 * (1 - cos_i) ** 5)[:, None, None]
body_far, body_near = np.array([0.11, 0.15, 0.19], np.float32), np.array([0.035, 0.065, 0.085], np.float32)
body = body_far[None, None] * (1 - k) + body_near[None, None] * k
water = R * refl + (1 - R) * body

# Mist lying on the water at the shoreline.
mist = sky[-6:].mean(axis=0)[None]
haze = np.exp(-(ys - yh) / 70.0)[:, None, None] * 0.45
water = water * (1 - haze) + mist * haze
img[yh:] = water

# Lens: gentle vignette and fine grain so it reads as a photograph, not a gradient.
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = 1 - 0.22 * (((xx - W / 2) / (W / 2)) ** 2 * 0.6 + ((yy - H * 0.45) / H) ** 2 * 1.1)
img *= vig[..., None]
rng = np.random.default_rng(7)
img += rng.normal(0, 0.006, img.shape).astype(np.float32)
Image.fromarray((img.clip(0, 1) * 255 + 0.5).astype(np.uint8)).save(OUT, quality=90, optimize=True, progressive=True)
print("wrote", OUT, "horizon at", yh, "of", H)
