#!/usr/bin/env python3
"""
OmniSVG Setup — OpenMark Icons
Installs OmniSVG and downloads model weights for RTX 5070 (16GB VRAM).

Usage:
  python setup_omnisvg.py            # full setup
  python setup_omnisvg.py --check    # check environment only
  python setup_omnisvg.py --test     # test existing install
  python setup_omnisvg.py --4b       # download 4B model instead of 8B
"""

import sys
import subprocess
from pathlib import Path

from pipeline.config import (
    ROOT,
    OMNISVG_DIR,
    MODEL_8B,
    MODEL_4B,
    OMNISVG_TMP,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print(f"  > {' '.join(cmd)}")
    return subprocess.run(cmd, **kwargs)


def pip(*packages: str):
    run(
        [sys.executable, "-m", "pip", "install", "--upgrade", *packages],
        check=True,
    )


def header(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ── Steps ─────────────────────────────────────────────────────────────────────

def check_python():
    header("Checking Python")
    v = sys.version_info
    print(f"  Python {v.major}.{v.minor}.{v.micro}")
    if v.major != 3 or v.minor < 10:
        print("  ERROR: Python 3.10+ required.")
        sys.exit(1)
    print("  ✓ Python OK")


def check_cuda() -> bool:
    header("Checking CUDA")
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"  ✓ {name} — {vram:.1f} GB VRAM")
            return True
        print("  ✗ CUDA not available")
        return False
    except ImportError:
        print("  PyTorch not installed yet")
        return False


def install_torch():
    header("Installing PyTorch (CUDA 12.8 — RTX 5070)")
    print("  Note: RTX 5070 requires CUDA 12.8+ and PyTorch 2.7+")
    run([
        sys.executable, "-m", "pip", "install",
        "torch", "torchvision", "torchaudio",
        "--index-url", "https://download.pytorch.org/whl/cu128",
    ], check=True)


def install_dependencies():
    header("Installing OmniSVG dependencies")
    pip("transformers>=4.47.0", "accelerate", "huggingface_hub")
    pip("Pillow", "einops", "sentencepiece", "tiktoken", "scipy", "numpy")
    try:
        pip("cairosvg")
        print("  ✓ CairoSVG installed")
    except subprocess.CalledProcessError:
        print("  ⚠ CairoSVG failed — install Cairo from:")
        print("    https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer")
        print("  Generation will still work without it.")


def clone_repo():
    header("Cloning OmniSVG repository")
    if OMNISVG_DIR.exists():
        print(f"  Already cloned at {OMNISVG_DIR}")
        return
    run(
        ["git", "clone", "https://github.com/OmniSVG/OmniSVG.git", str(OMNISVG_DIR)],
        check=True,
    )
    print("  ✓ Cloned")


def download_model(size: str = "8B"):
    model_dir = MODEL_8B if size == "8B" else MODEL_4B
    repo_id   = f"OmniSVG/OmniSVG1.1_{size}"
    gb        = "17" if size == "8B" else "8"

    header(f"Downloading OmniSVG1.1_{size} (~{gb} GB)")

    if model_dir.exists() and any(model_dir.iterdir()):
        print(f"  Already downloaded at {model_dir}")
        return

    print("  This may take a while. Interrupted downloads resume automatically.")
    run([
        "hf", "download",
        repo_id,
        "--local-dir", str(model_dir),
    ], check=True)

    print(f"  ✓ Model saved to {model_dir}")


def test_inference(size: str = "8B"):
    header("Testing inference")

    model_path = MODEL_8B if size == "8B" else MODEL_4B
    if not OMNISVG_DIR.exists() or not model_path.exists():
        print("  ERROR: OmniSVG or model not found. Run full setup first.")
        return False

    OMNISVG_TMP.mkdir(exist_ok=True)
    prompt_file = OMNISVG_TMP / "_test_prompt.txt"
    prompt_file.write_text(
        "Simple SVG icon of a conical flask, minimal, stroke only, 24x24",
        encoding="utf-8",
    )

    result = run([
        sys.executable, str(OMNISVG_DIR / "inference.py"),
        "--task",           "text-to-svg",
        "--input",          str(prompt_file),
        "--output",         str(OMNISVG_TMP),
        "--model-path",     str(model_path),
        "--model-size",     size,
        "--num-candidates", "1",
    ], cwd=str(OMNISVG_DIR))

    svgs = list(OMNISVG_TMP.glob("*.svg"))
    if svgs:
        print(f"\n  ✓ Success — {len(svgs)} SVG generated")
        print(f"  Preview:\n{svgs[0].read_text()[:200]}...")
        return True

    print("  ✗ No SVG output. Check errors above.")
    return False


def print_next_steps():
    print("""
╔══════════════════════════════════════════════════════════════╗
║  OmniSVG ready. Start generating:                           ║
║                                                              ║
║  python queue_manager.py starter                            ║
║  python generate.py --backend omnisvg                       ║
╚══════════════════════════════════════════════════════════════╝
""")


# ── Entrypoint ────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    size = "4B" if "--4b" in args else "8B"

    if "--check" in args:
        check_python()
        check_cuda()
        return

    if "--test" in args:
        test_inference(size)
        return

    # Full setup
    check_python()

    if not check_cuda():
        install_torch()
        check_cuda()

    install_dependencies()
    clone_repo()

    if "--skip-download" not in args:
        download_model(size)

    if "--skip-test" not in args:
        test_inference(size)

    print_next_steps()


if __name__ == "__main__":
    main()