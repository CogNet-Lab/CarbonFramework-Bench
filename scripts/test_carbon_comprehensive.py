#!/usr/bin/env python3
"""
Comprehensive Carbon Footprint Test Script
Tests multiple frameworks with various load levels (100, 1000, 10000 requests)
"""

import subprocess
import time
import json
import os
import sys
import csv
import threading
from datetime import datetime
from codecarbon import EmissionsTracker
import requests
import concurrent.futures
import statistics

# Framework configurations
FRAMEWORKS = {
    "fastapi": {"port": 8000, "name": "FastAPI", "folder": "fastapi-carbon-test"},
    "django": {"port": 8001, "name": "Django", "folder": "django-carbon-test"},
    "springboot": {"port": 8002, "name": "Spring Boot", "folder": "springboot-carbon-test"},
    "micronaut": {"port": 8003, "name": "Micronaut", "folder": "micronaut-carbon-test"},
    "gin": {"port": 8004, "name": "Gin", "folder": "gin-carbon-test"},
    "chi": {"port": 8005, "name": "Chi", "folder": "chi-carbon-test"},
}

# Test configurations
TEST_LOADS = [100, 1000, 10000]
ENDPOINTS = {
    "light": "/api/v1/weather/analytics/light",
    "medium": "/api/v1/weather/analytics/medium",
    "heavy": "/api/v1/weather/analytics/heavy",
}

# Measurement reliability thresholds (seconds)
# CodeCarbon's default sampling interval is ~15 seconds
RELIABILITY_THRESHOLDS = {
    "reliable": 15.0,    # >= 15s: at least one full CodeCarbon sampling window
    "marginal": 5.0,     # >= 5s but < 15s: partial sampling
    # < 5s: "unreliable" — below noise floor
}

