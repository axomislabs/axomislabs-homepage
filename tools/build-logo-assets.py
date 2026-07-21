#!/usr/bin/env python3
"""Regenerate every logo asset in site/assets/ from the master brand image.

The master (Branding/Axomislabs - Logo.png) is a flat RGB render on a white plate,
so everything downstream is derived: the white is converted to alpha, the lockup is
split into its three brand inks, and each ink is traced to vector separately.

    python3 tools/build-logo-assets.py

Requires Pillow and potrace (brew install potrace).
"""
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, "Branding", "Axomislabs - Logo.png")
OUT = os.path.join(ROOT, "site", "assets")

# White-plate removal: the scan's background sits at ~254, and the darkest channel is
# a good coverage estimate for these inks. Between HI and LO we ramp alpha and
# unpremultiply against white so edges keep no pale halo.
HI, LO = 250.0, 205.0

# Tracing. The master is a textured render, so its edges carry noise that potrace
# would otherwise reproduce as wobble along what should be straight strokes. We
# upsample, blur, and re-threshold at 50% coverage: that removes the noise while
# leaving the edge on its original centreline. BLUR is capped at 2 because the
# hairline rules beside the tagline are only ~2px tall and erode above that.
SCALE, BLUR = 3, 2
TURDSIZE = 400  # drops sub-40px specks; real glyphs are 300px+

CHARCOAL, COPPER, OLIVE = "#2E3133", "#B66A3C", "#68724D"
IVORY = "#F7F5F0"
DARK = {"charcoal": CHARCOAL, "copper": COPPER, "olive": OLIVE}
LIGHT = {"charcoal": IVORY, "copper": "#D08A5C", "olive": "#97A473"}
ORDER = ("charcoal", "copper", "olive")
# Raster equivalents of LIGHT, used to recolour the PNG variants for dark grounds.
LIGHT_RGB = {"charcoal": (247, 245, 240), "copper": (208, 138, 92), "olive": (151, 164, 115)}


def ink_of(r, g, b):
    """Which brand ink is this pixel? Chroma separates the neutral charcoal from
    copper and olive; the red/blue spread then separates those two."""
    if max(r, g, b) - min(r, g, b) < 30:
        return "charcoal"
    if r >= g and r - b > 45:
        return "copper"
    if g >= r:
        return "olive"
    return None


def dewhite(im):
    def px(p):
        r, g, b = p
        cov = (HI - min(r, g, b)) / (HI - LO)
        if cov <= 0:
            return (255, 255, 255, 0)
        if cov >= 1:
            return (r, g, b, 255)
        inv = 255.0 * (1.0 - cov)
        return (min(255, max(0, int((r - inv) / cov))),
                min(255, max(0, int((g - inv) / cov))),
                min(255, max(0, int((b - inv) / cov))),
                int(cov * 255))
    out = Image.new("RGBA", im.size)
    out.putdata([px(p) for p in im.getdata()])
    return out


def trim(img):
    return img.crop(img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())


def relight(img):
    """Recolour charcoal to ivory (and lift copper/olive) for dark backgrounds."""
    def px(p):
        r, g, b, a = p
        if a == 0:
            return p
        k = ink_of(r, g, b)
        return (LIGHT_RGB[k] + (a,)) if k else p
    out = Image.new("RGBA", img.size)
    out.putdata([px(p) for p in img.getdata()])
    return out


def trace(img, work):
    """Trace one lockup into per-ink SVG path lists."""
    w, h = img.size
    buf = {k: bytearray(w * h) for k in ORDER}
    for i, (r, g, b, a) in enumerate(img.getdata()):
        if a:
            k = ink_of(r, g, b)
            if k:
                buf[k][i] = a  # keep alpha as coverage so anti-aliasing survives

    paths = {}
    for k in ORDER:
        m = Image.frombytes("L", (w, h), bytes(buf[k]))
        if not m.getbbox():
            continue
        m = m.resize((w * SCALE, h * SCALE), Image.LANCZOS).filter(ImageFilter.GaussianBlur(BLUR))
        pbm = os.path.join(work, f"{k}.pbm")
        svg = os.path.join(work, f"{k}.svg")
        m.point(lambda v: 0 if v >= 128 else 255).convert("1").save(pbm)  # potrace traces black
        subprocess.run(["potrace", "-b", "svg", "--turdsize", str(TURDSIZE),
                        "--alphamax", "1.0", "--opttolerance", "0.2",
                        "-o", svg, pbm], check=True)
        paths[k] = re.findall(r'<path d="([^"]+)"', open(svg).read())
    return paths


