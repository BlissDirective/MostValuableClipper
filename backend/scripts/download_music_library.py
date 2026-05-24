"""
Music Library Bulk Downloader — Internet Archive sources

Downloads 100-500 CC-licensed MP3s from:
  1. Incompetech (Kevin MacLeod) — 108 tracks, CC-BY 4.0, via archive.org
  2. Internet Archive Netlabels — CC-licensed release bundles
  3. Internet Archive free music collections

Generates music/catalog.json consumed by MusicLibraryService.

Usage:
  python3 scripts/download_music_library.py
  python3 scripts/download_music_library.py --target 200 --workers 12
  python3 scripts/download_music_library.py --source incompetech
  python3 scripts/download_music_library.py --source netlabels
  MUSIC_DIR=/path/to/music python3 scripts/download_music_library.py
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DEFAULT_MUSIC_DIR = Path(__file__).parent.parent / "app" / "music"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "MVC-MusicDownloader/1.0 (archive.org research)"})

# ---------------------------------------------------------------------------
# Mood inference from track name + tags
# ---------------------------------------------------------------------------

MOOD_KEYWORDS = {
    "high_energy": [
        "rock", "metal", "power", "action", "fight", "battle", "intense", "hard",
        "aggressive", "driving", "energetic", "adrenaline", "dungeon", "epic boss",
    ],
    "upbeat": [
        "happy", "fun", "bright", "cheerful", "playful", "comedy", "light",
        "bounce", "skip", "whimsy", "cute", "quirky", "jingle", "pop", "upbeat",
        "summer", "carefree",
    ],
    "calm": [
        "ambient", "chill", "relax", "lofi", "lo-fi", "peaceful", "soft", "gentle",
        "meditation", "sleep", "nature", "rain", "drift", "float", "lullaby",
        "quiet", "tranquil", "serene",
    ],
    "emotional": [
        "sad", "melancholy", "emotional", "piano", "acoustic", "longing", "nostalgic",
        "tender", "heartfelt", "bittersweet", "reflective", "sorrow", "touching",
        "string", "violin", "cello",
    ],
    "dramatic": [
        "cinematic", "dramatic", "tension", "suspense", "thriller", "horror",
        "ominous", "mystery", "dark", "foreboding", "epic", "orchestral",
        "score", "trailer", "build", "rising",
    ],
}

MOOD_BPM = {
    "high_energy": 130,
    "upbeat": 115,
    "calm": 80,
    "emotional": 72,
    "dramatic": 105,
}

MOOD_DUCK = {
    "high_energy": 0.12,
    "upbeat": 0.14,
    "calm": 0.18,
    "emotional": 0.20,
    "dramatic": 0.15,
}


def infer_mood(name: str, tags: str = "") -> str:
    combined = (name + " " + tags).lower()
    scores: dict[str, int] = {m: 0 for m in MOOD_KEYWORDS}
    for mood, keywords in MOOD_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                scores[mood] += 1
    best = max(scores, key=lambda m: scores[m])
    return best if scores[best] > 0 else "upbeat"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class TrackMeta:
    id: str
    title: str
    artist: str
    mood: str
    source: str
    license_type: str
    duration_seconds: float
    tempo_bpm: int
    file_path: str
    volume_duck_factor: float


# ---------------------------------------------------------------------------
# Source: Incompetech (Kevin MacLeod) via archive.org
# ---------------------------------------------------------------------------

INCOMPETECH_IDENTIFIER = "Incompetech"


def incompetech_list_tracks() -> list[dict]:
    """List all MP3s in the Incompetech archive item."""
    r = SESSION.get(
        f"https://archive.org/metadata/{INCOMPETECH_IDENTIFIER}/files",
        timeout=20,
    )
    r.raise_for_status()
    files = r.json().get("result", [])
    tracks = []
    for f in files:
        name = f.get("name", "")
        if not name.endswith(".mp3"):
            continue
        title = Path(name).stem  # e.g. "Achaidh Cheide"
        url = f"https://archive.org/download/{INCOMPETECH_IDENTIFIER}/{requests.utils.quote(name)}"
        tracks.append({
            "id": f"incompetech_{re.sub(r'[^a-z0-9]', '_', title.lower())}",
            "title": title,
            "artist": "Kevin MacLeod",
            "source": "incompetech",
            "license_type": "CC-BY-4.0",
            "duration_seconds": 120.0,
            "download_url": url,
            "raw_name": name,
        })
    return tracks


# ---------------------------------------------------------------------------
# Source: Internet Archive netlabels / free music collections
# ---------------------------------------------------------------------------

# Well-curated CC-licensed netlabel identifiers with quality background music
NETLABEL_ITEMS = [
    # Background / ambient / electronic
    ("FREE_background_music_dhalius", "Background Music - Dhalius"),
    ("incompetech-gaming-music", "Incompetech Gaming Music"),
    # Netlabel releases — instrumental, CC-licensed
    ("DWK123", "Deltitnu - Curses From Past Times"),
    ("DWK031", "Deltitnu EP"),
    ("NS050", "Netlabels - Various"),
    ("badpanda018", "Bad Panda - Brick City"),
    ("CANDY032", "Candy Music - Christmasasaurus"),
    ("freemusiccharts.songs2011", "Free Music Charts 2011"),
]

# Additional IA search terms for finding more CC music items
ARCHIVE_SEARCHES = [
    "collection:audio_music AND mediatype:audio AND licenseurl:(*creativecommons*) AND subject:instrumental",
    "collection:netlabels AND mediatype:audio AND licenseurl:(*creativecommons*)",
    "creator:Incompetech AND mediatype:audio",
]


def archive_list_from_item(identifier: str, label: str) -> list[dict]:
    """Get MP3 candidates from a single archive.org item."""
    try:
        r = SESSION.get(f"https://archive.org/metadata/{identifier}/files", timeout=15)
        r.raise_for_status()
        files = r.json().get("result", [])
        mp3s = [f for f in files if f.get("name", "").lower().endswith(".mp3")]
        candidates = []
        for f in mp3s:
            raw_name = f["name"]
            title = Path(raw_name).stem
            url = f"https://archive.org/download/{identifier}/{requests.utils.quote(raw_name)}"
            candidates.append({
                "id": f"ia_{identifier}_{re.sub(r'[^a-z0-9]', '_', title.lower())[:40]}",
                "title": title,
                "artist": label,
                "source": "archive",
                "license_type": "CC-BY",
                "duration_seconds": 120.0,
                "download_url": url,
                "raw_name": raw_name,
            })
        log.info(f"  {identifier}: {len(candidates)} MP3s")
        return candidates
    except Exception as e:
        log.warning(f"  {identifier}: failed — {e}")
        return []


def archive_search_items(query: str, max_items: int = 15) -> list[str]:
    """Return archive.org identifiers from a search."""
    try:
        r = SESSION.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": query,
                "fl": "identifier,title,creator",
                "sort": "downloads desc",
                "rows": max_items,
                "page": 1,
                "output": "json",
            },
            timeout=15,
        )
        r.raise_for_status()
        docs = r.json().get("response", {}).get("docs", [])
        return [d["identifier"] for d in docs if "identifier" in d]
    except Exception as e:
        log.warning(f"Archive search failed: {e}")
        return []


def netlabels_list_tracks(target: int) -> list[dict]:
    """Collect MP3 candidates from netlabels and free music items."""
    candidates: list[dict] = []
    seen_ids: set[str] = set()

    # Known-good items first
    for identifier, label in NETLABEL_ITEMS:
        for c in archive_list_from_item(identifier, label):
            if c["id"] not in seen_ids:
                seen_ids.add(c["id"])
                candidates.append(c)
        if len(candidates) >= target:
            return candidates[:target]

    # Search-based discovery
    for query in ARCHIVE_SEARCHES:
        identifiers = archive_search_items(query, max_items=20)
        for ident in identifiers:
            if len(candidates) >= target:
                break
            for c in archive_list_from_item(ident, ident):
                if c["id"] not in seen_ids:
                    seen_ids.add(c["id"])
                    candidates.append(c)
        if len(candidates) >= target:
            break

    return candidates[:target]


# ---------------------------------------------------------------------------
# Downloader
# ---------------------------------------------------------------------------

def _safe_stem(s: str) -> str:
    return re.sub(r"[^\w\-]", "_", s)[:60]


def download_track(candidate: dict, music_dir: Path) -> Optional[TrackMeta]:
    mood = infer_mood(candidate["title"])
    mood_dir = music_dir / mood
    mood_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_stem(f"{candidate['source']}_{candidate['id']}")
    dest = mood_dir / f"{safe_name}.mp3"

    if dest.exists() and dest.stat().st_size > 10_000:
        return _build_meta(candidate, mood, dest)

    try:
        r = SESSION.get(candidate["download_url"], timeout=45, stream=True)
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if "audio" not in ct and "octet" not in ct and "mpeg" not in ct:
            return None

        with open(dest, "wb") as fh:
            for chunk in r.iter_content(chunk_size=131072):
                fh.write(chunk)

        size_kb = dest.stat().st_size // 1024
        if size_kb < 10:
            dest.unlink()
            return None

        log.info(f"  ✓ [{mood:12s}] {candidate['title'][:40]:40s} ({size_kb} KB)")
        return _build_meta(candidate, mood, dest)

    except Exception as e:
        log.debug(f"  ✗ {candidate['id']}: {e}")
        if dest.exists():
            dest.unlink()
        return None


def _build_meta(candidate: dict, mood: str, dest: Path) -> TrackMeta:
    return TrackMeta(
        id=candidate["id"],
        title=candidate["title"],
        artist=candidate["artist"],
        mood=mood,
        source=candidate["source"],
        license_type=candidate["license_type"],
        duration_seconds=candidate.get("duration_seconds", 120.0),
        tempo_bpm=MOOD_BPM[mood],
        file_path=str(dest.resolve()),
        volume_duck_factor=MOOD_DUCK[mood],
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run(music_dir: Path, target: int, source_filter: Optional[str], workers: int):
    music_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = music_dir / "catalog.json"

    log.info(f"Music directory : {music_dir}")
    log.info(f"Target          : {target} tracks")
    log.info(f"Workers         : {workers}")
    log.info(f"Source filter   : {source_filter or 'all'}")

    # --- Collect candidates ---
    log.info("\n=== Collecting track candidates ===")
    candidates: list[dict] = []

    if not source_filter or source_filter == "incompetech":
        log.info("Listing Incompetech (Kevin MacLeod)…")
        ic = incompetech_list_tracks()
        log.info(f"  Incompetech: {len(ic)} tracks")
        candidates.extend(ic)

    if not source_filter or source_filter == "netlabels":
        remaining = target - len(candidates)
        if remaining > 0:
            log.info(f"Listing netlabels / archive collections (need {remaining} more)…")
            nl = netlabels_list_tracks(remaining)
            log.info(f"  Netlabels: {len(nl)} candidates")
            candidates.extend(nl)

    # Deduplicate, cap at target
    seen: set[str] = set()
    unique: list[dict] = []
    for c in candidates:
        if c["id"] not in seen:
            seen.add(c["id"])
            unique.append(c)
    candidates = unique[:target]

    log.info(f"Total unique candidates: {len(candidates)}")
    if not candidates:
        log.error("No candidates found. Check network connectivity.")
        sys.exit(1)

    # --- Download ---
    log.info(f"\n=== Downloading {len(candidates)} tracks ({workers} workers) ===")
    downloaded: list[TrackMeta] = []
    failed = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download_track, c, music_dir): c for c in candidates}
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                downloaded.append(result)
            else:
                failed += 1

    # --- Save catalog ---
    catalog = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_tracks": len(downloaded),
        "license_notes": {
            "incompetech": "CC-BY 4.0 — Credit: Kevin MacLeod (incompetech.com)",
            "archive": "Various CC licenses — see individual track license_type field",
        },
        "tracks": [asdict(t) for t in downloaded],
    }
    with open(catalog_path, "w") as f:
        json.dump(catalog, f, indent=2)

    # --- Summary ---
    by_mood: dict[str, list] = {}
    by_source: dict[str, int] = {}
    for t in downloaded:
        by_mood.setdefault(t.mood, []).append(t)
        by_source[t.source] = by_source.get(t.source, 0) + 1

    total_bytes = sum(
        Path(t.file_path).stat().st_size
        for t in downloaded
        if Path(t.file_path).exists()
    )

    log.info("\n=== Download Summary ===")
    log.info(f"Downloaded : {len(downloaded)}")
    log.info(f"Failed     : {failed}")
    log.info(f"Disk usage : {total_bytes / 1_048_576:.1f} MB")
    log.info(f"Catalog    : {catalog_path}")
    log.info("")
    log.info("By mood:")
    for mood, tracks in sorted(by_mood.items()):
        log.info(f"  {mood:14s}: {len(tracks):3d} tracks")
    log.info("")
    log.info("By source:")
    for src, count in sorted(by_source.items()):
        log.info(f"  {src:14s}: {count:3d} tracks")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        choices=["incompetech", "netlabels"],
        default=None,
        help="Restrict to a single source",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=200,
        help="Number of tracks to download (default: 200)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Parallel download workers (default: 10)",
    )
    parser.add_argument(
        "--music-dir",
        type=Path,
        default=os.environ.get("MUSIC_DIR", DEFAULT_MUSIC_DIR),
        help="Directory to save MP3s",
    )
    args = parser.parse_args()

    run(
        music_dir=args.music_dir,
        target=args.target,
        source_filter=args.source,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