class LoadTester:
    def __init__(self, framework, port, load_size, endpoint_path, endpoint_name):
        self.framework = framework
        self.base_url = f"http://localhost:{port}"
        self.endpoint_url = f"{self.base_url}{endpoint_path}"
        self.load_size = load_size
        self.endpoint_name = endpoint_name
        self.results = {
            "success": 0,
            "errors": 0,
            "response_times": [],
        }
    
    def make_request(self):
        """Make a single request and return timing"""
        try:
            start = time.time()
            response = requests.get(self.endpoint_url, timeout=30)
            elapsed = (time.time() - start) * 1000  # Convert to ms
            
            if response.status_code == 200:
                return {"success": True, "time": elapsed}
            else:
                return {"success": False, "time": elapsed}
        except Exception as e:
            return {"success": False, "time": 0, "error": str(e)}
    
    def run_sequential(self):
        """Run requests sequentially"""
        print(f"   Running {self.load_size} sequential requests...")
        start_time = time.time()
        
        for i in range(self.load_size):
            result = self.make_request()
            if result["success"]:
                self.results["success"] += 1
                self.results["response_times"].append(result["time"])
            else:
                self.results["errors"] += 1
            
            # Progress update
            if (i + 1) % max(1, self.load_size // 10) == 0:
                print(f"      Progress: {i + 1}/{self.load_size}")
        
        elapsed = time.time() - start_time
        return elapsed
    
    def run_concurrent(self, max_workers=50):
        """Run requests concurrently"""
        print(f"   Running {self.load_size} concurrent requests (workers={max_workers})...")
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.make_request) for _ in range(self.load_size)]
            
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result["success"]:
                    self.results["success"] += 1
                    self.results["response_times"].append(result["time"])
                else:
                    self.results["errors"] += 1
                
                completed += 1
                if completed % max(1, self.load_size // 10) == 0:
                    print(f"      Progress: {completed}/{self.load_size}")
        
        elapsed = time.time() - start_time
        return elapsed
    
    def get_statistics(self):
        """Calculate statistics from results"""
        times = self.results["response_times"]
        
        if not times:
            return {
                "min_ms": 0,
                "max_ms": 0,
                "mean_ms": 0,
                "median_ms": 0,
                "p95_ms": 0,
                "p99_ms": 0,
            }
        
        times_sorted = sorted(times)
        
        return {
            "min_ms": round(min(times), 2),
            "max_ms": round(max(times), 2),
            "mean_ms": round(statistics.mean(times), 2),
            "median_ms": round(statistics.median(times), 2),
            "p95_ms": round(times_sorted[int(len(times_sorted) * 0.95)], 2),
            "p99_ms": round(times_sorted[int(len(times_sorted) * 0.99)], 2),
        }


class ContainerMonitor:
    """Polls Docker container CPU% and memory via `docker stats --no-stream` in a background thread."""

    def __init__(self, container_name, interval=1.0):
        self.container_name = container_name
        self.interval = interval
        self.cpu_samples = []
        self.mem_samples = []
        self._running = False
        self._thread = None
        self._error = None

    @staticmethod
    def _parse_cpu(cpu_str):
        """Parse '2.50%' -> 2.50 float."""
        try:
            return float(cpu_str.strip().rstrip("%"))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_mem(mem_str):
        """Parse '45.5MiB / 1.5GiB' -> 45.5 (MB). Handles GiB, MiB, KiB, B."""
        try:
            usage_part = mem_str.split("/")[0].strip()
            value_str = ""
            unit = ""
            for ch in usage_part:
                if ch.isdigit() or ch == ".":
                    value_str += ch
                else:
                    unit += ch
            value = float(value_str)
            unit = unit.strip().lower()
            if "gib" in unit:
                return value * 1024
            elif "mib" in unit:
                return value
            elif "kib" in unit:
                return value / 1024
            elif "b" in unit:
                return value / (1024 * 1024)
            return value  # assume MiB
        except (ValueError, TypeError, IndexError):
            return None

    def _poll(self):
        """Background thread: poll docker stats until stopped."""
        while self._running:
            try:
                result = subprocess.run(
                    ["docker", "stats", self.container_name, "--no-stream",
                     "--format", "{{.CPUPerc}}\t{{.MemUsage}}"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    parts = result.stdout.strip().split("\t")
                    if len(parts) >= 2:
                        cpu = self._parse_cpu(parts[0])
                        mem = self._parse_mem(parts[1])
                        if cpu is not None:
                            self.cpu_samples.append(cpu)
                        if mem is not None:
                            self.mem_samples.append(mem)
            except FileNotFoundError:
                self._error = "Docker CLI not found"
                break
            except subprocess.TimeoutExpired:
                pass
            except Exception as e:
                self._error = str(e)
                break

            # Sleep in small increments for responsive stopping
            elapsed = 0.0
            while self._running and elapsed < self.interval:
                time.sleep(0.1)
                elapsed += 0.1

    def start(self):
        """Start background polling."""
        self._running = True
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop polling and return result dict."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)

        result = {
            "container_name": self.container_name,
            "sample_count": len(self.cpu_samples),
            "sample_interval_s": self.interval,
        }

        if self.cpu_samples:
            result["cpu_percent_avg"] = round(statistics.mean(self.cpu_samples), 2)
            result["cpu_percent_max"] = round(max(self.cpu_samples), 2)
            result["cpu_percent_min"] = round(min(self.cpu_samples), 2)
            result["cpu_percent_samples"] = [round(s, 2) for s in self.cpu_samples]
        else:
            result["cpu_percent_avg"] = None
            result["cpu_percent_max"] = None
            result["cpu_percent_min"] = None
            result["cpu_percent_samples"] = []

        if self.mem_samples:
            result["memory_mb_avg"] = round(statistics.mean(self.mem_samples), 2)
            result["memory_mb_max"] = round(max(self.mem_samples), 2)
            result["memory_mb_min"] = round(min(self.mem_samples), 2)
            result["memory_mb_baseline"] = round(self.mem_samples[0], 2)
            result["memory_mb_samples"] = [round(s, 2) for s in self.mem_samples]
        else:
            result["memory_mb_avg"] = None
            result["memory_mb_max"] = None
            result["memory_mb_min"] = None
            result["memory_mb_baseline"] = None
            result["memory_mb_samples"] = []

        if self._error:
            result["error"] = self._error

        return result


def check_health(framework, port):
    """Check if framework is responding"""
    try:
        response = requests.get(f"http://localhost:{port}/api/v1/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def warmup(port, requests_count=50):
    """Warm up the application"""
    print(f"   Warming up with {requests_count} requests...")
    url = f"http://localhost:{port}/api/v1/health"
    for i in range(requests_count):
        try:
            requests.get(url, timeout=5)
        except:
            pass
    time.sleep(2)


def extract_energy_metadata(csv_path, test_duration):
    """Extract rich metadata from CodeCarbon's CSV output.

    Reads the last row of the CSV to capture tracking mode, power values,
    energy breakdown, and hardware info.  Detects whether power measurement
    is TDP-based (constant cpu_power) or hardware-based (RAPL/powermetrics).
    Classifies measurement reliability based on test duration relative to
    CodeCarbon's ~15s sampling window.

    Returns a dict; wrapped in try/except so a failure here never blocks
    the test pipeline.
    """
    try:
        if not os.path.exists(csv_path):
            return {"error": f"CSV not found: {csv_path}"}

        with open(csv_path, "r", newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        if not rows:
            return {"error": "CSV is empty"}

        last = rows[-1]

        # --- Power measurement method detection ---
        cpu_power_values = []
        for row in rows:
            try:
                cpu_power_values.append(float(row.get("cpu_power", 0)))
            except (ValueError, TypeError):
                pass

        if cpu_power_values and len(set(cpu_power_values)) == 1:
            power_method = f"TDP-based (constant cpu_power={cpu_power_values[0]}W)"
        elif cpu_power_values:
            power_method = "Hardware-based (RAPL/powermetrics)"
        else:
            power_method = "unknown"

        # --- Reliability classification ---
        if test_duration >= RELIABILITY_THRESHOLDS["reliable"]:
            reliability = "reliable"
        elif test_duration >= RELIABILITY_THRESHOLDS["marginal"]:
            reliability = "marginal"
        else:
            reliability = "unreliable"

        # --- Helper to safely extract floats ---
        def _float(key, default=0.0):
            try:
                return float(last.get(key, default))
            except (ValueError, TypeError):
                return default

        metadata = {
            "tracking_mode": last.get("tracking_mode", "unknown"),
            "power_measurement_method": power_method,
            "measurement_reliability": reliability,
            "cpu_power_w": _float("cpu_power"),
            "gpu_power_w": _float("gpu_power"),
            "ram_power_w": _float("ram_power"),
            "cpu_energy_kwh": _float("cpu_energy"),
            "gpu_energy_kwh": _float("gpu_energy"),
            "ram_energy_kwh": _float("ram_energy"),
            "energy_consumed_kwh": _float("energy_consumed"),
            "cpu_model": last.get("cpu_model", "unknown"),
            "gpu_model": last.get("gpu_model", "unknown"),
            "ram_total_size_gb": _float("ram_total_size"),
            "cpu_count": last.get("cpu_count", "unknown"),
            "codecarbon_version": last.get("codecarbon_version", "unknown"),
            "os": last.get("os", "unknown"),
            "country_iso_code": last.get("country_iso_code", "unknown"),
            "region": last.get("region", "unknown"),
        }

        return metadata

    except Exception as e:
        return {
            "error": str(e),
            "measurement_reliability": "unknown",
        }


def run_test(framework_key, load_size, endpoint_name, endpoint_path, run_id=None, min_duration=0):
    """Run a complete test for one framework, load size, and endpoint"""

    framework_config = FRAMEWORKS[framework_key]
    framework_name = framework_config["name"]
    port = framework_config["port"]

    run_label = f" (Run {run_id})" if run_id is not None else ""

    print("\n" + "=" * 80)
    print(f"🌱 Carbon Footprint Test{run_label}")
    print("=" * 80)
    print(f"Framework: {framework_name}")
    print(f"Load: {load_size} requests")
    print(f"Endpoint: {endpoint_name} ({endpoint_path})")
    print(f"URL: http://localhost:{port}{endpoint_path}")
    print()
    
    # Check health
    if not check_health(framework_key, port):
        print(f"❌ {framework_name} is not responding on port {port}!")
        print(f"   Make sure the container is running:")
        print(f"   cd {framework_config['folder']} && docker-compose up -d")
        return None
    
    print(f"✓ {framework_name} is healthy")
    
    # Warmup
    warmup(port)
    
    # Initialize load tester
    tester = LoadTester(framework_key, port, load_size, endpoint_path, endpoint_name)
    
    # Initialize CodeCarbon tracker
    os.makedirs("test_results", exist_ok=True)
    test_id = f"{framework_key}_{endpoint_name}_{load_size}"
    
    tracker = EmissionsTracker(
        project_name=test_id,
        output_dir="./test_results",
        output_file=f"codecarbon_{test_id}.csv",
        log_level="warning",
    )
    
    print(f"\n🚀 Starting load test and carbon tracking...")

    # Start tracking
    tracker.start()
    test_start = time.time()

    # Start container resource monitoring (app container only, not DB)
    container_name = f"{framework_config['folder']}-app-1"
    monitor = ContainerMonitor(container_name)
    monitor.start()

    # Run load test (use concurrent for large loads)
    if load_size <= 100:
        test_duration = tester.run_sequential()
    else:
        workers = min(100, load_size // 10)
        test_duration = tester.run_concurrent(max_workers=workers)

    test_end = time.time()
    actual_duration = test_end - test_start

    # Stop container monitor (captures load-phase metrics only, not padding)
    container_metrics = monitor.stop()

    # Pad with sleep if --min-duration requires a longer measurement window
    padding_seconds = 0.0
    if min_duration > 0 and actual_duration < min_duration:
        padding_seconds = min_duration - actual_duration
        print(f"\n   Padding {padding_seconds:.1f}s to reach --min-duration={min_duration}s "
              f"(test ran {actual_duration:.1f}s)...")
        time.sleep(padding_seconds)

    # Stop tracking
    emissions_kg = tracker.stop()

    total_tracked_duration = actual_duration + padding_seconds
    stats = tester.get_statistics()

    print(f"\n✓ Test completed ({actual_duration:.2f}s load + {padding_seconds:.1f}s padding)")

    # Extract energy metadata from CodeCarbon CSV (before next test overwrites it)
    csv_path = f"./test_results/codecarbon_{test_id}.csv"
    energy_metadata = extract_energy_metadata(csv_path, total_tracked_duration)

    # Print reliability warning
    reliability = energy_metadata.get("measurement_reliability", "unknown")
    if reliability == "unreliable":
        print(f"\n   ⚠️  WARNING: Test duration ({total_tracked_duration:.1f}s) is UNRELIABLE — "
              f"below CodeCarbon's ~15s sampling window.")
        print(f"      Energy readings are likely noise. Use --min-duration 15 for reliable measurements.")
    elif reliability == "marginal":
        print(f"\n   ⚠️  NOTICE: Test duration ({total_tracked_duration:.1f}s) is MARGINAL — "
              f"partial CodeCarbon sampling window.")
        print(f"      Consider --min-duration 15 for more reliable measurements.")

    # Compile results
    results = {
        "framework": framework_name,
        "framework_key": framework_key,
        "load_size": load_size,
        "endpoint_name": endpoint_name,
        "endpoint_path": endpoint_path,
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": round(actual_duration, 2),
        "test_duration_seconds": round(test_duration, 2),
        "total_tracked_duration_seconds": round(total_tracked_duration, 2),
        "emissions_kg": round(emissions_kg, 6) if emissions_kg else 0,
        "emissions_g": round(emissions_kg * 1000, 3) if emissions_kg else 0,
        "success_count": tester.results["success"],
        "error_count": tester.results["errors"],
        "success_rate": round(tester.results["success"] / load_size * 100, 2),
        "requests_per_second": round(load_size / test_duration, 2),
        "avg_emissions_per_request_mg": round(emissions_kg * 1000000 / load_size, 3) if emissions_kg else 0,
        "response_time_stats": stats,
        "energy_metadata": energy_metadata,
        "measurement_reliability": reliability,
        "container_metrics": container_metrics,
    }
    if padding_seconds > 0:
        results["padding_seconds"] = round(padding_seconds, 2)
    if run_id is not None:
        results["run_id"] = run_id

    # Save results
    save_results(results, test_id, run_id=run_id)
    print_summary(results)

    return results


def save_results(results, test_id, run_id=None):
    """Save test results to JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_suffix = f"_run{run_id}" if run_id is not None else ""
    filename = f"test_results/{test_id}{run_suffix}_{timestamp}.json"

    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: {filename}")


def print_summary(results):
    """Print test summary"""
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"Framework:              {results['framework']}")
    print(f"Load:                   {results['load_size']} requests")
    print(f"Endpoint:               {results['endpoint_name']}")
    print(f"Duration:               {results['duration_seconds']}s")
    print(f"Requests/sec:           {results['requests_per_second']}")
    print()
    print(f"Success:                {results['success_count']} ({results['success_rate']}%)")
    print(f"Errors:                 {results['error_count']}")
    print()
    print(f"💨 Carbon Emissions:")
    print(f"  Total:                {results['emissions_g']}g CO2")
    print(f"  Per Request:          {results['avg_emissions_per_request_mg']}mg CO2")
    print()
    print(f"⏱️  Response Times:")
    stats = results['response_time_stats']
    print(f"  Min:                  {stats['min_ms']}ms")
    print(f"  Mean:                 {stats['mean_ms']}ms")
    print(f"  Median:               {stats['median_ms']}ms")
    print(f"  P95:                  {stats['p95_ms']}ms")
    print(f"  P99:                  {stats['p99_ms']}ms")
    print(f"  Max:                  {stats['max_ms']}ms")
    print()

    # Container Resource Usage
    cm = results.get("container_metrics", {})
    if cm and cm.get("sample_count", 0) > 0:
        print(f"🐳 Container Resource Usage ({cm.get('container_name', 'N/A')}):")
        print(f"  CPU:  avg={cm.get('cpu_percent_avg', 'N/A')}%, max={cm.get('cpu_percent_max', 'N/A')}%  ({cm['sample_count']} samples)")
        mem_avg = cm.get('memory_mb_avg')
        mem_max = cm.get('memory_mb_max')
        mem_base = cm.get('memory_mb_baseline')
        if mem_avg is not None:
            print(f"  RAM:  avg={mem_avg}MB, max={mem_max}MB, baseline={mem_base}MB")
    elif cm and cm.get("error"):
        print(f"🐳 Container Resource Usage: Error — {cm['error']}")
    else:
        print(f"🐳 Container Resource Usage: No samples collected")
    print()

    # Energy Measurement Details
    em = results.get("energy_metadata", {})
    if em and "error" not in em:
        reliability = em.get("measurement_reliability", "unknown")
        reliability_marker = {"reliable": "✓", "marginal": "~", "unreliable": "✗"}.get(reliability, "?")
        print(f"🔬 Energy Measurement Details:")
        print(f"  Tracking Mode:        {em.get('tracking_mode', 'N/A')}")
        print(f"  Power Method:         {em.get('power_measurement_method', 'N/A')}")
        print(f"  Reliability:          {reliability_marker} {reliability}")
        cpu_e = em.get("cpu_energy_kwh", 0)
        gpu_e = em.get("gpu_energy_kwh", 0)
        ram_e = em.get("ram_energy_kwh", 0)
        total_e = em.get("energy_consumed_kwh", 0)
        print(f"  Energy Breakdown:     CPU={cpu_e:.6f} kWh, GPU={gpu_e:.6f} kWh, RAM={ram_e:.6f} kWh")
        print(f"  Total Energy:         {total_e:.6f} kWh")
        print(f"  Hardware:             {em.get('cpu_model', 'N/A')} ({em.get('cpu_count', '?')} CPUs), "
              f"{em.get('ram_total_size_gb', '?')} GB RAM")
    elif em and "error" in em:
        print(f"🔬 Energy Measurement Details: Error — {em['error']}")
    print("=" * 80)


def measure_startup_time(framework_key, timeout=120):
    """Measure cold-start time by restarting the app container and polling health.

    Returns a dict with framework info and startup_time_seconds.
    """
    framework_config = FRAMEWORKS[framework_key]
    container_name = f"{framework_config['folder']}-app-1"
    port = framework_config["port"]
    health_url = f"http://localhost:{port}/api/v1/health"

    print(f"\n  Measuring startup for {framework_config['name']} ({container_name})...")

    # Stop the container
    try:
        subprocess.run(["docker", "stop", container_name],
                        capture_output=True, text=True, timeout=30)
    except Exception as e:
        return {
            "framework_key": framework_key,
            "framework": framework_config["name"],
            "container_name": container_name,
            "startup_time_seconds": None,
            "error": f"Failed to stop container: {e}",
            "timestamp": datetime.now().isoformat(),
        }

    time.sleep(2)  # Wait for full stop

    # Start the container and time until health responds
    start_time = time.time()
    try:
        subprocess.run(["docker", "start", container_name],
                        capture_output=True, text=True, timeout=30)
    except Exception as e:
        return {
            "framework_key": framework_key,
            "framework": framework_config["name"],
            "container_name": container_name,
            "startup_time_seconds": None,
            "error": f"Failed to start container: {e}",
            "timestamp": datetime.now().isoformat(),
        }

    # Poll health endpoint
    while time.time() - start_time < timeout:
        try:
            resp = requests.get(health_url, timeout=2)
            if resp.status_code == 200:
                startup_time = time.time() - start_time
                print(f"    {framework_config['name']}: {startup_time:.2f}s")
                return {
                    "framework_key": framework_key,
                    "framework": framework_config["name"],
                    "container_name": container_name,
                    "startup_time_seconds": round(startup_time, 3),
                    "timestamp": datetime.now().isoformat(),
                }
        except requests.exceptions.ConnectionError:
            pass
        except Exception:
            pass
        time.sleep(0.5)

    return {
        "framework_key": framework_key,
        "framework": framework_config["name"],
        "container_name": container_name,
        "startup_time_seconds": None,
        "error": f"Health endpoint did not respond within {timeout}s",
        "timestamp": datetime.now().isoformat(),
    }


def run_startup_benchmark(frameworks=None, num_runs=3):
    """Measure container cold-start times for all (or selected) frameworks.

    Uses round-robin ordering across runs for temporal fairness.
    Results are saved to test_results/startup_times_{timestamp}.json.
    """
    if frameworks is None:
        frameworks = list(FRAMEWORKS.keys())

    print("\n" + "=" * 80)
    print("  CONTAINER STARTUP TIME BENCHMARK")
    print("=" * 80)
    print(f"  Frameworks: {', '.join([FRAMEWORKS[f]['name'] for f in frameworks])}")
    print(f"  Runs: {num_runs}")
    print()

    all_results = []

    for run_id in range(1, num_runs + 1):
        print(f"\n  --- Round {run_id}/{num_runs} ---")
        for fw_key in frameworks:
            result = measure_startup_time(fw_key)
            result["run_id"] = run_id
            all_results.append(result)

            # Wait between measurements for stabilization
            time.sleep(5)

    # Save results
    os.makedirs("test_results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_results/startup_times_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(all_results, f, indent=2)

    # Print summary table
    print(f"\n\n{'='*80}")
    print("  STARTUP TIME SUMMARY")
    print(f"{'='*80}")
    print(f"\n  {'Framework':<15} {'Runs':<8} {'Mean (s)':<12} {'Std (s)':<12} {'Min (s)':<12} {'Max (s)':<12}")
    print("  " + "-" * 70)

    for fw_key in frameworks:
        fw_results = [r for r in all_results
                      if r["framework_key"] == fw_key and r.get("startup_time_seconds") is not None]
        times = [r["startup_time_seconds"] for r in fw_results]
        if times:
            mean_t = statistics.mean(times)
            std_t = statistics.stdev(times) if len(times) >= 2 else 0.0
            print(f"  {FRAMEWORKS[fw_key]['name']:<15} {len(times):<8} {mean_t:<12.3f} {std_t:<12.3f} "
                  f"{min(times):<12.3f} {max(times):<12.3f}")
        else:
            print(f"  {FRAMEWORKS[fw_key]['name']:<15} {'0':<8} {'N/A':<12} {'N/A':<12} {'N/A':<12} {'N/A':<12}")

    print(f"\n  Results saved to: {filename}")
    print()

    return all_results


def run_comparison_suite(frameworks=None, loads=None, endpoints=None, num_runs=5, min_duration=0):
    """Run comprehensive comparison across frameworks, loads, and endpoints.

    Uses round-robin ordering: all configurations run in round 1, then all in
    round 2, etc.  This spreads measurements across time so that temporal
    factors (thermal throttling, background load) affect all frameworks equally
    and makes the independence assumption for statistical tests more defensible.
    """

    if frameworks is None:
        frameworks = list(FRAMEWORKS.keys())
    if loads is None:
        loads = TEST_LOADS
    if endpoints is None:
        endpoints = ENDPOINTS

    all_results = []

    # Build list of (framework, load, endpoint_name, endpoint_path) configs
    configs = []
    for framework in frameworks:
        for load in loads:
            for endpoint_name, endpoint_path in endpoints.items():
                configs.append((framework, load, endpoint_name, endpoint_path))

    total_tests = len(configs) * num_runs

    print("\n" + "🔬" * 40)
    print("COMPREHENSIVE CARBON FOOTPRINT COMPARISON")
    print("🔬" * 40)
    print(f"Frameworks: {', '.join([FRAMEWORKS[f]['name'] for f in frameworks])}")
    print(f"Load Sizes: {', '.join(map(str, loads))}")
    print(f"Endpoints: {', '.join(endpoints.keys())}")
    print(f"Runs per config: {num_runs}")
    print(f"Total tests: {total_tests}")
    print()

    current_test = 0

    for run_id in range(1, num_runs + 1):
        print(f"\n\n{'#'*80}")
        print(f"  ROUND {run_id}/{num_runs}")
        print(f"{'#'*80}")

        for framework, load, endpoint_name, endpoint_path in configs:
            current_test += 1
            print(f"\n\n{'='*80}")
            print(f"Test {current_test}/{total_tests} (Round {run_id})")
            print(f"{'='*80}")

            rid = run_id if num_runs > 1 else None
            result = run_test(framework, load, endpoint_name, endpoint_path, run_id=rid, min_duration=min_duration)
            if result:
                all_results.append(result)

            # Small delay between tests
            if current_test < total_tests:
                print("\n  Waiting 5 seconds before next test...")
                time.sleep(5)

    # Save combined results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    combined_file = f"test_results/comparison_suite_{timestamp}.json"
    with open(combined_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n\n{'='*80}")
    print(f"  ALL TESTS COMPLETED!")
    print(f"{'='*80}")
    print(f"Total tests run: {len(all_results)}")
    print(f"Combined results saved to: {combined_file}")
    print()

    return all_results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Carbon Footprint Testing for Web Frameworks")
    parser.add_argument("--framework", "-f", choices=list(FRAMEWORKS.keys()), 
                        help="Specific framework to test")
    parser.add_argument("--load", "-l", type=int, choices=TEST_LOADS,
                        help="Specific load size to test")
    parser.add_argument("--endpoint", "-e", choices=list(ENDPOINTS.keys()),
                        help="Specific endpoint to test")
    parser.add_argument("--suite", "-s", action="store_true",
                        help="Run full comparison suite")
    parser.add_argument("--runs", "-r", type=int, default=None,
                        help="Number of independent repetitions per configuration "
                             "(default: 5 for suite, 1 for single test). "
                             "Use -r 3 for quicker runs or -r 5+ for statistical significance.")
    parser.add_argument("--min-duration", type=float, default=0,
                        help="Minimum test duration in seconds. If the load test finishes "
                             "faster, pad with sleep so CodeCarbon captures at least one "
                             "sampling window. Use 15 for reliable measurements.")
    parser.add_argument("--measure-startup", action="store_true",
                        help="Measure container cold-start times (restarts containers)")
    parser.add_argument("--startup-runs", type=int, default=3,
                        help="Number of startup measurement runs (default: 3)")

    args = parser.parse_args()

    if args.measure_startup:
        fws = [args.framework] if args.framework else None
        run_startup_benchmark(frameworks=fws, num_runs=args.startup_runs)
    elif args.suite:
        num_runs = args.runs if args.runs is not None else 5
        run_comparison_suite(num_runs=num_runs, min_duration=args.min_duration)
    elif args.framework and args.load and args.endpoint:
        num_runs = args.runs if args.runs is not None else 1
        for run_id in range(1, num_runs + 1):
            if num_runs > 1:
                print(f"\n{'#'*80}")
                print(f"  RUN {run_id}/{num_runs}")
                print(f"{'#'*80}")
            rid = run_id if num_runs > 1 else None
            run_test(args.framework, args.load, args.endpoint, ENDPOINTS[args.endpoint],
                     run_id=rid, min_duration=args.min_duration)
            if run_id < num_runs:
                print("\n  Waiting 5 seconds before next run...")
                time.sleep(5)
    else:
        print("Available frameworks:", ", ".join(FRAMEWORKS.keys()))
        print("Available loads:", ", ".join(map(str, TEST_LOADS)))
        print("Available endpoints:", ", ".join(ENDPOINTS.keys()))
        print()
        print("Usage:")
        print("  Full suite (5 runs):  python test_carbon_comprehensive.py --suite")
        print("  Suite (3 runs):       python test_carbon_comprehensive.py --suite -r 3")
        print("  Single test:          python test_carbon_comprehensive.py -f fastapi -l 100 -e light")
        print("  Single (3 runs):      python test_carbon_comprehensive.py -f fastapi -l 100 -e light -r 3")
        print("  Help:                 python test_carbon_comprehensive.py --help")
