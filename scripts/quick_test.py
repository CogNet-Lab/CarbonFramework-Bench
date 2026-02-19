#!/usr/bin/env python3
"""
Quick test runner for a single framework
Usage: python quick_test.py <framework> [load]
"""

import sys
import subprocess

FRAMEWORKS = {
    "fastapi": 8000,
    "django": 8001,
    "springboot": 8002,
    "spring": 8002,  # alias
    "micronaut": 8003,
    "gin": 8004,
    "chi": 8005,
}

def print_usage():
    print("\n Quick Test Runner")
    print("="*60)
    print("\nUsage: python quick_test.py <framework> [load] [endpoint] [runs] [--min-duration N]")
    print("       python quick_test.py --startup [framework]")
    print("\nFrameworks:", ", ".join(sorted(set(FRAMEWORKS.keys()))))
    print("Loads:      100, 1000, 10000 (default: 100)")
    print("Endpoints:  light, medium, heavy (default: light)")
    print("Runs:       number of independent repetitions (default: 1)")
    print("\nOptions:")
    print("  --min-duration N  Pad short tests to N seconds for reliable energy measurement")
    print("  --startup [fw]    Measure container cold-start times (restarts containers)")
    print("\nExamples:")
    print("  python quick_test.py fastapi")
    print("  python quick_test.py django 1000")
    print("  python quick_test.py gin 10000 heavy")
    print("  python quick_test.py fastapi 100 light 5    # 5 independent runs")
    print("  python quick_test.py fastapi 100 light 1 --min-duration 15")
    print("  python quick_test.py --startup              # all frameworks")
    print("  python quick_test.py --startup fastapi      # single framework")
    print()

def main():
    # Handle --startup before positional arg parsing
    if len(sys.argv) >= 2 and sys.argv[1] == "--startup":
        fw_arg = sys.argv[2] if len(sys.argv) > 2 else None
        cmd = ["python", "test_carbon_comprehensive.py", "--measure-startup"]
        if fw_arg:
            cmd.extend(["-f", fw_arg.lower()])
        subprocess.run(cmd)
        return

    # Extract --min-duration before positional arg parsing
    min_duration = None
    argv = list(sys.argv[1:])
    if "--min-duration" in argv:
        idx = argv.index("--min-duration")
        if idx + 1 < len(argv):
            min_duration = argv[idx + 1]
            argv = argv[:idx] + argv[idx + 2:]
        else:
            print("\n  --min-duration requires a value")
            sys.exit(1)

    if len(argv) < 1:
        print_usage()
        sys.exit(1)

    framework = argv[0].lower()
    load = argv[1] if len(argv) > 1 else "100"
    endpoint = argv[2] if len(argv) > 2 else "light"
    runs = argv[3] if len(argv) > 3 else "1"

    if framework not in FRAMEWORKS:
        print(f"\n  Unknown framework: {framework}")
        print_usage()
        sys.exit(1)

    if load not in ["100", "1000", "10000"]:
        print(f"\n  Invalid load: {load}")
        print("   Must be: 100, 1000, or 10000")
        sys.exit(1)

    if endpoint not in ["light", "medium", "heavy"]:
        print(f"\n  Invalid endpoint: {endpoint}")
        print("   Must be: light, medium, or heavy")
        sys.exit(1)

    if not runs.isdigit() or int(runs) < 1:
        print(f"\n  Invalid runs: {runs}")
        print("   Must be a positive integer")
        sys.exit(1)

    print(f"\n  Running test:")
    print(f"   Framework: {framework}")
    print(f"   Load: {load} requests")
    print(f"   Endpoint: {endpoint}")
    print(f"   Runs: {runs}")
    if min_duration:
        print(f"   Min Duration: {min_duration}s")
    print()

    cmd = [
        "python",
        "test_carbon_comprehensive.py",
        "-f", framework,
        "-l", load,
        "-e", endpoint,
        "-r", runs,
    ]

    if min_duration:
        cmd.extend(["--min-duration", min_duration])

    subprocess.run(cmd)

if __name__ == "__main__":
    main()