def write_svg(path, paths, size, palette, label):
    w, h = size
    # potrace emits tenths of a bitmap pixel with Y pointing up. Fold the 1/SCALE
    # reduction, the 1/10 unit and the Y-flip into one matrix back to native coords.
    k = 1.0 / (10.0 * SCALE)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
           f'role="img" aria-label="{label}">', f"<title>{label}</title>",
           f'<g transform="matrix({k:.7f},0,0,-{k:.7f},0,{h})">']
    for layer in ORDER:
        for d in paths.get(layer, []):
            out.append(f'<path fill="{palette[layer]}" d="{d}"/>')
    out += ["</g>", "</svg>", ""]
    open(path, "w").write("\n".join(out))


def main():
    if not os.path.exists(MASTER):
        sys.exit(f"master not found: {MASTER}")
    os.makedirs(OUT, exist_ok=True)

    full = trim(dewhite(Image.open(MASTER).convert("RGB")))

    # Split the lockup into horizontal bands of non-empty rows: mark / wordmark / tagline.
    alpha = full.getchannel("A")
    filled = [alpha.crop((0, y, full.width, y + 1)).getextrema()[1] > 8 for y in range(full.height)]
    bands, run = [], None
    for i, v in enumerate(filled):
        if v and run is None:
            run = i
        elif not v and run is not None:
            bands.append((run, i))
            run = None
    if run is not None:
        bands.append((run, full.height))
    bands = [b for b in bands if b[1] - b[0] > full.height * 0.02]
    mark = trim(full.crop((0, bands[0][0], full.width, bands[0][1])))

    # ── Raster ────────────────────────────────────────────────────────────────
    for img, name in ((full, "logo-full"), (mark, "logo-mark")):
        img.save(f"{OUT}/{name}.png")
        relight(img).save(f"{OUT}/{name}-light.png")

    side = int(max(mark.size) * 1.18)
    fav = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    fav.paste(mark, ((side - mark.width) // 2, (side - mark.height) // 2), mark)
    for px in (512, 180, 32):
        fav.resize((px, px), Image.LANCZOS).save(f"{OUT}/favicon-{px}.png")

    og = Image.new("RGB", (1200, 630), (247, 245, 240))
    lock = full.resize((620, round(full.height * 620 / full.width)), Image.LANCZOS)
    og.paste(lock, ((1200 - lock.width) // 2, (630 - lock.height) // 2 - 10), lock)
    og.paste(Image.new("RGB", (150, 3), (182, 106, 60)), ((1200 - 150) // 2, 630 - 96))
    og.save(f"{OUT}/og-image.png")

    # ── Vector ────────────────────────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as work:
        for img, name, label in ((full, "logo-full", "Axomis Labs — Thoughtful Solutions"),
                                 (mark, "logo-mark", "Axomis Labs")):
            sub = os.path.join(work, name)
            os.makedirs(sub)
            paths = trace(img, sub)
            write_svg(f"{OUT}/{name}.svg", paths, img.size, DARK, label)
            write_svg(f"{OUT}/{name}-light.svg", paths, img.size, LIGHT, label)
            n = sum(len(v) for v in paths.values())
            print(f"{name}: {img.size[0]}x{img.size[1]}, {n} traced paths")

    # Favicon: one file that inverts itself against dark browser chrome.
    inner = re.search(r"(<g transform=.*</g>)", open(f"{OUT}/logo-mark.svg").read(), re.S).group(1)
    inner = inner.replace(f'fill="{CHARCOAL}"', 'class="ink"')
    s = int(max(mark.size) * 1.18)
    dx, dy = (s - mark.width) / 2, (s - mark.height) / 2
    open(f"{OUT}/favicon.svg", "w").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {s} {s}" '
        f'role="img" aria-label="Axomis Labs">\n<title>Axomis Labs</title>\n'
        f"<style>\n.ink {{ fill: {CHARCOAL}; }}\n"
        f"@media (prefers-color-scheme: dark) {{ .ink {{ fill: {IVORY}; }} }}\n</style>\n"
        f'<g transform="translate({dx:.1f},{dy:.1f})">\n{inner}\n</g>\n</svg>\n')

    print(f"\nwrote {len(os.listdir(OUT)) - 1} files to site/assets/")


if __name__ == "__main__":
    main()
