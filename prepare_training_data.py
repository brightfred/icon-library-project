#!/usr/bin/env python3
"""
OpenMark Icons — Training Data Preparation
Downloads SVG icons from MIT-licensed open source libraries and formats
them as prompt/completion pairs for LLM fine-tuning.

Usage:
  python prepare_training_data.py              # download all libraries
  python prepare_training_data.py --lucide     # lucide only
  python prepare_training_data.py --tabler     # tabler only
  python prepare_training_data.py --phosphor   # phosphor only
  python prepare_training_data.py --heroicons  # heroicons only
  python prepare_training_data.py --local      # include your own src/ icons
  python prepare_training_data.py --stats      # show dataset stats only

Output:
  training_data/
    raw/             # downloaded SVG files
    training.jsonl   # prompt/completion pairs for fine-tuning
    validation.jsonl
    stats.json
"""

import json
import re
import sys
import time
import random
import argparse
import urllib.request
import urllib.error
import zipfile
import io
from pathlib import Path
from datetime import datetime


# ── Config ────────────────────────────────────────────────────────────────────

ROOT         = Path(__file__).parent
SRC          = ROOT / "src"
TRAINING_DIR = ROOT / "training_data"
RAW_DIR      = TRAINING_DIR / "raw"
OUTPUT_JSONL = TRAINING_DIR / "training.jsonl"
VALID_JSONL  = TRAINING_DIR / "validation.jsonl"
STATS_FILE   = TRAINING_DIR / "stats.json"

VALIDATION_SPLIT = 0.1
RANDOM_SEED      = 42

# ── Library definitions ───────────────────────────────────────────────────────

LIBRARIES = {
    # Stroke-only libraries — match our style guide exactly
    "lucide": {
        "url":    "https://github.com/lucide-icons/lucide/archive/refs/heads/main.zip",
        "subdir": "lucide-main/icons",
        "style":  "stroke",
    },
    "tabler": {
        "url":    "https://github.com/tabler/tabler-icons/archive/refs/heads/main.zip",
        "subdir": "tabler-icons-main/icons/outline",
        "style":  "stroke",
    },
    "heroicons": {
        "url":    "https://github.com/tailwindlabs/heroicons/archive/refs/heads/master.zip",
        "subdir": "heroicons-master/src/24/outline",
        "style":  "stroke",
    },
    # Filled libraries — different style, labeled accordingly
    "phosphor": {
        "url":    "https://github.com/phosphor-icons/core/archive/refs/heads/main.zip",
        "subdir": "core-main/assets/regular",
        "style":  "fill",
    },
}

# Prompt templates for stroke-only icons
STROKE_PROMPTS = [
    "SVG icon of {concept}, stroke-only, 24x24 viewBox, currentColor",
    "Create a minimal SVG icon for {concept}. Stroke-based, viewBox 0 0 24 24.",
    "Draw an SVG icon: {concept}. Use stroke not fill, 24x24 grid.",
    "Icon for {concept} as SVG. Stroke-only style, single color, 24px grid.",
    "Generate a clean SVG icon of {concept} for a UI library.",
    "{concept} icon in SVG format, minimal stroke style, 24x24.",
    "Minimal SVG icon: {concept}. Stroke-based, currentColor, viewBox 0 0 24 24.",
    "Create a {concept} icon. SVG, stroke-only, no fills, 24x24 viewBox.",
    "Design a {concept} icon. Stroke style, round linecaps, 24x24.",
    "SVG stroke icon of {concept}. Clean paths, currentColor, 24px grid.",
]

# Prompt templates for filled icons
FILL_PROMPTS = [
    "SVG icon of {concept}, filled style, currentColor",
    "Create a filled SVG icon for {concept}. Fill-based, currentColor.",
    "Draw a filled SVG icon: {concept}. Use fill not stroke.",
    "Icon for {concept} as filled SVG. Single color, fill style.",
    "Generate a filled SVG icon of {concept}.",
    "{concept} icon in filled SVG format.",
    "Filled SVG icon: {concept}. currentColor, no strokes.",
    "Create a {concept} filled icon in SVG format.",
]


