import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import init_db  # noqa: E402
from app.seed import seed  # noqa: E402

if __name__ == "__main__":
    init_db()
    seed()
