"""Generate WhisperTyping .ico file. Run once to (re)create assets/icon.ico"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from PIL import Image, ImageDraw
import math


def _draw_mic(draw: ImageDraw.ImageDraw, size: int, color="white"):
    """Draw a microphone symbol scaled to `size`."""
    cx = size / 2

    # Microphone capsule
    cap_w = size * 0.155
    cap_top = size * 0.14
    cap_bot = size * 0.50
    cap_r = cap_w
    draw.rounded_rectangle(
        [cx - cap_w, cap_top, cx + cap_w, cap_bot],
        radius=cap_r,
        fill=color,
    )

    # Arc (sound-pickup curve below capsule)
    arc_x0 = size * 0.18
    arc_y0 = size * 0.38
    arc_x1 = size * 0.82
    arc_y1 = size * 0.65
    lw = max(2, round(size * 0.055))
    draw.arc([arc_x0, arc_y0, arc_x1, arc_y1], start=0, end=180,
             fill=color, width=lw)

    # Pole
    pole_top = (arc_y0 + arc_y1) / 2
    pole_bot = size * 0.78
    draw.line([cx, pole_top, cx, pole_bot], fill=color, width=lw)

    # Base
    base_w = size * 0.22
    draw.line([cx - base_w, pole_bot, cx + base_w, pole_bot],
              fill=color, width=lw)


def create_icon_image(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded square background — purple #6c5ce7
    r = size // 5
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r,
                            fill=(108, 92, 231, 255))

    _draw_mic(draw, size)
    return img


def main():
    out_path = os.path.join(os.path.dirname(__file__), "icon.ico")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    # Create the largest image; PIL will auto-resize for each size in ICO
    big = create_icon_image(256)
    big.save(
        out_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
    )
    print(f"Icon saved to {out_path}")


if __name__ == "__main__":
    main()
