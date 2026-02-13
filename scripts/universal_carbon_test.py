#!/usr/bin/env python3
"""
Universal Carbon Footprint Test Script - Windows Compatible
Works with ANY framework: Django, FastAPI, Spring Boot, Micronaut, Gin, Chi
"""

import subprocess
import time
import json
import os
import platform
from datetime import datetime
from codecarbon import EmissionsTracker
import argparse

class UniversalCarbonTest:
    def __init__(self, framework: str, test_name: str, duration: int, 
                 concurrent_users: int, endpoint: str = "/api/v1/health"):
        self.framework = framework
        self.test_name = test_name
        self.duration = duration
        self.concurrent_users = concurrent_users
        self.app_url = f"http://localhost:8000{endpoint}"
        self.is_windows = platform.system() == "Windows"
        
    def run_test(self):
        print("=" * 70)
        print(f"🌱 Carbon Footprint Test")
        print("=" * 70)
        print(f"Framework: {self.framework}")
        print(f"Test: {self.test_name}")
        print(f"Duration: {self.duration}s")
        print(f"Concurrent Users: {self.concurrent_users}")
        print(f"Endpoint: {self.app_url}")
        print(f"Platform: {platform.system()}")
        print()
        
        # Check if app is responding
        if not self.check_app_health():
            print("❌ Application is not responding!")
            print(f"   Make sure your {self.framework} app is running on port 8000")
            print(f"   Check with: docker ps")
            return
        
        # Warmup
        print("🔥 Warming up application...")
        self.warmup()
        
        # Initialize CodeCarbon tracker
        os.makedirs("test_results", exist_ok=True)
        tracker = EmissionsTracker(
            project_name=f"{self.framework}_{self.test_name}",
            output_dir="./test_results",
            output_file=f"codecarbon_{self.framework}_{self.test_name}.csv",
            log_level="warning",
            # country_iso_code="LK"  # Sri Lanka
        )
        
        print(f"\n🚀 Starting load test and carbon tracking...")
        print(f"   This will take approximately {self.duration} seconds...")
        print()
        
        # Start tracking
        tracker.start()
        test_start = time.time()
        
        # Run load test
        perf_data = self.run_load_test()
        
        test_end = time.time()
        
        # Stop tracking
        emissions_kg = tracker.stop()
        
        actual_duration = test_end - test_start
        
        if not perf_data:
            print("❌ Load test failed")
            return
        
        print(f"✓ Test completed ({actual_duration:.1f}s)")
        
        # Compile results
        results = self.compile_results(perf_data, emissions_kg, actual_duration)
        
        # Save and display
        self.save_results(results)
        self.print_summary(results)
        
        return results
    
    def check_app_health(self) -> bool:
        """Check if application is responding"""
        import requests
        try:
            response = requests.get(self.app_url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"   Health check failed: {e}")
            return False
    
    def warmup(self):
        """Warm up the application"""
        import requests
        try:
            for i in range(50):
                requests.get(self.app_url, timeout=5)
                if i % 10 == 0:
                    print(f"   Warmup: {i}/50 requests...")
        except Exception as e:
            print(f"⚠️  Warmup warning: {e}")
        time.sleep(3)
    
    def run_load_test(self) -> dict:
        """Run load test - Windows compatible"""
        
        # Try Apache Bench first
        ab_result = self._try_apache_bench()
        if ab_result:
            return ab_result
        
        # Fallback to Python-based load test
        print("⚠️  Apache Bench not available, using Python load tester...")
        return self._python_load_test()
    
    def _try_apache_bench(self) -> dict:
        """Try to use Apache Bench"""
        try:
            # On Windows, ab.exe might be in PATH or specific location
            ab_command = "ab.exe" if self.is_windows else "ab"
            
            command = [
                ab_command,
                "-t", str(self.duration),
                "-c", str(self.concurrent_users),
                "-q",
                self.app_url
            ]
            
            print(f"   Running: {ab_command} -t {self.duration} -c {self.concurrent_users}")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.duration + 60,
                shell=self.is_windows  # Use shell on Windows
            )
            
            return self.parse_ab_output(result.stdout)
            
        except FileNotFoundError:
            print("   Apache Bench not found in PATH")
            return None
        except subprocess.TimeoutExpired:
            print("   Load test timed out")
            return None
        except Exception as e:
            print(f"   Apache Bench error: {e}")
            return None
    
    def _python_load_test(self) -> dict:
        """Pure Python load test (fallback)"""
        import requests
        import threading
        from queue import Queue
        
        results_queue = Queue()
        start_time = time.time()
        end_time = start_time + self.duration
        
        def worker():
            local_results = {
                "requests": 0,
                "errors": 0,
                "response_times": []
            }
            
            while time.time() < end_time:
                req_start = time.time()
                try:
                    response = requests.get(self.app_url, timeout=5)
                    req_end = time.time()
                    
                    local_results["requests"] += 1
                    local_results["response_times"].append((req_end - req_start) * 1000)
                    
                    if response.status_code != 200:
                        local_results["errors"] += 1
                except Exception:
                    local_results["errors"] += 1
            
            results_queue.put(local_results)
        
        # Start worker threads
        threads = []
        for _ in range(self.concurrent_users):
            t = threading.Thread(target=worker)
            t.start()
            threads.append(t)
        
        # Show progress
        while time.time() < end_time:
            elapsed = time.time() - start_time
            remaining = self.duration - elapsed
            print(f"   Testing... {remaining:.0f}s remaining", end='\r')
            time.sleep(1)
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        print()  # New line after progress
        
        # Aggregate results
        total_requests = 0
        total_errors = 0
        all_times = []
        
        while not results_queue.empty():
            r = results_queue.get()
            total_requests += r["requests"]
            total_errors += r["errors"]
            all_times.extend(r["response_times"])
        
        if not all_times:
            return {}
        
        all_times.sort()
        actual_duration = time.time() - start_time
        
        return {
            "total_requests": total_requests,
            "failed_requests": total_errors,
            "requests_per_second": total_requests / actual_duration,
            "avg_response_time_ms": sum(all_times) / len(all_times),
            "p50_ms": int(all_times[len(all_times) // 2]),
            "p95_ms": int(all_times[int(len(all_times) * 0.95)]),
            "p99_ms": int(all_times[int(len(all_times) * 0.99)])
        }
    
    def parse_ab_output(self, output: str) -> dict:
        """Parse Apache Bench output"""
        results = {
            "total_requests": 0,
            "failed_requests": 0,
            "requests_per_second": 0,
            "avg_response_time_ms": 0,
            "p50_ms": 0,
            "p95_ms": 0,
            "p99_ms": 0
        }
        
        if not output:
            return results
        
        lines = output.split('\n')
        
        for line in lines:
            if "Complete requests:" in line:
                results["total_requests"] = int(line.split(':')[1].strip())
            elif "Failed requests:" in line:
                results["failed_requests"] = int(line.split(':')[1].strip())
            elif "Requests per second:" in line:
                results["requests_per_second"] = float(line.split(':')[1].split()[0])
            elif "Time per request:" in line and "mean" in line:
                results["avg_response_time_ms"] = float(line.split(':')[1].split()[0])
        
        in_percentile_section = False
        for line in lines:
            if "Percentage of the requests" in line:
                in_percentile_section = True
                continue
            if in_percentile_section:
                if "50%" in line:
                    results["p50_ms"] = int(line.split()[1])
                elif "95%" in line:
                    results["p95_ms"] = int(line.split()[1])
                elif "99%" in line:
                    results["p99_ms"] = int(line.split()[1])
        
        return results
    
    def compile_results(self, perf_data: dict, emissions_kg: float, 
                       actual_duration: float) -> dict:
        """Compile all results into a structured format"""
        total_requests = perf_data.get("total_requests", 1)
        emissions_grams = emissions_kg * 1000
        
        co2_per_request_mg = (emissions_grams / total_requests) * 1000 if total_requests > 0 else 0
        co2_per_1k_requests = co2_per_request_mg * 1000 / 1000
        
        return {
            "test_metadata": {
                "framework": self.framework,
                "test_name": self.test_name,
                "timestamp": datetime.utcnow().isoformat(),
                "duration_seconds": actual_duration,
                "concurrent_users": self.concurrent_users,
                "endpoint": self.app_url,
                "platform": platform.system(),
                "measurement_method": "codecarbon"
            },
            "performance": {
                "total_requests": perf_data.get("total_requests", 0),
                "successful_requests": perf_data.get("total_requests", 0) - perf_data.get("failed_requests", 0),
                "failed_requests": perf_data.get("failed_requests", 0),
                "requests_per_second": perf_data.get("requests_per_second", 0),
                "avg_response_time_ms": perf_data.get("avg_response_time_ms", 0),
                "p50_response_time_ms": perf_data.get("p50_ms", 0),
                "p95_response_time_ms": perf_data.get("p95_ms", 0),
                "p99_response_time_ms": perf_data.get("p99_ms", 0)
            },
            "carbon": {
                "total_co2_kg": emissions_kg,
                "total_co2_grams": emissions_grams,
                "co2_per_request_milligrams": co2_per_request_mg,
                "co2_per_1000_requests_grams": co2_per_1k_requests,
                "duration_seconds": actual_duration,
                "country": "Sri Lanka (LK)",
                "measurement_method": "codecarbon_estimation"
            }
        }
    
    def save_results(self, results: dict):
        """Save results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results/{self.framework}_{self.test_name}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")
    
    def print_summary(self, results: dict):
        """Print formatted summary"""
        print("\n" + "=" * 70)
        print(f"📊 TEST SUMMARY - {self.framework.upper()}")
        print("=" * 70)
        
        perf = results["performance"]
        carbon = results["carbon"]
        
        print(f"\n📈 Performance Metrics:")
        print(f"   Total requests:      {perf['total_requests']:,}")
        print(f"   Successful:          {perf['successful_requests']:,}")
        print(f"   Failed:              {perf['failed_requests']:,}")
        print(f"   Requests/sec:        {perf['requests_per_second']:.2f}")
        print(f"   Avg response time:   {perf['avg_response_time_ms']:.2f} ms")
        print(f"   P50:                 {perf['p50_response_time_ms']} ms")
        print(f"   P95:                 {perf['p95_response_time_ms']} ms")
        print(f"   P99:                 {perf['p99_response_time_ms']} ms")
        
        print(f"\n🌍 Carbon Footprint:")
        print(f"   Total CO2:           {carbon['total_co2_grams']:.3f} grams")
        print(f"   Per request:         {carbon['co2_per_request_milligrams']:.6f} mg")
        print(f"   Per 1000 requests:   {carbon['co2_per_1000_requests_grams']:.3f} grams")
        print(f"   Test duration:       {carbon['duration_seconds']:.1f} seconds")
        print(f"   Measurement:         {carbon['measurement_method']}")
        
        print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Universal Carbon Footprint Testing Tool (Windows Compatible)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test FastAPI
  python universal_carbon_test.py --framework fastapi --test light_load --duration 60 --users 10
  
  # Test Django
  python universal_carbon_test.py --framework django --test moderate_load --duration 120 --users 50
  
  # Test Spring Boot
  python universal_carbon_test.py --framework springboot --test heavy_load --duration 180 --users 200
        """
    )
    
    parser.add_argument("--framework", required=True,
                       choices=["fastapi", "django", "springboot", "micronaut", "gin", "chi"],
                       help="Framework being tested")
    parser.add_argument("--test", default="light_load",
                       help="Test name (e.g., light_load, moderate_load, heavy_load)")
    parser.add_argument("--duration", type=int, default=60,
                       help="Test duration in seconds")
    parser.add_argument("--users", type=int, default=10,
                       help="Number of concurrent users")
    parser.add_argument("--endpoint", default="/api/v1/health",
                       help="API endpoint to test")
    
    args = parser.parse_args()
    
    tester = UniversalCarbonTest(
        framework=args.framework,
        test_name=args.test,
        duration=args.duration,
        concurrent_users=args.users,
        endpoint=args.endpoint
    )
    
    tester.run_test()


if __name__ == "__main__":
    main()