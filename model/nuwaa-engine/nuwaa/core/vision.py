# -*- coding: utf-8 -*-
"""Crude image input: the honest, buildable version of 'make it see images, even low quality.'

How it works (no new architecture, no CNN, no separate vision model):
  1. Downsample the image to a TINY grid (default 16x16 = 256 pixels) and convert to grayscale.
  2. Each pixel's intensity (0-255) IS a valid byte-level token already (the tokenizer is byte-level,
     so token ids 0-255 already mean "this byte"). So the image becomes 256 ordinary tokens.
  3. Wrap them in IMG_START / IMG_END markers and feed them before the text, exactly like any other
     input. The transformer attends over them the same way it attends over text bytes.

Why this is genuinely "بس بجودة سيئة" (low quality on purpose, not a bug):
  - 16x16 grayscale throws away almost all detail on purpose, to keep the sequence short (256 tokens
    is cheap; a real photo at even 256x256 would be 65,536 tokens just for the image).
  - There is NO convolution, NO 2D spatial inductive bias — the model sees a flat list of 256 numbers,
    not a grid. It has to learn any notion of "neighboring pixel" purely from data, which is much harder
    than a real vision model. Expect it to pick up very coarse brightness/shape patterns at best, and
    only after training on real image+caption pairs — untrained, these bytes are as meaningless to it
    as any other untrained input.
  - This is a legitimate, real, working mechanism today. It is NOT a path to real image understanding
    (no OCR, no object detection, no spatial reasoning) — that needs a real vision encoder (CNN/ViT),
    which is a much bigger addition than this file. Ask for that explicitly if you want it later.

Requires Pillow (`pip install pillow`) — the one new dependency this adds.
"""
from .tokenizer import IMG_START, IMG_END

try:
    from PIL import Image
except ImportError:
    Image = None


def image_to_tokens(path: str, size: int = 16) -> list[int]:
    """size=16 -> 256 pixel-tokens (16*16). size=32 -> 1024 tokens. Bigger = less lossy, more tokens
    (quadratic attention cost — see the note in stages.py), so bigger is not automatically better."""
    if Image is None:
        raise RuntimeError("Pillow is not installed. Run: pip install pillow")
    img = Image.open(path).convert("L")          # grayscale
    img = img.resize((size, size), Image.BILINEAR)
    pixels = list(img.getdata())                 # size*size ints, 0-255 — already valid byte tokens
    return [IMG_START] + pixels + [IMG_END]


def describe_grid(path: str, size: int = 16) -> str:
    """Pure-debug helper (not fed to the model): render the same low-res grid as ASCII art, so a human
    can sanity-check what the model is actually being given — useful while you're building training data."""
    if Image is None:
        raise RuntimeError("Pillow is not installed. Run: pip install pillow")
    ramp = " .:-=+*#%@"
    img = Image.open(path).convert("L").resize((size, size), Image.BILINEAR)
    rows = []
    w, h = img.size
    px = img.load()
    for y in range(h):
        rows.append("".join(ramp[int(px[x, y] / 256 * len(ramp))] for x in range(w)))
    return "\n".join(rows)
