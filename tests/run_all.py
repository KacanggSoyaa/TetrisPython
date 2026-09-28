# Run every test in this folder. Headless, no repository files are modified.
#
#     python tests/run_all.py
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Order matters only for readability: fast smoke first, layout audit last.
TESTS = ["test_smoke.py", "test_regress.py", "test_pixels.py", "test_layout.py"]


# Run every test file in a subprocess and report an overall result.
#
# Subprocesses isolate the module-level Pygame state between files, so one
# test cannot leave a dirty screen or keybinds behind for the next.
def main():
    failed = []
    for name in TESTS:
        print("=" * 62, flush=True)
        print(name, flush=True)
        print("=" * 62, flush=True)
        result = subprocess.run([sys.executable, os.path.join(HERE, name)],
                                cwd=os.path.dirname(HERE))
        if result.returncode != 0:
            failed.append(name)
    print("=" * 62, flush=True)
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print(f"ALL {len(TESTS)} TEST FILES PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
