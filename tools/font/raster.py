"""Shared-bearing glyph cells, sized from every requested glyph, not one anchor."""

import math
from PIL import Image, ImageDraw


def layout(
    font, chars, pixel_size, skew=0, top_padding=1, bottom_padding=1, fit_height=None
):
    if not chars or pixel_size < 1 or not 0 <= skew <= 1:
        raise ValueError("Invalid raster inputs")
    if any(
        type(p) is not int or not 0 <= p <= 32 for p in (top_padding, bottom_padding)
    ):
        raise ValueError("Invalid glyph padding")
    boxes = [font.getbbox(ch) for ch in chars]
    left = min(0, min(b[0] for b in boxes))
    top = min(b[1] for b in boxes)
    right = max(pixel_size, max(b[2] for b in boxes))
    bottom = max(b[3] for b in boxes)
    raster_height = max(pixel_size, bottom - top) + top_padding + bottom_padding
    if fit_height is not None and (type(fit_height) is not int or fit_height < 1):
        raise ValueError("Invalid target line height")
    height = fit_height or raster_height
    width = right - left
    return dict(
        source_bounds=[left, top, right, bottom],
        origin=[-left, top_padding - top],
        base_width=width,
        width=width + math.ceil((height - 1) * skew),
        height=height,
        raster_height=raster_height,
        vertical_fit_scale=height / raster_height,
        top_padding=top_padding,
        bottom_padding=bottom_padding,
        skew=skew,
    )


def render(font, ch, metrics):
    mask = Image.new("L", (metrics["base_width"], metrics["raster_height"]), 0)
    ImageDraw.Draw(mask).text(tuple(metrics["origin"]), ch, font=font, fill=255)
    # Compare against a generously bordered independent canvas before shearing.
    border = 64
    reference = Image.new("L", (mask.width + 2 * border, mask.height + 2 * border), 0)
    ImageDraw.Draw(reference).text(
        (metrics["origin"][0] + border, metrics["origin"][1] + border),
        ch,
        font=font,
        fill=255,
    )
    if sum(mask.tobytes()) != sum(reference.tobytes()):
        raise ValueError("Glyph cell clips source ink: " + repr(ch))
    if mask.height != metrics["height"]:
        # Fit the whole shared-bearing canvas. Never crop a glyph or align punctuation individually.
        mask = mask.resize((mask.width, metrics["height"]), Image.Resampling.LANCZOS)
    skew = metrics["skew"]
    if skew:
        mask = mask.transform(
            (metrics["width"], metrics["height"]),
            Image.Transform.AFFINE,
            (1, skew, -skew * (metrics["height"] - 1), 0, 1, 0),
            resample=Image.Resampling.BICUBIC,
        )
    if mask.getbbox() is None and not ch.isspace():
        raise ValueError("Empty raster for " + repr(ch))
    return mask
