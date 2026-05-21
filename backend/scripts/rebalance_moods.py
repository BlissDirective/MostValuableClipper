"""
Rebalance mood distribution across the music catalog.

Kevin MacLeod track names don't contain mood keywords, so after initial download
most tracks default to "upbeat". This script uses an extended keyword dictionary
and cyclically assigns moods to tracks without a strong keyword match, targeting
a balanced distribution across all 5 moods.

Usage:
    python3 scripts/rebalance_moods.py [--catalog path/to/catalog.json]
"""

import argparse
import json
import os
import shutil
from pathlib import Path

DEFAULT_CATALOG = Path(__file__).parent.parent / "app" / "music" / "catalog.json"

# Extended keyword patterns for mood inference
MOOD_KEYWORDS: dict[str, list[str]] = {
    "high_energy": [
        "rock", "metal", "power", "action", "fight", "battle", "intense", "hard",
        "aggressive", "driving", "energetic", "adrenaline", "dungeon", "boss",
        "aces", "blipstream", "bit quest", "bit shift", "chiptune", "bloop",
        "acid", "industrial", "thrash", "gun", "warrior", "chase", "rush",
        "electro", "dance", "funk", "groove", "bass", "impact", "surge",
        "hypno", "frenzy", "blip", "overdrive", "turbo", "rally", "manic",
    ],
    "upbeat": [
        "happy", "fun", "bright", "cheerful", "playful", "comedy", "light",
        "bounce", "skip", "whimsy", "cute", "quirky", "jingle", "pop", "ska",
        "summer", "carefree", "jazz", "swing", "beach", "party", "fiesta",
        "lounge", "bossa", "latin", "merengue", "celebration", "festive",
        "groove", "walk", "travel", "adventure", "meme", "silly", "goofy",
        "tropical", "sunrise", "morning", "fresh", "lively", "peppy", "sprightly",
    ],
    "calm": [
        "ambient", "chill", "relax", "lofi", "lo-fi", "peaceful", "soft", "gentle",
        "meditation", "sleep", "nature", "rain", "drift", "float", "lullaby",
        "quiet", "tranquil", "serene", "breeze", "cloud", "mist", "fog",
        "prelude", "serenity", "pastoral", "twilight", "dusk", "night",
        "acoustic guitar", "breathe", "slow", "tender", "soothe", "ease",
        "space", "cosmos", "galaxy", "ethereal", "drone", "pad", "atmospheric",
        "airport", "lounge", "haze", "vapour", "airy", "fluid", "shimmer",
    ],
    "emotional": [
        "sad", "melancholy", "emotional", "piano", "acoustic", "longing",
        "nostalgic", "tender", "heartfelt", "bittersweet", "reflective",
        "sorrow", "touching", "string", "violin", "cello", "choir", "hymn",
        "grace", "prayer", "sacred", "requiem", "elegy", "lament", "tears",
        "memory", "remember", "dream", "hope", "loss", "farewell", "goodbye",
        "miss", "alone", "empty", "hollow", "wistful", "yearning", "lonesome",
    ],
    "dramatic": [
        "cinematic", "dramatic", "tension", "suspense", "thriller", "horror",
        "ominous", "mystery", "dark", "foreboding", "epic", "orchestral",
        "score", "trailer", "build", "rising", "climax", "confrontation",
        "villain", "danger", "threat", "shadow", "lurk", "stalk", "menace",
        "arcane", "ancient", "relic", "artifact", "curse", "doom", "fate",
        "heavy", "weight", "burden", "conflict", "war", "siege", "march",
        "apprehension", "anxiety", "dread", "unease", "creep",
    ],
}

# Target distribution (percentages)
MOOD_TARGETS = {
    "high_energy": 0.20,   # 20%
    "upbeat":      0.25,   # 25%
    "calm":        0.20,   # 20%
    "emotional":   0.18,   # 18%
    "dramatic":    0.17,   # 17%
}

MOOD_ORDER = list(MOOD_TARGETS.keys())


def infer_mood_score(name: str) -> dict[str, int]:
    """Return mood scores based on keyword matches in the track name."""
    combined = name.lower()
    scores: dict[str, int] = {m: 0 for m in MOOD_KEYWORDS}
    for mood, keywords in MOOD_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                scores[mood] += 1
    return scores


def rebalance(catalog_path: Path):
    catalog = json.loads(catalog_path.read_text())
    tracks = catalog["tracks"]
    total = len(tracks)
    print(f"Loaded {total} tracks from {catalog_path}")

    # Count target per mood
    targets = {m: max(1, int(total * pct)) for m, pct in MOOD_TARGETS.items()}
    # Fix rounding so targets sum to total
    deficit = total - sum(targets.values())
    for m in MOOD_ORDER:
        if deficit == 0:
            break
        targets[m] += 1
        deficit -= 1

    print(f"Target distribution: {targets}")

    # Score every track
    strong: dict[str, list] = {m: [] for m in MOOD_ORDER}
    weak: list = []

    for t in tracks:
        scores = infer_mood_score(t["title"])
        best_mood = max(scores, key=lambda m: scores[m])
        best_score = scores[best_mood]
        if best_score > 0:
            strong[best_mood].append((t, best_score))
        else:
            weak.append(t)

    # Sort strong lists by score descending
    for m in MOOD_ORDER:
        strong[m].sort(key=lambda x: x[1], reverse=True)

    # Assign tracks greedily: fill up each mood to its target
    assigned: dict[str, list] = {m: [] for m in MOOD_ORDER}
    unassigned: list = list(weak)  # tracks with no keyword match

    for m in MOOD_ORDER:
        for t, _ in strong[m]:
            if len(assigned[m]) < targets[m]:
                assigned[m].append(t)
            else:
                unassigned.append(t)

    # Distribute unassigned tracks cyclically
    mood_cycle = [m for m in MOOD_ORDER for _ in range(targets[m] - len(assigned[m]))]
    for i, t in enumerate(unassigned):
        if i < len(mood_cycle):
            assigned[mood_cycle[i]].append(t)
        else:
            # overflow goes to upbeat
            assigned["upbeat"].append(t)

    # Apply new moods and move files
    new_tracks = []
    for mood, track_list in assigned.items():
        for t in track_list:
            old_path = Path(t["file_path"])
            new_dir = old_path.parent.parent / mood
            new_dir.mkdir(parents=True, exist_ok=True)
            new_path = new_dir / old_path.name

            if old_path != new_path and old_path.exists():
                shutil.move(str(old_path), str(new_path))

            t["mood"] = mood
            t["file_path"] = str(new_path.resolve())
            new_tracks.append(t)

    # Save updated catalog
    catalog["tracks"] = new_tracks
    catalog_path.write_text(json.dumps(catalog, indent=2))

    print("\nNew distribution:")
    for mood in MOOD_ORDER:
        count = sum(1 for t in new_tracks if t["mood"] == mood)
        print(f"  {mood:14s}: {count:3d} tracks  (target: {targets[mood]})")

    print(f"\nCatalog updated: {catalog_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()
    rebalance(args.catalog)


if __name__ == "__main__":
    main()
