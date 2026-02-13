#!/usr/bin/env python3
"""
Carbon Footprint Analysis & Comparison Report Generator
Analyzes test results and generates comparison reports
"""

import json
import os
import glob
from datetime import datetime
from typing import List, Dict
import statistics

def load_test_results(directory="test_results"):
    """Load all JSON test results from directory"""
    json_files = glob.glob(os.path.join(directory, "*.json"))
    
    all_results = []
    for file_path in json_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
                # Handle both single result and array of results
                if isinstance(data, list):
                    all_results.extend(data)
                else:
                    all_results.append(data)
        except Exception as e:
            print(f"Warning: Could not load {file_path}: {e}")
    
    return all_results


def group_by_criteria(results: List[Dict], criteria: str) -> Dict:
    """Group results by a specific criteria"""
    grouped = {}
    for result in results:
        key = result.get(criteria)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(result)
    return grouped


def calculate_averages(results: List[Dict]) -> Dict:
    """Calculate average metrics from multiple results"""
    if not results:
        return {}
    
    emissions = [r.get('emissions_g', 0) for r in results]
    per_request = [r.get('avg_emissions_per_request_mg', 0) for r in results]
    rps = [r.get('requests_per_second', 0) for r in results]
    mean_times = [r.get('response_time_stats', {}).get('mean_ms', 0) for r in results]
    
    return {
        "count": len(results),
        "avg_emissions_g": round(statistics.mean(emissions), 3) if emissions else 0,
        "avg_emissions_per_request_mg": round(statistics.mean(per_request), 3) if per_request else 0,
        "avg_rps": round(statistics.mean(rps), 2) if rps else 0,
        "avg_response_time_ms": round(statistics.mean(mean_times), 2) if mean_times else 0,
    }


def print_comparison_table(results: List[Dict], group_by: str = "framework"):
    """Print a comparison table grouped by criteria"""
    
    grouped = group_by_criteria(results, group_by)
    
    print("\n" + "="*100)
    print(f"📊 COMPARISON BY {group_by.upper()}")
    print("="*100)
    
    # Table header
    print(f"\n{'Framework':<15} {'Load':<8} {'Endpoint':<10} {'Emissions':<15} {'Per Req':<12} {'RPS':<10} {'Avg Time':<12}")
    print(f"{'':15} {'':8} {'':10} {'(g CO2)':<15} {'(mg CO2)':<12} {'':10} {'(ms)':<12}")
    print("-"*100)
    
    # Sort by framework name
    for key in sorted(grouped.keys()):
        items = grouped[key]
        for item in items:
            framework = item.get('framework', 'N/A')
            load = item.get('load_size', 0)
            endpoint = item.get('endpoint_name', 'N/A')
            emissions = item.get('emissions_g', 0)
            per_req = item.get('avg_emissions_per_request_mg', 0)
            rps = item.get('requests_per_second', 0)
            avg_time = item.get('response_time_stats', {}).get('mean_ms', 0)
            
            print(f"{framework:<15} {load:<8} {endpoint:<10} {emissions:<15.3f} {per_req:<12.3f} {rps:<10.2f} {avg_time:<12.2f}")
    
    print("="*100)