# ── SVG Validators ────────────────────────────────────────────────────────────

class StrokeSVGValidator:
    """Validates stroke-only SVG icons."""

    MAX_SIZE = 8000
    MIN_SIZE = 100

    def is_valid(self, svg: str) -> tuple[bool, str]:
        if len(svg) < self.MIN_SIZE:
            return False, "too short"
        if len(svg) > self.MAX_SIZE:
            return False, "too complex"
        if "<svg" not in svg:
            return False, "no svg tag"
        if 'viewBox="0 0 24 24"' not in svg:
            return False, "wrong viewBox"
        if "currentColor" not in svg:
            return False, "no currentColor"
        if 'fill="none"' not in svg:
            return False, "not stroke-only"
        hardcoded = re.findall(
            r'(?:fill|stroke|color)="(?!none|currentColor)[^"]*"', svg
        )
        if hardcoded:
            return False, f"hardcoded color"
        return True, "ok"

    def clean(self, svg: str) -> str:
        svg = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()
        svg = re.sub(r"\s+", " ", svg)
        svg = re.sub(r">\s+<", "><", svg)
        return svg.strip()


class FilledSVGValidator:
    """Validates filled SVG icons (Phosphor style)."""

    MAX_SIZE = 8000
    MIN_SIZE = 100

    def is_valid(self, svg: str) -> tuple[bool, str]:
        if len(svg) < self.MIN_SIZE:
            return False, "too short"
        if len(svg) > self.MAX_SIZE:
            return False, "too complex"
        if "<svg" not in svg:
            return False, "no svg tag"
        if "currentColor" not in svg:
            return False, "no currentColor"
        # Must have fill (not stroke-only)
        if 'fill="none"' in svg and 'stroke="currentColor"' not in svg:
            return False, "no fill"
        return True, "ok"

    def clean(self, svg: str) -> str:
        svg = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()
        svg = re.sub(r"\s+", " ", svg)
        svg = re.sub(r">\s+<", "><", svg)
        return svg.strip()


# ── Name helpers ──────────────────────────────────────────────────────────────

def filename_to_concept(filename: str) -> str:
    name = Path(filename).stem
    for suffix in ["-outline", "-fill", "-regular", "-bold", "-thin", "-light"]:
        name = name.replace(suffix, "")
    return name.replace("-", " ").replace("_", " ").strip()


def concept_to_category(concept: str) -> str:
    concept_lower = concept.lower()
    mapping = {
        "science":     ["atom", "flask", "microscope", "dna", "molecule", "cell",
                        "magnet", "beaker", "pipette", "lab", "science", "chemical",
                        "test tube", "petri", "telescope", "prism"],
        "engineering": ["gear", "wrench", "circuit", "valve", "pump", "motor",
                        "drill", "bolt", "nut", "tool", "engine", "pipe", "piston",
                        "turbine", "compressor", "sensor", "caliper"],
        "environment": ["leaf", "tree", "wave", "sun", "wind", "cloud", "rain",
                        "snow", "fire", "water", "earth", "nature", "plant",
                        "flower", "mountain", "glacier", "coral"],
        "nav":         ["arrow", "chevron", "caret", "menu", "close", "back",
                        "forward", "home", "navigate", "direction"],
        "action":      ["search", "add", "edit", "delete", "save", "upload",
                        "download", "copy", "paste", "refresh", "filter", "sort",
                        "plus", "minus", "check", "cross"],
        "media":       ["play", "pause", "stop", "camera", "image", "video",
                        "music", "audio", "film", "photo", "record", "microphone"],
        "comm":        ["mail", "chat", "message", "phone", "call", "email",
                        "send", "inbox", "notification", "bell", "comment"],
        "social":      ["heart", "star", "like", "share", "user", "person",
                        "people", "group", "team", "profile", "avatar"],
        "file":        ["file", "folder", "document", "page", "paper", "doc"],
        "device":      ["phone", "mobile", "laptop", "computer", "tablet",
                        "monitor", "keyboard", "mouse", "printer"],
        "commerce":    ["cart", "shop", "store", "bag", "wallet", "credit",
                        "payment", "price", "tag", "gift"],
    }
    for category, terms in mapping.items():
        for term in terms:
            if term in concept_lower:
                return category
    return "ui"


