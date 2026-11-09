"""Launch with the existing pygame gint simulator from the parent folder."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root.parent))
sys.path.insert(0, str(root))
import main
