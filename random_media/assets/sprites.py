"""
High-Performance Transparent Sprite Factory for Click Chaos Engine.
Pre-renders and caches pixel-crisp transparent PNG sprites using Pillow:
- Tiny Bouncing Cat sprite (44x44)
- 8-frame spinning Low-Poly Rat sprite sequence (56x56)
- Soul-Staring Corner Furby sprite (160x160)
"""

import math
from typing import List, Optional
from PIL import Image, ImageDraw, ImageTk


def create_cat_image(size: int = 44) -> Image.Image:
    """Renders the unhinged manic goblin cat with alpha transparency."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    scale = size / 100.0

    def s(x, y):
        return (x * scale, y * scale)

    # Magenta chaos aura glow
    d.ellipse((s(5, 5), s(95, 95)), fill=(255, 0, 85, 45))

    # Bristled curling tail
    tail_pts = [s(25, 65), s(10, 45), s(15, 20), s(25, 25), s(18, 50), s(30, 60)]
    d.polygon(tail_pts, fill=(26, 26, 26, 255), outline=(255, 0, 85, 255))

    # Arched back & bristled body
    body_pts = [
        s(25, 75), s(30, 55), s(35, 40), s(50, 32), s(65, 40),
        s(75, 55), s(80, 75), s(70, 85), s(35, 85)
    ]
    d.polygon(body_pts, fill=(18, 18, 22, 255), outline=(255, 51, 102, 255))
    # Fur tufts
    d.polygon([s(45, 33), s(50, 20), s(55, 33)], fill=(255, 0, 85, 255))
    d.polygon([s(32, 45), s(24, 38), s(35, 52)], fill=(255, 0, 85, 255))

    # Large goblin head
    d.ellipse((s(30, 35), s(70, 75)), fill=(24, 24, 28, 255), outline=(255, 0, 85, 255), width=int(max(1, 2 * scale)))

    # Spiky ears
    d.polygon([s(32, 42), s(20, 15), s(45, 36)], fill=(24, 24, 28, 255), outline=(255, 0, 85, 255))
    d.polygon([s(28, 38), s(23, 20), s(40, 36)], fill=(255, 0, 85, 180))

    d.polygon([s(68, 42), s(80, 15), s(55, 36)], fill=(24, 24, 28, 255), outline=(255, 0, 85, 255))
    d.polygon([s(72, 38), s(77, 20), s(60, 36)], fill=(255, 0, 85, 180))

    # Mismatched Unhinged Eyes
    # Left: Glowing bright green-yellow orb
    d.ellipse((s(36, 45), s(48, 57)), fill=(0, 255, 102, 255), outline=(255, 255, 255, 255))
    d.ellipse((s(40, 48), s(45, 53)), fill=(0, 0, 0, 255))
    d.point(s(42, 49), fill=(255, 255, 255, 255))

    # Right: Hypnotic fiery red-orange slit
    d.ellipse((s(52, 45), s(64, 57)), fill=(255, 51, 0, 255), outline=(255, 255, 255, 255))
    d.ellipse((s(56, 47), s(60, 55)), fill=(0, 0, 0, 255))
    d.point(s(57, 49), fill=(255, 255, 255, 255))

    # Wide needle-tooth mouth
    d.arc((s(38, 55), s(62, 70)), 0, 180, fill=(255, 0, 85, 255), width=int(max(1, 2 * scale)))
    # Teeth
    d.polygon([s(43, 62), s(46, 67), s(49, 62)], fill=(255, 255, 255, 255))
    d.polygon([s(51, 62), s(54, 67), s(57, 62)], fill=(255, 255, 255, 255))

    # Whiskers
    d.line([s(32, 58), s(12, 54)], fill=(255, 255, 0, 255), width=1)
    d.line([s(32, 63), s(10, 66)], fill=(255, 255, 0, 255), width=1)
    d.line([s(68, 58), s(88, 54)], fill=(255, 255, 0, 255), width=1)
    d.line([s(68, 63), s(90, 66)], fill=(255, 255, 0, 255), width=1)

    # Claws
    d.line([s(34, 82), s(30, 90)], fill=(255, 255, 255, 255), width=int(max(1, 2 * scale)))
    d.line([s(40, 84), s(40, 92)], fill=(255, 255, 255, 255), width=int(max(1, 2 * scale)))
    d.line([s(66, 82), s(62, 90)], fill=(255, 255, 255, 255), width=int(max(1, 2 * scale)))
    d.line([s(72, 84), s(72, 92)], fill=(255, 255, 255, 255), width=int(max(1, 2 * scale)))

    return img


def create_rat_base_image(size: int = 56) -> Image.Image:
    """Renders the base low-poly rat sprite."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    scale = size / 100.0

    def s(x, y):
        return (x * scale, y * scale)

    # Low-poly tail
    d.polygon([s(70, 55), s(85, 45), s(95, 30), s(90, 38), s(75, 60)], fill=(255, 141, 161, 255), outline=(194, 24, 91, 255))

    # Low-poly faceted body
    d.polygon([s(40, 65), s(58, 75), s(75, 60), s(58, 50)], fill=(60, 60, 68, 255), outline=(17, 17, 21, 255))
    d.polygon([s(25, 55), s(40, 65), s(58, 50), s(40, 42)], fill=(112, 112, 122, 255), outline=(17, 17, 21, 255))
    d.polygon([s(40, 42), s(58, 50), s(72, 40), s(54, 32)], fill=(176, 176, 184, 255), outline=(17, 17, 21, 255))

    # Low-poly snout & head
    d.polygon([s(25, 55), s(40, 42), s(30, 32), s(15, 45)], fill=(176, 176, 184, 255), outline=(17, 17, 21, 255))
    d.polygon([s(15, 45), s(30, 32), s(18, 24), s(8, 35)], fill=(112, 112, 122, 255), outline=(17, 17, 21, 255))
    # Pink nose tip
    d.polygon([s(8, 35), s(18, 24), s(12, 20), s(5, 28)], fill=(255, 141, 161, 255), outline=(194, 24, 91, 255))

    # Low-poly Ears
    d.polygon([s(32, 28), s(42, 16), s(46, 26)], fill=(112, 112, 122, 255), outline=(17, 17, 21, 255))
    d.polygon([s(42, 16), s(48, 20), s(46, 26)], fill=(255, 141, 161, 255))

    # Beady Red Eyes
    d.polygon([s(18, 32), s(22, 30), s(24, 34), s(20, 36)], fill=(255, 0, 51, 255), outline=(255, 255, 255, 255))

    # Paws
    d.polygon([s(28, 62), s(32, 72), s(24, 70)], fill=(255, 141, 161, 255))
    d.polygon([s(60, 72), s(66, 82), s(56, 80)], fill=(255, 141, 161, 255))

    # Neon wireframe accent line
    d.line([s(25, 55), s(40, 42), s(58, 50)], fill=(0, 255, 204, 200), width=1)

    return img