# ── Training example builder ──────────────────────────────────────────────────

def build_example(svg: str, concept: str, source: str,
                  category: str, style: str) -> dict:
    templates = STROKE_PROMPTS if style == "stroke" else FILL_PROMPTS
    prompt    = random.choice(templates).format(concept=concept)
    return {
        "prompt":     prompt,
        "completion": svg,
        "metadata": {
            "concept":  concept,
            "category": category,
            "source":   source,
            "style":    style,
            "length":   len(svg),
        }
    }


# ── Downloader ────────────────────────────────────────────────────────────────

class LibraryDownloader:

    def __init__(self, raw_dir: Path):
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def download(self, name: str, config: dict) -> list[Path]:
        lib_dir = self.raw_dir / name
        lib_dir.mkdir(exist_ok=True)

        existing = list(lib_dir.glob("*.svg"))
        if existing:
            print(f"  {name}: already downloaded ({len(existing)} SVGs)")
            return existing

        print(f"  {name}: downloading from GitHub...")
        url = config["url"]

        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "OpenMark-Icons/1.0"}
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = resp.read()
        except urllib.error.URLError as e:
            print(f"  {name}: download failed — {e}")
            return []

        print(f"  {name}: extracting SVGs...")
        svgs    = []
        subdir  = config["subdir"]

        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                for member in zf.namelist():
                    if (subdir in member
                            and member.endswith(".svg")
                            and not member.endswith("/")):
                        filename = Path(member).name
                        content  = zf.read(member).decode("utf-8", errors="ignore")
                        dest     = lib_dir / filename
                        dest.write_text(content, encoding="utf-8")
                        svgs.append(dest)
        except zipfile.BadZipFile:
            print(f"  {name}: bad zip file")
            return []

        print(f"  {name}: extracted {len(svgs)} SVGs")
        return svgs


# ── Library processor ─────────────────────────────────────────────────────────

def process_library(name: str, svg_files: list[Path],
                    style: str) -> list[dict]:
    validator = StrokeSVGValidator() if style == "stroke" else FilledSVGValidator()
    examples  = []
    skipped   = 0

    for svg_path in svg_files:
        try:
            raw = svg_path.read_text(encoding="utf-8").strip()
        except Exception:
            continue

        ok, reason = validator.is_valid(raw)
        if not ok:
            skipped += 1
            continue

        svg     = validator.clean(raw)
        concept = filename_to_concept(svg_path.name)
        cat     = concept_to_category(concept)

        examples.append(build_example(svg, concept, name, cat, style))

    print(f"  {name}: {len(examples)} valid, {skipped} skipped")
    return examples


def process_local_src() -> list[dict]:
    """Include your own icons with 3x weight."""
    if not SRC.exists():
        return []

    validator = StrokeSVGValidator()
    examples  = []

    for svg_path in SRC.glob("*.svg"):
        try:
            raw = svg_path.read_text(encoding="utf-8").strip()
        except Exception:
            continue

        ok, _ = validator.is_valid(raw)
        if not ok:
            continue

        parts   = svg_path.stem.split("-", 1)
        cat     = parts[0]
        concept = parts[1].replace("-", " ") if len(parts) > 1 else svg_path.stem
        svg     = validator.clean(raw)

        for _ in range(3):
            examples.append(build_example(svg, concept, "openmark", cat, "stroke"))

    print(f"  local src/: {len(examples)} examples (3x weight)")
    return examples


# ── Output helpers ────────────────────────────────────────────────────────────