def print_framework_summary(results: List[Dict]):
    """Print summary comparing all frameworks"""
    
    grouped = group_by_criteria(results, "framework_key")
    
    print("\n" + "="*100)
    print("🏆 FRAMEWORK SUMMARY (All Tests Combined)")
    print("="*100)
    print(f"\n{'Framework':<15} {'Tests':<8} {'Avg Emissions':<18} {'Per Request':<15} {'Avg RPS':<12} {'Avg Time':<12}")
    print(f"{'':15} {'':8} {'(g CO2)':<18} {'(mg CO2)':<15} {'':12} {'(ms)':<12}")
    print("-"*100)
    
    summaries = []
    for framework_key in sorted(grouped.keys()):
        items = grouped[framework_key]
        framework_name = items[0].get('framework', framework_key)
        avg = calculate_averages(items)
        
        summaries.append({
            "name": framework_name,
            "key": framework_key,
            **avg
        })
        
        print(f"{framework_name:<15} {avg['count']:<8} {avg['avg_emissions_g']:<18.3f} "
              f"{avg['avg_emissions_per_request_mg']:<15.3f} {avg['avg_rps']:<12.2f} "
              f"{avg['avg_response_time_ms']:<12.2f}")
    
    print("="*100)
    
    # Find winners
    if summaries:
        print("\n🥇 WINNERS:")
        min_emissions = min(summaries, key=lambda x: x['avg_emissions_g'])
        min_per_request = min(summaries, key=lambda x: x['avg_emissions_per_request_mg'])
        max_rps = max(summaries, key=lambda x: x['avg_rps'])
        min_time = min(summaries, key=lambda x: x['avg_response_time_ms'])
        
        print(f"  Lowest Total Emissions:     {min_emissions['name']} ({min_emissions['avg_emissions_g']:.3f}g CO2)")
        print(f"  Lowest Per-Request:         {min_per_request['name']} ({min_per_request['avg_emissions_per_request_mg']:.3f}mg CO2)")
        print(f"  Highest Throughput:         {max_rps['name']} ({max_rps['avg_rps']:.2f} req/s)")
        print(f"  Fastest Response Time:      {min_time['name']} ({min_time['avg_response_time_ms']:.2f}ms)")
        print()


def print_load_analysis(results: List[Dict]):
    """Analyze how each framework scales with load"""
    
    print("\n" + "="*100)
    print("📈 LOAD SCALING ANALYSIS")
    print("="*100)
    
    grouped_by_framework = group_by_criteria(results, "framework_key")
    
    for framework_key in sorted(grouped_by_framework.keys()):
        items = grouped_by_framework[framework_key]
        framework_name = items[0].get('framework', framework_key)
        
        grouped_by_load = group_by_criteria(items, "load_size")
        
        print(f"\n{framework_name}:")
        print(f"{'  Load':<10} {'Emissions (g)':<15} {'Per Req (mg)':<15} {'RPS':<12} {'Avg Time (ms)':<15}")
        print("  " + "-"*65)
        
        for load in sorted(grouped_by_load.keys()):
            load_items = grouped_by_load[load]
            avg = calculate_averages(load_items)
            
            print(f"  {load:<10} {avg['avg_emissions_g']:<15.3f} "
                  f"{avg['avg_emissions_per_request_mg']:<15.3f} "
                  f"{avg['avg_rps']:<12.2f} {avg['avg_response_time_ms']:<15.2f}")


def print_endpoint_analysis(results: List[Dict]):
    """Analyze performance by endpoint type"""
    
    print("\n" + "="*100)
    print("🎯 ENDPOINT TYPE ANALYSIS")
    print("="*100)
    
    grouped_by_endpoint = group_by_criteria(results, "endpoint_name")
    
    for endpoint in sorted(grouped_by_endpoint.keys()):
        items = grouped_by_endpoint[endpoint]
        print(f"\n{endpoint.upper()} Endpoint:")
        
        grouped_by_framework = group_by_criteria(items, "framework_key")
        
        print(f"{'  Framework':<15} {'Tests':<8} {'Avg Emissions':<15} {'Per Req':<12} {'RPS':<10}")
        print("  " + "-"*60)
        
        for framework_key in sorted(grouped_by_framework.keys()):
            framework_items = grouped_by_framework[framework_key]
            framework_name = framework_items[0].get('framework', framework_key)
            avg = calculate_averages(framework_items)
            
            print(f"  {framework_name:<15} {avg['count']:<8} {avg['avg_emissions_g']:<15.3f} "
                  f"{avg['avg_emissions_per_request_mg']:<12.3f} {avg['avg_rps']:<10.2f}")


