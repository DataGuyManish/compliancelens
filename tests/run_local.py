"""Zero-dependency test runner for environments without pytest.
GitHub Actions uses pytest; this simply executes every test_* function.
"""
import importlib
import os
import sys
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

MODULES = ["test_validators", "test_checks", "test_drift",
           "test_detector", "test_masking", "test_policy", "test_scoring"]


def main() -> int:
    passed = failed = 0
    failures = []
    for name in MODULES:
        mod = importlib.import_module(name)
        for attr in dir(mod):
            if attr.startswith("test_") and callable(getattr(mod, attr)):
                try:
                    getattr(mod, attr)()
                    passed += 1
                    print(f"PASS {name}::{attr}")
                except TypeError:      # pytest-style fixtures: skip locally
                    print(f"SKIP {name}::{attr} (needs pytest)")
                except Exception:
                    failed += 1
                    failures.append(f"{name}::{attr}\n{traceback.format_exc()}")
                    print(f"FAIL {name}::{attr}")
    print(f"\n{passed} passed, {failed} failed")
    for f in failures:
        print(f)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