def create_furby_image(size: int = 160) -> Image.Image:
    """Renders the soul-staring cursed Furby sprite."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    scale = size / 200.0

    def s(x, y):
        return (x * scale, y * scale)

    # Ominous purple void aura
    d.ellipse((s(10, 10), s(190, 190)), fill=(74, 14, 78, 90))

    # Big pointy furry ears
    # Left Ear
    d.polygon([s(45, 60), s(15, 20), s(60, 35)], fill=(38, 50, 56, 255), outline=(16, 32, 39, 255), width=2)
    d.polygon([s(40, 55), s(22, 28), s(52, 38)], fill=(244, 143, 177, 255))
    # Right Ear
    d.polygon([s(155, 60), s(185, 20), s(140, 35)], fill=(38, 50, 56, 255), outline=(16, 32, 39, 255), width=2)
    d.polygon([s(160, 55), s(178, 28), s(148, 38)], fill=(244, 143, 177, 255))

    # Fuzzy Gremlin Body
    d.ellipse((s(30, 45), s(170, 180)), fill=(33, 33, 33, 255), outline=(17, 17, 17, 255), width=3)
    # Fluffy belly patch
    d.ellipse((s(65, 110), s(135, 170)), fill=(236, 239, 241, 230))

    # Feet
    d.ellipse((s(50, 170), s(85, 188)), fill=(255, 183, 77, 255), outline=(230, 81, 0, 255), width=2)
    d.ellipse((s(115, 170), s(150, 188)), fill=(255, 183, 77, 255), outline=(230, 81, 0, 255), width=2)

    # Hard Molded Plastic Faceplate
    d.ellipse((s(55, 55), s(145, 135)), fill=(207, 216, 220, 255), outline=(55, 71, 79, 255), width=3)

    # Stiff Eyelashes
    for angle in [-35, -15, 15, 35]:
        rad = math.radians(angle)
        # Left eye lashes
        x0, y0 = s(75, 75)
        d.line([(x0 + math.sin(rad) * 12, y0 - math.cos(rad) * 12), (x0, y0)], fill=(0, 0, 0, 255), width=2)
        # Right eye lashes
        x1, y1 = s(125, 75)
        d.line([(x1 + math.sin(rad) * 12, y1 - math.cos(rad) * 12), (x1, y1)], fill=(0, 0, 0, 255), width=2)

    # Giant Glass Robotic Eyes
    # Left Eye
    d.ellipse((s(60, 68), s(94, 102)), fill=(0, 188, 212, 255), outline=(0, 96, 100, 255), width=2)
    d.ellipse((s(70, 78), s(84, 92)), fill=(0, 0, 0, 255))
    # Red sensor dot
    d.ellipse((s(75, 83), s(79, 87)), fill=(255, 0, 68, 255))
    # White highlight
    d.ellipse((s(66, 73), s(74, 81)), fill=(255, 255, 255, 240))

    # Right Eye
    d.ellipse((s(106, 68), s(140, 102)), fill=(0, 188, 212, 255), outline=(0, 96, 100, 255), width=2)
    d.ellipse((s(116, 78), s(130, 92)), fill=(0, 0, 0, 255))
    # Red sensor dot
    d.ellipse((s(121, 83), s(125, 87)), fill=(255, 0, 68, 255))
    # White highlight
    d.ellipse((s(112, 73), s(120, 81)), fill=(255, 255, 255, 240))

    # Parted Yellow Molded Beak
    d.polygon([s(90, 105), s(110, 105), s(100, 122)], fill=(253, 216, 53, 255), outline=(230, 81, 0, 255), width=2)
    # Pink mechanical tongue
    d.ellipse((s(96, 110), s(104, 118)), fill=(255, 64, 129, 255))
    d.polygon([s(92, 114), s(108, 114), s(100, 126)], fill=(245, 127, 23, 255), outline=(230, 81, 0, 255), width=1)

    return img


_cached_cat_pil = None
_cached_rat_pils: List[Image.Image] = []
_cached_furby_pil = None


def get_cat_sprite(master=None) -> ImageTk.PhotoImage:
    """Returns Tkinter PhotoImage for the tiny bouncing cat, optionally bound to master."""
    global _cached_cat_pil
    if _cached_cat_pil is None:
        _cached_cat_pil = create_cat_image(44)
    return ImageTk.PhotoImage(_cached_cat_pil, master=master)


def get_rat_frames(master=None) -> List[ImageTk.PhotoImage]:
    """Returns 8-frame 3D rotation sequence for the spinning low-poly rat, optionally bound to master."""
    global _cached_rat_pils
    if not _cached_rat_pils:
        base_img = create_rat_base_image(56)
        for i in range(8):
            angle = i * 45.0
            rotated = base_img.rotate(angle, resample=Image.Resampling.BICUBIC)
            _cached_rat_pils.append(rotated)
    return [ImageTk.PhotoImage(img, master=master) for img in _cached_rat_pils]


def get_furby_sprite(master=None) -> ImageTk.PhotoImage:
    """Returns Tkinter PhotoImage for the soul-staring Furby, optionally bound to master."""
    global _cached_furby_pil
    if _cached_furby_pil is None:
        _cached_furby_pil = create_furby_image(160)
    return ImageTk.PhotoImage(_cached_furby_pil, master=master)

