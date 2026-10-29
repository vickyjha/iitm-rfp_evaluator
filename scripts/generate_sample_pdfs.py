"""Deprecated name kept for compatibility. Use scripts/generate_samples.py."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("generate_samples.py")), run_name="__main__")
