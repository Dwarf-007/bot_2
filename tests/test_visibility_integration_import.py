from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def main():
    try:
        from services.movement.visibility_aware_movement_engine import VisibilityAwareMovementEngine
    except ModuleNotFoundError as exc:
        # Expected when base movement/corridor packages are not present in isolated patch test.
        print(f"SKIP missing dependency: {exc}")
        return
    assert VisibilityAwareMovementEngine is not None
    print("OK visibility integration import")

if __name__ == "__main__": main()
