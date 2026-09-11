"""
Unified Media Frame Extraction and Cache for Click Chaos Module.
Extracts and caches video, animated GIF, and image frames from memes/*.mp4
and cached Reddit memes (r/memes, r/dankmemes) using OpenCV and Pillow.
Supports dynamic discovery of videos, GIFs, and static memes with letterboxed scaling.
"""

import os
import random
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image, ImageSequence, ImageTk

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

MEMES_DIR = Path(__file__).parent.parent.parent / "memes"
DEFAULT_VID = MEMES_DIR / "explosionvideo.mp4"

_cached_media_pil_frames: Dict[str, List[Image.Image]] = {}
_lock = threading.Lock()


@dataclass
class MediaSourceItem:
    path: Path
    title: str
    source: str       # "local" or "r/memes", "r/dankmemes"
    media_type: str   # "video", "gif", or "image"


def get_available_videos() -> List[Path]:
    """Returns list of all available .mp4 video files in memes/."""
    if not MEMES_DIR.exists():
        return []
    return list(MEMES_DIR.glob("*.mp4"))


def get_available_media_items() -> List[MediaSourceItem]:
    """
    Returns a unified pool of all available media items:
    - Local videos (explosionvideo.mp4, etc.)
    - Reddit memes (images, animated GIFs, videos) from r/memes cache
    """
    items: List[MediaSourceItem] = []

    # 1. Local videos in memes/*.mp4
    for vid_file in get_available_videos():
        title = vid_file.stem.upper()
        items.append(MediaSourceItem(
            path=vid_file,
            title=title,
            source="local",
            media_type="video",
        ))

    # 2. Reddit cached memes from random_media.reddit_memes
    try:
        from random_media.reddit_memes import get_reddit_fetcher
        fetcher = get_reddit_fetcher()
        for meme in fetcher.get_available_memes():
            items.append(MediaSourceItem(
                path=meme.file_path,
                title=meme.title,
                source=f"r/{meme.subreddit}",
                media_type=meme.media_type,
            ))
    except Exception as err:
        print(f"[VideoFrames] Notice: could not load Reddit memes pool: {err}")

    # Fallback if no media exists at all
    if not items and DEFAULT_VID.exists():
        items.append(MediaSourceItem(
            path=DEFAULT_VID,
            title="EXPLOSION",
            source="local",
            media_type="video",
        ))

    return items


def _fit_image_to_frame(img: Image.Image, target_width: int, target_height: int) -> Image.Image:
    """Scales image preserving aspect ratio with clean dark letterboxing."""
    img_ratio = img.width / max(1, img.height)
    target_ratio = target_width / target_height

    if img_ratio > target_ratio:
        new_w = target_width
        new_h = max(1, int(target_width / img_ratio))
    else:
        new_h = target_height
        new_w = max(1, int(target_height * img_ratio))

    resample_filter = Image.Resampling.BILINEAR if hasattr(Image, "Resampling") else Image.BILINEAR
    resized = img.resize((new_w, new_h), resample_filter)

    canvas = Image.new("RGB", (target_width, target_height), (14, 14, 18))
    paste_x = (target_width - new_w) // 2
    paste_y = (target_height - new_h) // 2

    if resized.mode in ("RGBA", "LA"):
        canvas.paste(resized, (paste_x, paste_y), mask=resized)
    else:
        if resized.mode != "RGB":
            resized = resized.convert("RGB")
        canvas.paste(resized, (paste_x, paste_y))

    return canvas


def load_media_pil_frames(
    media_path: Optional[str] = None,
    target_width: int = 160,
    target_height: int = 218,
    max_frames: int = 90,
) -> List[Image.Image]:
    """
    Decodes and returns cached list of PIL Image frames for a given media file.
    Supports MP4 videos (OpenCV), animated GIFs (Pillow), and static images (Pillow).
    """
    path_str = str(Path(media_path or DEFAULT_VID).resolve())
    cache_key = f"{path_str}_{target_width}x{target_height}"

    with _lock:
        if cache_key in _cached_media_pil_frames and _cached_media_pil_frames[cache_key]:
            return _cached_media_pil_frames[cache_key]

    frames: List[Image.Image] = []
    p = Path(path_str)
    ext = p.suffix.lower()

    if p.exists():
        # Case 1: Animated GIF
        if ext == ".gif":
            try:
                with Image.open(p) as gif_img:
                    for idx, frame in enumerate(ImageSequence.Iterator(gif_img)):
                        if len(frames) >= max_frames:
                            break
                        # Sample frames if long GIF
                        if idx % 1 == 0:
                            fitted = _fit_image_to_frame(frame, target_width, target_height)
                            frames.append(fitted)
            except Exception as err:
                print(f"[MediaFrames] Error decoding GIF {path_str}: {err}")

        # Case 2: MP4 Video via OpenCV
        elif ext in (".mp4", ".webm") and HAS_OPENCV:
            try:
                cap = cv2.VideoCapture(path_str)
                frame_idx = 0
                while cap.isOpened() and len(frames) < max_frames:
                    ret, cv_frame = cap.read()
                    if not ret:
                        break
                    if frame_idx % 2 == 0:
                        rgb = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
                        pil_img = Image.fromarray(rgb)
                        fitted = _fit_image_to_frame(pil_img, target_width, target_height)
                        frames.append(fitted)
                    frame_idx += 1
                cap.release()
            except Exception as err:
                print(f"[MediaFrames] Error decoding video {path_str}: {err}")

        # Case 3: Static Meme Image (PNG, JPG, WEBP)
        elif ext in (".png", ".jpg", ".jpeg", ".webp"):
            try:
                with Image.open(p) as static_img:
                    fitted = _fit_image_to_frame(static_img, target_width, target_height)
                    frames.append(fitted)
            except Exception as err:
                print(f"[MediaFrames] Error decoding image {path_str}: {err}")

    # Fallback if media file or decoder failed
    if not frames:
        print(f"[MediaFrames] Generating placeholder frames for {path_str}")
        for i in range(12):
            img = Image.new("RGB", (target_width, target_height), (255, 60 + i * 15, 0))
            frames.append(img)

    with _lock:
        _cached_media_pil_frames[cache_key] = frames

    return frames


# Backward compatibility aliases
def load_video_pil_frames(
    video_path: Optional[str] = None,
    target_width: int = 160,
    target_height: int = 218,
    max_frames: int = 90,
) -> List[Image.Image]:
    return load_media_pil_frames(video_path, target_width, target_height, max_frames)


def get_media_tk_frames(
    master,
    media_path: Optional[str] = None,
    target_width: int = 160,
    target_height: int = 218,
) -> List[ImageTk.PhotoImage]:
    """Returns Tkinter PhotoImages for the media file, bound to master."""
    pil_frames = load_media_pil_frames(
        media_path=media_path,
        target_width=target_width,
        target_height=target_height,
    )
    return [ImageTk.PhotoImage(f, master=master) for f in pil_frames]


def get_video_tk_frames(
    master,
    video_path: Optional[str] = None,
    target_width: int = 160,
    target_height: int = 218,
) -> List[ImageTk.PhotoImage]:
    return get_media_tk_frames(master, video_path, target_width, target_height)


def _async_prewarm():
    try:
        load_media_pil_frames()
    except Exception:
        pass


threading.Thread(target=_async_prewarm, daemon=True).start()
