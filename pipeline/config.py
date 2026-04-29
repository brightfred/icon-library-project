# pipeline/config.py
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT        = Path(__file__).parent.parent
SRC         = ROOT / "src"
DOCS        = ROOT / "docs"
QUEUE_FILE  = ROOT / "queue.json"
REJECTED    = ROOT / "rejected.json"
STYLE_GUIDE = ROOT / "style-guide.md"
CATALOG     = ROOT / "CATALOG.md"
LOG_FILE    = ROOT / "generate.log"
REVIEW_TMPL = ROOT / "review_template.html"
REVIEW_OUT  = ROOT / "review.html"
OMNISVG_DIR = ROOT / "OmniSVG"
MODEL_8B    = ROOT / "OmniSVG1.1_8B"
MODEL_4B    = ROOT / "OmniSVG1.1_4B"
OMNISVG_TMP = ROOT / "_omnisvg_output"

# Qwen base models — 4B OmniSVG needs 3B Qwen, 8B OmniSVG needs 7B Qwen
QWEN_MODEL_3B = ROOT / "Qwen2.5-VL-3B-Instruct"
QWEN_MODEL_7B = ROOT / "Qwen2.5-VL-7B-Instruct"
QWEN_MODEL    = QWEN_MODEL_7B  # legacy alias

# ── Generation ────────────────────────────────────────────────────────────────

DEFAULT_BACKEND     = "ollama"
NUM_CANDIDATES      = 3
SLEEP_BETWEEN_ICONS = 2  # seconds

# ── Ollama ────────────────────────────────────────────────────────────────────

OLLAMA_MODEL       = "qwen2.5-coder:7b"
OLLAMA_URL         = "http://localhost:11434/api/generate"
OLLAMA_TEMPERATURE = 0.7
OLLAMA_MAX_TOKENS  = 800
OLLAMA_TIMEOUT     = 60  # seconds

# ── OmniSVG ───────────────────────────────────────────────────────────────────

OMNISVG_DEFAULT_SIZE    = "4B"
OMNISVG_TIMEOUT         = 300  # seconds
OMNISVG_PROMPT_TEMPLATE = (
    "Minimal stroke SVG icon of {concept}, "
    "24x24 viewBox, single color, clean paths, stroke only"
)

# ── Style guide rules ─────────────────────────────────────────────────────────

# Categories that use stroke-width 1.5 (complex/detailed)
COMPLEX_CATEGORIES = {"science", "aquaculture", "engineering", "environment"}

# Categories that use stroke-width 2 (simple/UI)
SIMPLE_CATEGORIES  = {"action", "nav", "ui", "status", "social",
                      "comm", "file", "device", "commerce", "media"}

REQUIRED_VIEWBOX = '0 0 24 24'
REQUIRED_FILL    = "none"
REQUIRED_STROKE  = "currentColor"
MIN_SVG_LENGTH   = 50
MAX_PATHS_IDEAL  = 8
MIN_PATHS_IDEAL  = 2

# ── Git ───────────────────────────────────────────────────────────────────────

GIT_COMMIT_PREFIX = "add"
GIT_COMMIT_SUFFIX = "icon [auto]"
AUTO_PUSH         = True