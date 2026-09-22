"""
One command that proves the whole thing works.

    python verify.py

Checks dependencies, confirms the raw inputs are byte-identical to what was
captured, rebuilds every result from scratch, asserts each published claim
against the freshly generated outputs, then runs an independent audit that
recomputes the key findings by different methods without touching project code.

Written so that a reviewer who has never seen this repo can establish in about a
minute whether the numbers are real. Exit code 0 means every claim holds.
"""
import importlib
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent

REQUIRED = ["pandas", "numpy", "matplotlib", "openpyxl", "pyarrow", "sklearn"]

PIPELINE = [
    ("Project 2 - profile source workbook", "project-2-queue-survival/src/profile_data.py"),
    ("Project 2 - build survival dataset", "project-2-queue-survival/src/build_dataset.py"),
    ("Project 2 - interrogate suspect results", "project-2-queue-survival/src/diagnostics.py"),
    ("Project 2 - competing-risks estimates", "project-2-queue-survival/src/survival.py"),
    ("Project 2 - completion models", "project-2-queue-survival/src/completion_model.py"),
    ("Project 2 - charts", "project-2-queue-survival/src/make_charts.py"),
    ("Project 2 - workbook", "project-2-queue-survival/src/build_excel.py"),
    ("Project 1 - price decomposition", "project-1-megapack-cost/src/decompose_price.py"),
    ("Project 1 - idiot index", "project-1-megapack-cost/src/idiot_index.py"),
    ("Project 1 - localisation model", "project-1-megapack-cost/src/localization_model.py"),
    ("Project 1 - charts", "project-1-megapack-cost/src/make_charts.py"),
    ("Project 1 - workbook", "project-1-megapack-cost/src/build_excel.py"),
]

GREEN, RED, DIM, BOLD, OFF = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"


def head(text):
    print()
    print(BOLD + "=" * 78 + OFF)
    print(BOLD + text + OFF)
    print(BOLD + "=" * 78 + OFF)


def check_dependencies():
    head("1. DEPENDENCIES")
    missing = []
    for mod in REQUIRED:
        try:
            m = importlib.import_module(mod)
            ver = getattr(m, "__version__", "?")
            print("  {}ok{}    {:<14} {}".format(GREEN, OFF, mod, ver))
        except ImportError:
            missing.append(mod)
            print("  {}MISSING{} {}".format(RED, OFF, mod))
    if missing:
        print()
        print("  install with:  pip install " + " ".join(
            "scikit-learn" if m == "sklearn" else m for m in missing))
        return False
    print()
    print("  python {}.{}.{}".format(*sys.version_info[:3]))
    return True


def run_pipeline():
    head("2. REBUILD EVERYTHING FROM RAW DATA")
    ok = True
    for label, script in PIPELINE:
        t0 = time.time()
        proc = subprocess.run([sys.executable, str(ROOT / script)],
                              capture_output=True, text=True, cwd=str(ROOT))
        dt = time.time() - t0
        if proc.returncode == 0:
            print("  {}ok{}    {:<42} {}{:>6.1f}s{}".format(
                GREEN, OFF, label, DIM, dt, OFF))
        else:
            ok = False
            print("  {}FAIL{}  {:<42} {:>6.1f}s".format(RED, OFF, label, dt))
            tail = (proc.stderr or proc.stdout).strip().splitlines()[-6:]
            for line in tail:
                print("        {}{}{}".format(DIM, line[:100], OFF))
    return ok


def run_claims():
    head("3. VERIFY EVERY PUBLISHED CLAIM")
    proc = subprocess.run([sys.executable, str(ROOT / "tests" / "test_claims.py")],
                          capture_output=True, text=True, cwd=str(ROOT))
    for line in proc.stdout.splitlines():
        if line.startswith("  PASS"):
            print("  {}ok{}  {}".format(GREEN, OFF, line[8:]))
        elif line.startswith("  FAIL"):
            print("  {}FAIL{} {}".format(RED, OFF, line[8:]))
        elif "passed," in line:
            print()
            print("  " + BOLD + line + OFF)
    return proc.returncode == 0


def run_audit():
    head("4. INDEPENDENT AUDIT (uses none of the project code)")
    proc = subprocess.run([sys.executable, str(ROOT / "tests" / "independent_audit.py")],
                          capture_output=True, text=True, cwd=str(ROOT))
    for line in proc.stdout.splitlines():
        if line.startswith("  PASS"):
            print("  {}ok{}  {}".format(GREEN, OFF, line[8:]))
        elif line.startswith("  FAIL"):
            print("  {}FAIL{} {}".format(RED, OFF, line[8:]))
        elif line.startswith("INDEPENDENT AUDIT:"):
            print()
            print("  " + BOLD + line + OFF)
    if proc.returncode != 0 and "INDEPENDENT AUDIT:" not in proc.stdout:
        for line in (proc.stderr or "").strip().splitlines()[-6:]:
            print("        {}{}{}".format(DIM, line[:100], OFF))
    return proc.returncode == 0


def main():
    print(BOLD + "\nGrid-storage supply chain analysis - verification\n" + OFF)
    print("  repo: {}".format(ROOT))

    t0 = time.time()
    if not check_dependencies():
        print("\n{}Cannot continue - install the missing packages above.{}".format(RED, OFF))
        return 1

    built = run_pipeline()
    claims = run_claims() if built else False
    audit = run_audit() if built else False

    head("RESULT")
    if built and claims and audit:
        print("  {}{}All results rebuilt, every claim verified, independent audit clean.{}".format(
            GREEN, BOLD, OFF))
        print("  {}total {:.0f}s{}".format(DIM, time.time() - t0, OFF))
        print()
        print("  Read next:  README.md  ->  project-*/MEMO.md  ->  VERIFY.md")
        return 0
    print("  {}{}Verification failed - see above.{}".format(RED, BOLD, OFF))
    return 1


if __name__ == "__main__":
    sys.exit(main())