def generate_markdown_report(results: List[Dict], output_file="test_results/REPORT.md"):
    """Generate a detailed markdown report"""
    
    with open(output_file, 'w') as f:
        f.write("# Carbon Footprint Comparison Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Total Tests: {len(results)}\n\n")
        
        # Framework Summary
        f.write("## Framework Summary\n\n")
        grouped = group_by_criteria(results, "framework_key")
        
        f.write("| Framework | Tests | Avg Emissions (g CO2) | Per Request (mg CO2) | Avg RPS | Avg Response Time (ms) |\n")
        f.write("|-----------|-------|----------------------|----------------------|---------|------------------------|\n")
        
        for framework_key in sorted(grouped.keys()):
            items = grouped[framework_key]
            framework_name = items[0].get('framework', framework_key)
            avg = calculate_averages(items)
            
            f.write(f"| {framework_name} | {avg['count']} | {avg['avg_emissions_g']:.3f} | "
                   f"{avg['avg_emissions_per_request_mg']:.3f} | {avg['avg_rps']:.2f} | "
                   f"{avg['avg_response_time_ms']:.2f} |\n")
        
        # Detailed Results
        f.write("\n## Detailed Results\n\n")
        f.write("| Framework | Load | Endpoint | Emissions (g) | Per Req (mg) | RPS | Mean Time (ms) |\n")
        f.write("|-----------|------|----------|---------------|--------------|-----|----------------|\n")
        
        for result in sorted(results, key=lambda x: (x.get('framework', ''), x.get('load_size', 0), x.get('endpoint_name', ''))):
            f.write(f"| {result.get('framework', 'N/A')} | {result.get('load_size', 0)} | "
                   f"{result.get('endpoint_name', 'N/A')} | {result.get('emissions_g', 0):.3f} | "
                   f"{result.get('avg_emissions_per_request_mg', 0):.3f} | "
                   f"{result.get('requests_per_second', 0):.2f} | "
                   f"{result.get('response_time_stats', {}).get('mean_ms', 0):.2f} |\n")
        
        f.write("\n## Key Findings\n\n")
        
        # Calculate winners
        grouped = group_by_criteria(results, "framework_key")
        summaries = []
        for framework_key in grouped.keys():
            items = grouped[framework_key]
            framework_name = items[0].get('framework', framework_key)
            avg = calculate_averages(items)
            summaries.append({"name": framework_name, **avg})
        
        if summaries:
            min_emissions = min(summaries, key=lambda x: x['avg_emissions_g'])
            max_rps = max(summaries, key=lambda x: x['avg_rps'])
            
            f.write(f"- **Most Energy Efficient**: {min_emissions['name']} ")
            f.write(f"({min_emissions['avg_emissions_g']:.3f}g CO2 average)\n")
            f.write(f"- **Highest Throughput**: {max_rps['name']} ")
            f.write(f"({max_rps['avg_rps']:.2f} requests/second)\n")
    
    print(f"\n📄 Markdown report saved to: {output_file}")


def main():
    """Main analysis function"""
    print("\n" + "🔬" * 50)
    print("CARBON FOOTPRINT ANALYSIS REPORT")
    print("🔬" * 50)
    
    results = load_test_results()
    
    if not results:
        print("\n❌ No test results found in test_results/ directory")
        print("   Run tests first using: python test_carbon_comprehensive.py --suite")
        return
    
    print(f"\n✓ Loaded {len(results)} test results")
    
    # Generate various analysis reports
    print_comparison_table(results)
    print_framework_summary(results)
    print_load_analysis(results)
    print_endpoint_analysis(results)
    
    # Generate markdown report
    generate_markdown_report(results)
    
    print("\n" + "="*100)
    print("✅ ANALYSIS COMPLETE")
    print("="*100 + "\n")


if __name__ == "__main__":
    main()
