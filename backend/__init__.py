import sys
from pathlib import Path

# Ensure the backend directory is in sys.path so 'import app...' works regardless of cwd
_backend_dir = str(Path(__file__).resolve().parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