def write_jsonl(examples: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")


def write_stats(examples: list[dict], path: Path) -> dict:
    sources    = {}
    categories = {}
    styles     = {}
    lengths    = []

    for ex in examples:
        src  = ex["metadata"]["source"]
        cat  = ex["metadata"]["category"]
        sty  = ex["metadata"]["style"]
        sources[src]    = sources.get(src, 0) + 1
        categories[cat] = categories.get(cat, 0) + 1
        styles[sty]     = styles.get(sty, 0) + 1
        lengths.append(ex["metadata"]["length"])

    stats = {
        "total":      len(examples),
        "sources":    sources,
        "categories": categories,
        "styles":     styles,
        "svg_length": {
            "min":  min(lengths),
            "max":  max(lengths),
            "mean": int(sum(lengths) / len(lengths)),
        },
        "generated_at": datetime.now().isoformat(),
    }
    path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def print_stats(stats: dict):
    print(f"\n{'='*50}")
    print(f"  Dataset Statistics")
    print(f"{'='*50}")
    print(f"  Total examples:  {stats['total']}")
    print(f"\n  By style:")
    for sty, count in sorted(stats["styles"].items(), key=lambda x: -x[1]):
        print(f"    {sty:<20} {count:>5}")
    print(f"\n  By source:")
    for src, count in sorted(stats["sources"].items(), key=lambda x: -x[1]):
        print(f"    {src:<20} {count:>5}")
    print(f"\n  By category:")
    for cat, count in sorted(stats["categories"].items(), key=lambda x: -x[1]):
        print(f"    {cat:<20} {count:>5}")
    print(f"\n  SVG length:")
    print(f"    min:  {stats['svg_length']['min']}")
    print(f"    max:  {stats['svg_length']['max']}")
    print(f"    mean: {stats['svg_length']['mean']}")
    print(f"{'='*50}\n")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Prepare SVG fine-tuning dataset")
    parser.add_argument("--lucide",    action="store_true")
    parser.add_argument("--tabler",    action="store_true")
    parser.add_argument("--phosphor",  action="store_true")
    parser.add_argument("--heroicons", action="store_true")
    parser.add_argument("--local",     action="store_true")
    parser.add_argument("--stats",     action="store_true")
    args = parser.parse_args()

    download_all = not any([
        args.lucide, args.tabler, args.phosphor,
        args.heroicons, args.local,
    ])

    if args.stats and OUTPUT_JSONL.exists():
        data  = [json.loads(l) for l in OUTPUT_JSONL.read_text().splitlines()]
        stats = write_stats(data, STATS_FILE)
        print_stats(stats)
        return

    print("OpenMark Icons — Training Data Preparation")
    print(f"Output: {TRAINING_DIR}\n")

    random.seed(RANDOM_SEED)
    downloader   = LibraryDownloader(RAW_DIR)
    all_examples = []

    print("Downloading libraries...")
    for name, config in LIBRARIES.items():
        should = (
            download_all
            or (name == "lucide"    and args.lucide)
            or (name == "tabler"    and args.tabler)
            or (name == "phosphor"  and args.phosphor)
            or (name == "heroicons" and args.heroicons)
        )
        if not should:
            continue

        svgs     = downloader.download(name, config)
        examples = process_library(name, svgs, config["style"])
        all_examples.extend(examples)

    if args.local or download_all:
        all_examples.extend(process_local_src())

    if not all_examples:
        print("No examples generated.")
        sys.exit(1)

    # Shuffle and split
    random.shuffle(all_examples)
    split     = int(len(all_examples) * (1 - VALIDATION_SPLIT))
    train_set = all_examples[:split]
    valid_set = all_examples[split:]

    print(f"\nWriting dataset...")
    write_jsonl(train_set, OUTPUT_JSONL)
    write_jsonl(valid_set, VALID_JSONL)
    stats = write_stats(all_examples, STATS_FILE)

    print(f"  training.jsonl:   {len(train_set)} examples")
    print(f"  validation.jsonl: {len(valid_set)} examples")

    print_stats(stats)

    print("Next steps:")
    print("  1. Review training_data/training.jsonl")
    print("  2. pip install unsloth")
    print("  3. python finetune.py")


if __name__ == "__main__":
    main()