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


def run_test(framework_key, load_size, endpoint_name, endpoint_path):
    """Run a complete test for one framework, load size, and endpoint"""
    
    framework_config = FRAMEWORKS[framework_key]
    framework_name = framework_config["name"]
    port = framework_config["port"]
    
    print("\n" + "=" * 80)
    print(f"🌱 Carbon Footprint Test")
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
    
    # Run load test (use concurrent for large loads)
    if load_size <= 100:
        test_duration = tester.run_sequential()
    else:
        workers = min(100, load_size // 10)
        test_duration = tester.run_concurrent(max_workers=workers)
    
    test_end = time.time()
    
    # Stop tracking
    emissions_kg = tracker.stop()
    
    actual_duration = test_end - test_start
    stats = tester.get_statistics()
    
    print(f"\n✓ Test completed ({actual_duration:.2f}s)")
    
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
        "emissions_kg": round(emissions_kg, 6) if emissions_kg else 0,
        "emissions_g": round(emissions_kg * 1000, 3) if emissions_kg else 0,
        "success_count": tester.results["success"],
        "error_count": tester.results["errors"],
        "success_rate": round(tester.results["success"] / load_size * 100, 2),
        "requests_per_second": round(load_size / test_duration, 2),
        "avg_emissions_per_request_mg": round(emissions_kg * 1000000 / load_size, 3) if emissions_kg else 0,
        "response_time_stats": stats,
    }
    
    # Save results
    save_results(results, test_id)
    print_summary(results)
    
    return results


def save_results(results, test_id):
    """Save test results to JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_results/{test_id}_{timestamp}.json"
    
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
    print("=" * 80)


def run_comparison_suite(frameworks=None, loads=None, endpoints=None):
    """Run comprehensive comparison across frameworks, loads, and endpoints"""
    
    if frameworks is None:
        frameworks = list(FRAMEWORKS.keys())
    if loads is None:
        loads = TEST_LOADS
    if endpoints is None:
        endpoints = ENDPOINTS
    
    all_results = []
    
    print("\n" + "🔬" * 40)
    print("COMPREHENSIVE CARBON FOOTPRINT COMPARISON")
    print("🔬" * 40)
    print(f"Frameworks: {', '.join([FRAMEWORKS[f]['name'] for f in frameworks])}")
    print(f"Load Sizes: {', '.join(map(str, loads))}")
    print(f"Endpoints: {', '.join(endpoints.keys())}")
    print()
    
    total_tests = len(frameworks) * len(loads) * len(endpoints)
    current_test = 0
    
    for framework in frameworks:
        for load in loads:
            for endpoint_name, endpoint_path in endpoints.items():
                current_test += 1
                print(f"\n\n{'='*80}")
                print(f"Test {current_test}/{total_tests}")
                print(f"{'='*80}")
                
                result = run_test(framework, load, endpoint_name, endpoint_path)
                if result:
                    all_results.append(result)
                
                # Small delay between tests
                if current_test < total_tests:
                    print("\n⏳ Waiting 5 seconds before next test...")
                    time.sleep(5)
    
    # Save combined results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    combined_file = f"test_results/comparison_suite_{timestamp}.json"
    with open(combined_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n\n{'='*80}")
    print(f"✅ ALL TESTS COMPLETED!")
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
    
    args = parser.parse_args()
    
    if args.suite:
        # Run full suite
        run_comparison_suite()
    elif args.framework and args.load and args.endpoint:
        # Run specific test
        run_test(args.framework, args.load, args.endpoint, ENDPOINTS[args.endpoint])
    else:
        # Interactive mode
        print("Available frameworks:", ", ".join(FRAMEWORKS.keys()))
        print("Available loads:", ", ".join(map(str, TEST_LOADS)))
        print("Available endpoints:", ", ".join(ENDPOINTS.keys()))
        print()
        print("Usage:")
        print("  Full suite:    python test_carbon_comprehensive.py --suite")
        print("  Single test:   python test_carbon_comprehensive.py -f fastapi -l 100 -e light")
        print("  Help:          python test_carbon_comprehensive.py --help")
