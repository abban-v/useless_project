"""
Reddit Meme Fetcher and Local Cache Manager.
Sources memes (images, animated GIFs, and videos only) from r/memes and related subreddits.
Uses public meme-api and Reddit RSS feeds with automatic fallbacks and optional Reddit OAuth.
Downloads media asynchronously into memes/reddit_cache/ to ensure zero UI freezing.
"""

import hashlib
import json
import os
import random
import re
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional
import requests

from config import (
    REDDIT_CACHE_MAX_FILES,
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_FETCH_INTERVAL_SECONDS,
    REDDIT_SUBREDDITS,
)

CACHE_DIR = Path(__file__).parent.parent / "memes" / "reddit_cache"
METADATA_FILE = CACHE_DIR / "metadata.json"

VALID_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VALID_ANIM_EXTS = {".gif"}
VALID_VIDEO_EXTS = {".mp4", ".webm"}
ALL_VALID_EXTS = VALID_IMAGE_EXTS | VALID_ANIM_EXTS | VALID_VIDEO_EXTS

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UselessMemeBot/1.0"


@dataclass
class MemeItem:
    file_path: Path
    title: str
    subreddit: str
    url: str
    media_type: str  # "video", "gif", or "image"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["file_path"] = str(self.file_path)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "MemeItem":
        return cls(
            file_path=Path(data["file_path"]),
            title=data.get("title", "Reddit Meme"),
            subreddit=data.get("subreddit", "memes"),
            url=data.get("url", ""),
            media_type=data.get("media_type", "image"),
        )


