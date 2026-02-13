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
    print("\nUsage: python quick_test.py <framework> [load] [endpoint] [runs]")
    print("\nFrameworks:", ", ".join(sorted(set(FRAMEWORKS.keys()))))
    print("Loads:      100, 1000, 10000 (default: 100)")
    print("Endpoints:  light, medium, heavy (default: light)")
    print("Runs:       number of independent repetitions (default: 1)")
    print("\nExamples:")
    print("  python quick_test.py fastapi")
    print("  python quick_test.py django 1000")
    print("  python quick_test.py gin 10000 heavy")
    print("  python quick_test.py fastapi 100 light 5    # 5 independent runs")
    print()

def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    framework = sys.argv[1].lower()
    load = sys.argv[2] if len(sys.argv) > 2 else "100"
    endpoint = sys.argv[3] if len(sys.argv) > 3 else "light"
    runs = sys.argv[4] if len(sys.argv) > 4 else "1"

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
    print()

    cmd = [
        "python",
        "test_carbon_comprehensive.py",
        "-f", framework,
        "-l", load,
        "-e", endpoint,
        "-r", runs,
    ]

    subprocess.run(cmd)

if __name__ == "__main__":
    main()