class RedditMemeFetcher:
    """
    Asynchronous meme fetcher and cache manager for r/memes.
    Downloads strictly media files (images, animated gifs, videos) into local cache.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.cache_dir / "metadata.json"

        self._lock = threading.Lock()
        self._cached_items: Dict[str, MemeItem] = {}
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        # Load existing local cache on instantiation for instant availability
        self._load_local_cache()

    def _load_local_cache(self):
        """Scans local cache directory and loads existing valid media items."""
        metadata = {}
        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except Exception as err:
                print(f"[RedditMemes] Warning loading metadata: {err}")

        with self._lock:
            self._cached_items.clear()
            for media_file in self.cache_dir.iterdir():
                if media_file.is_file() and media_file.suffix.lower() in ALL_VALID_EXTS:
                    rel_name = media_file.name
                    meta = metadata.get(rel_name, {})
                    title = meta.get("title", media_file.stem.replace("_", " "))
                    sub = meta.get("subreddit", "memes")
                    url = meta.get("url", "")
                    ext = media_file.suffix.lower()

                    if ext in VALID_VIDEO_EXTS:
                        mtype = "video"
                    elif ext in VALID_ANIM_EXTS:
                        mtype = "gif"
                    else:
                        mtype = "image"

                    item = MemeItem(
                        file_path=media_file,
                        title=title,
                        subreddit=sub,
                        url=url,
                        media_type=mtype,
                    )
                    self._cached_items[rel_name] = item

        print(f"[RedditMemes] Loaded {len(self._cached_items)} cached memes from {self.cache_dir}")

    def _save_metadata(self):
        """Persists metadata to metadata.json."""
        with self._lock:
            data = {k: v.to_dict() for k, v in self._cached_items.items()}
        try:
            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as err:
            print(f"[RedditMemes] Failed saving metadata: {err}")

    def get_available_memes(self) -> List[MemeItem]:
        """Returns list of currently cached and valid meme items."""
        with self._lock:
            return [m for m in self._cached_items.values() if m.file_path.exists()]

    def get_random_meme(self) -> Optional[MemeItem]:
        """Returns a random cached meme item, or None if cache is empty."""
        items = self.get_available_memes()
        if not items:
            return None
        return random.choice(items)

    def fetch_batch_sync(self, count: int = 30) -> int:
        """
        Synchronously fetches a batch of memes from Reddit sources and downloads them.
        Returns the number of newly downloaded items.
        """
        candidates: List[dict] = []

        # 1. Try meme-api.com for each configured subreddit
        for sub in REDDIT_SUBREDDITS:
            try:
                url = f"https://meme-api.com/gimme/{sub}/{count}"
                resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    memes = data.get("memes", [])
                    for m in memes:
                        if m.get("nsfw") or m.get("spoiler"):
                            continue
                        m_url = m.get("url", "")
                        if self._is_supported_media_url(m_url):
                            candidates.append({
                                "title": m.get("title", "Reddit Meme"),
                                "subreddit": m.get("subreddit", sub),
                                "url": m_url,
                            })
            except Exception as err:
                print(f"[RedditMemes] meme-api query failed for r/{sub}: {err}")

        # 2. Fallback: Parse Reddit RSS feed directly if candidates are low
        if len(candidates) < 5:
            for sub in REDDIT_SUBREDDITS:
                try:
                    rss_url = f"https://www.reddit.com/r/{sub}/.rss?limit=40"
                    r = requests.get(rss_url, headers={"User-Agent": USER_AGENT}, timeout=8)
                    if r.status_code == 200:
                        root = ET.fromstring(r.content)
                        ns = {"atom": "http://www.w3.org/2005/Atom"}
                        for entry in root.findall("atom:entry", ns):
                            title_elem = entry.find("atom:title", ns)
                            content_elem = entry.find("atom:content", ns)
                            title = title_elem.text if title_elem is not None else "Reddit Meme"
                            text = content_elem.text if content_elem is not None else ""
                            matches = re.findall(
                                r'href="(https://[^"]+\.(?:jpg|jpeg|png|webp|gif|mp4))"',
                                text,
                                re.IGNORECASE,
                            )
                            for match_url in matches:
                                if self._is_supported_media_url(match_url):
                                    candidates.append({
                                        "title": title,
                                        "subreddit": sub,
                                        "url": match_url,
                                    })
                except Exception as err:
                    print(f"[RedditMemes] RSS feed parse error for r/{sub}: {err}")

        # 3. Optional Reddit OAuth if configured
        if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
            try:
                oauth_candidates = self._fetch_reddit_oauth(REDDIT_SUBREDDITS[0], count)
                candidates.extend(oauth_candidates)
            except Exception as err:
                print(f"[RedditMemes] Reddit OAuth error: {err}")

        # Deduplicate candidates by URL
        seen_urls = set()
        unique_candidates = []
        for c in candidates:
            if c["url"] not in seen_urls:
                seen_urls.add(c["url"])
                unique_candidates.append(c)

        print(f"[RedditMemes] Sourced {len(unique_candidates)} unique media meme candidates from r/memes.")

        # Download up to batch count
        downloaded = 0
        for item in unique_candidates:
            if self._stop_event.is_set():
                break
            if self._download_candidate(item):
                downloaded += 1

        # Prune older files if cache exceeds limit
        self._prune_cache()
        self._save_metadata()
        return downloaded

    def _is_supported_media_url(self, url: str) -> bool:
        """Returns True if the URL points directly to an image, gif, or video file."""
        if not url:
            return False
        clean_url = url.split("?")[0].lower()
        return any(clean_url.endswith(ext) for ext in ALL_VALID_EXTS)

    def _download_candidate(self, item: dict) -> bool:
        """Downloads a single meme media item to local cache if not present."""
        url = item["url"]
        clean_url = url.split("?")[0]
        ext = os.path.splitext(clean_url)[1].lower()
        if ext not in ALL_VALID_EXTS:
            return False

        # Generate deterministic filename from URL hash
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
        dest_filename = f"meme_{url_hash}{ext}"
        dest_path = self.cache_dir / dest_filename

        if dest_path.exists() and dest_path.stat().st_size > 512:
            return False  # Already downloaded

        try:
            resp = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=12,
                stream=True,
            )
            if resp.status_code == 200:
                # Save to temp file first then atomic rename
                temp_path = self.cache_dir / f"tmp_{dest_filename}"
                with open(temp_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=16384):
                        if chunk:
                            f.write(chunk)

                if temp_path.stat().st_size > 512:
                    if temp_path.exists() and dest_path.exists():
                        dest_path.unlink()
                    temp_path.rename(dest_path)

                    ext_lower = ext.lower()
                    if ext_lower in VALID_VIDEO_EXTS:
                        mtype = "video"
                    elif ext_lower in VALID_ANIM_EXTS:
                        mtype = "gif"
                    else:
                        mtype = "image"

                    meme_item = MemeItem(
                        file_path=dest_path,
                        title=item.get("title", "Reddit Meme"),
                        subreddit=item.get("subreddit", "memes"),
                        url=url,
                        media_type=mtype,
                    )
                    with self._lock:
                        self._cached_items[dest_filename] = meme_item
                    print(f"[RedditMemes] Downloaded [{mtype.upper()}] r/{meme_item.subreddit}: {meme_item.title[:30]}")
                    return True
                else:
                    if temp_path.exists():
                        temp_path.unlink()
        except Exception as err:
            print(f"[RedditMemes] Error downloading {url}: {err}")
        return False

    def _prune_cache(self):
        """Maintains cache at or below REDDIT_CACHE_MAX_FILES by removing oldest files."""
        with self._lock:
            items = list(self._cached_items.values())

        if len(items) <= REDDIT_CACHE_MAX_FILES:
            return

        # Sort by file modification time (oldest first)
        def get_mtime(m: MemeItem) -> float:
            try:
                return m.file_path.stat().st_mtime
            except Exception:
                return 0.0

        items.sort(key=get_mtime)
        excess_count = len(items) - REDDIT_CACHE_MAX_FILES
        to_delete = items[:excess_count]

        for item in to_delete:
            try:
                if item.file_path.exists():
                    item.file_path.unlink()
                with self._lock:
                    self._cached_items.pop(item.file_path.name, None)
            except Exception as err:
                print(f"[RedditMemes] Error pruning {item.file_path}: {err}")

        print(f"[RedditMemes] Pruned {len(to_delete)} old cached memes (cache size now {len(self._cached_items)}).")

    def _fetch_reddit_oauth(self, subreddit: str, count: int) -> List[dict]:
        """Fetches memes directly via official Reddit OAuth."""
        auth = requests.auth.HTTPBasicAuth(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
        data = {"grant_type": "client_credentials"}
        token_resp = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=auth,
            data=data,
            headers={"User-Agent": USER_AGENT},
            timeout=8,
        )
        if token_resp.status_code != 200:
            return []
        token = token_resp.json().get("access_token")
        headers = {
            "Authorization": f"bearer {token}",
            "User-Agent": USER_AGENT,
        }
        res = requests.get(
            f"https://oauth.reddit.com/r/{subreddit}/hot?limit={count}",
            headers=headers,
            timeout=8,
        )
        if res.status_code != 200:
            return []
        posts = res.json().get("data", {}).get("children", [])
        candidates = []
        for p in posts:
            pdata = p.get("data", {})
            if pdata.get("over_18") or pdata.get("spoiler"):
                continue
            url = pdata.get("url", "")
            if self._is_supported_media_url(url):
                candidates.append({
                    "title": pdata.get("title", "Reddit Meme"),
                    "subreddit": subreddit,
                    "url": url,
                })
        return candidates

    def start_background_worker(self):
        """Starts daemon thread to keep cache fresh in background without blocking."""
        if self._worker_thread and self._worker_thread.is_alive():
            return

        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._background_worker_loop,
            name="RedditMemeWorker",
            daemon=True,
        )
        self._worker_thread.start()
        print("[RedditMemes] Background meme caching worker started.")

    def _background_worker_loop(self):
        """Background loop that fetches batches periodically."""
        # Initial fetch on startup
        try:
            self.fetch_batch_sync(count=25)
        except Exception as err:
            print(f"[RedditMemes] Background initial fetch error: {err}")

        while not self._stop_event.is_set():
            # Wait for the interval or until stopped
            if self._stop_event.wait(timeout=REDDIT_FETCH_INTERVAL_SECONDS):
                break

            # If cache is getting low or after interval, fetch again
            try:
                self.fetch_batch_sync(count=20)
            except Exception as err:
                print(f"[RedditMemes] Background refresh error: {err}")

    def stop(self):
        """Stops the background worker thread."""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.5)
        print("[RedditMemes] Background meme caching worker stopped.")


# Global singleton instance
_fetcher_instance: Optional[RedditMemeFetcher] = None
_instance_lock = threading.Lock()


def get_reddit_fetcher() -> RedditMemeFetcher:
    """Returns singleton instance of RedditMemeFetcher."""
    global _fetcher_instance
    with _instance_lock:
        if _fetcher_instance is None:
            _fetcher_instance = RedditMemeFetcher()
        return _fetcher_instance
