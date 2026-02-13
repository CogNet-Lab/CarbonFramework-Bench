#!/usr/bin/env python3
"""
Carbon Footprint Analysis & Comparison Report Generator
Analyzes test results and generates comparison reports.

When multiple runs are available (run_id present or >1 result per config),
statistical analysis is performed including:
  - Descriptive statistics with 95% confidence intervals
  - One-way ANOVA across frameworks
  - Pairwise Welch's t-tests with Bonferroni correction
  - Cohen's d effect sizes
  - Significance-qualified winner statements
"""

import json
import os
import glob
import math
import warnings
from datetime import datetime
from itertools import combinations
from typing import List, Dict, Tuple, Optional
import statistics

try:
    import numpy as np
    from scipy import stats as sp_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ---------------------------------------------------------------------------
# Metric extraction helpers
# ---------------------------------------------------------------------------

METRIC_EXTRACTORS = {
    "emissions_g": lambda r: r.get("emissions_g", 0),
    "emissions_per_request_mg": lambda r: r.get("avg_emissions_per_request_mg", 0),
    "rps": lambda r: r.get("requests_per_second", 0),
    "response_time_ms": lambda r: r.get("response_time_stats", {}).get("mean_ms", 0),
}

METRIC_LABELS = {
    "emissions_g": "Total Emissions (g CO2)",
    "emissions_per_request_mg": "Emissions/Request (mg CO2)",
    "rps": "Requests/sec",
    "response_time_ms": "Avg Response Time (ms)",
}

# Lower is better for emissions and response time; higher is better for rps
METRIC_DIRECTION = {
    "emissions_g": "lower",
    "emissions_per_request_mg": "lower",
    "rps": "higher",
    "response_time_ms": "lower",
}

ALPHA = 0.05  # significance level

# Same thresholds as test_carbon_comprehensive.py
RELIABILITY_THRESHOLDS = {
    "reliable": 15.0,
    "marginal": 5.0,
}


def _extract_metric_values(results: List[Dict], metric: str) -> List[float]:
    """Extract a list of metric values from a list of result dicts."""
    extractor = METRIC_EXTRACTORS[metric]
    return [extractor(r) for r in results]


def group_by_config(results: List[Dict]) -> Dict[Tuple[str, int, str], List[Dict]]:
    """Group results by (framework_key, load_size, endpoint_name) tuples."""
    grouped: Dict[Tuple[str, int, str], List[Dict]] = {}
    for r in results:
        key = (r.get("framework_key", ""), r.get("load_size", 0), r.get("endpoint_name", ""))
        grouped.setdefault(key, []).append(r)
    return grouped


def _detect_num_runs(results: List[Dict]) -> int:
    """Detect how many independent runs the results represent.

    Uses the run_id field if present, otherwise counts results per config
    and returns the maximum count.
    """
    run_ids = {r.get("run_id") for r in results if r.get("run_id") is not None}
    if run_ids:
        return max(run_ids)

    config_groups = group_by_config(results)
    if not config_groups:
        return 1
    return max(len(v) for v in config_groups.values())


# ---------------------------------------------------------------------------
# Data loading (with duplicate-counting bug fix)
# ---------------------------------------------------------------------------

def load_test_results(directory="test_results"):
    """Load all JSON test results from directory.

    Skips comparison_suite_*.json files to avoid double-counting results
    that are already present as individual JSON files.
    """
    json_files = glob.glob(os.path.join(directory, "*.json"))

    all_results = []
    for file_path in json_files:
        basename = os.path.basename(file_path)
        # Skip combined suite files to prevent duplicate counting
        if basename.startswith("comparison_suite_"):
            continue
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


# ---------------------------------------------------------------------------
# Measurement reliability helpers
# ---------------------------------------------------------------------------

def _extract_reliability(result: Dict) -> str:
    """Extract measurement reliability from a result dict.

    Checks (in order):
    1. Top-level ``measurement_reliability`` (new format)
    2. Nested ``energy_metadata.measurement_reliability``
    3. Fallback: infer from ``duration_seconds`` using thresholds (backward compat)
    """
    rel = result.get("measurement_reliability")
    if rel:
        return rel

    rel = result.get("energy_metadata", {}).get("measurement_reliability")
    if rel:
        return rel

    # Backward compat: infer from duration
    dur = result.get("total_tracked_duration_seconds") or result.get("duration_seconds")
    if dur is not None:
        if dur >= RELIABILITY_THRESHOLDS["reliable"]:
            return "reliable"
        elif dur >= RELIABILITY_THRESHOLDS["marginal"]:
            return "marginal"
        else:
            return "unreliable"

    return "unknown"


def build_reliability_summary(results: List[Dict]) -> Dict:
    """Build a reliability assessment summary.

    Returns:
        dict with keys:
        - overall: {reliable: N, marginal: N, unreliable: N, unknown: N}
        - by_framework: {fw_key: {reliable: N, ...}}
        - by_config: {(fw, load, ep): {reliable: N, ...}}
        - reliable_fraction: float (0.0–1.0)
    """
    overall: Dict[str, int] = {"reliable": 0, "marginal": 0, "unreliable": 0, "unknown": 0}
    by_framework: Dict[str, Dict[str, int]] = {}
    by_config: Dict[tuple, Dict[str, int]] = {}

    for r in results:
        rel = _extract_reliability(r)
        overall[rel] = overall.get(rel, 0) + 1

        fw = r.get("framework_key", "unknown")
        if fw not in by_framework:
            by_framework[fw] = {"reliable": 0, "marginal": 0, "unreliable": 0, "unknown": 0}
        by_framework[fw][rel] = by_framework[fw].get(rel, 0) + 1

        cfg = (fw, r.get("load_size", 0), r.get("endpoint_name", ""))
        if cfg not in by_config:
            by_config[cfg] = {"reliable": 0, "marginal": 0, "unreliable": 0, "unknown": 0}
        by_config[cfg][rel] = by_config[cfg].get(rel, 0) + 1

    total = sum(overall.values())
    reliable_fraction = overall["reliable"] / total if total > 0 else 0.0

    return {
        "overall": overall,
        "by_framework": by_framework,
        "by_config": by_config,
        "reliable_fraction": reliable_fraction,
    }


def print_reliability_summary(results: List[Dict]):
    """Print measurement reliability assessment to console."""
    summary = build_reliability_summary(results)
    overall = summary["overall"]
    total = sum(overall.values())

    print("\n" + "=" * 100)
    print("  MEASUREMENT RELIABILITY ASSESSMENT")
    print("=" * 100)

    print(f"\n  Overall: {overall['reliable']}/{total} reliable, "
          f"{overall['marginal']}/{total} marginal, "
          f"{overall['unreliable']}/{total} unreliable")

    if overall["unreliable"] > 0:
        print(f"\n  ⚠️  WARNING: {overall['unreliable']} measurements are below CodeCarbon's noise floor (<5s).")
        print(f"     Energy comparisons for these configurations are unreliable.")
        print(f"     Re-run with --min-duration 15 for trustworthy energy measurements.")

    if overall["marginal"] > 0:
        print(f"\n  ⚠️  NOTICE: {overall['marginal']} measurements have partial sampling (5-15s).")

    # Per-framework table
    by_fw = summary["by_framework"]
    if by_fw:
        print(f"\n  {'Framework':<15} {'Reliable':<12} {'Marginal':<12} {'Unreliable':<12} {'Unknown':<10}")
        print("  " + "-" * 60)
        for fw_key in sorted(by_fw.keys()):
            counts = by_fw[fw_key]
            print(f"  {fw_key:<15} {counts['reliable']:<12} {counts['marginal']:<12} "
                  f"{counts['unreliable']:<12} {counts['unknown']:<10}")

    # List fully-unreliable configs
    unreliable_configs = []
    for cfg, counts in summary["by_config"].items():
        if counts["reliable"] == 0 and counts["marginal"] == 0 and (counts["unreliable"] > 0):
            unreliable_configs.append(cfg)

    if unreliable_configs:
        print(f"\n  Fully unreliable configurations (all measurements <5s):")
        for fw, load, ep in sorted(unreliable_configs):
            print(f"    - {fw} / {load} requests / {ep}")

    print()


# ---------------------------------------------------------------------------
# Basic grouping / averaging (backward-compatible)
# ---------------------------------------------------------------------------

def group_by_criteria(results: List[Dict], criteria: str) -> Dict:
    """Group results by a specific criteria."""
    grouped = {}
    for result in results:
        key = result.get(criteria)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(result)
    return grouped


def calculate_statistics(results: List[Dict]) -> Dict:
    """Calculate descriptive statistics with 95% confidence intervals.

    Returns a dict that is backward-compatible with calculate_averages()
    (same avg_* fields) plus additional stat_* fields when n >= 2.
    """
    if not results:
        return {}

    out: Dict = {"count": len(results)}

    for metric, label in [
        ("emissions_g", "emissions_g"),
        ("emissions_per_request_mg", "emissions_per_request_mg"),
        ("rps", "rps"),
        ("response_time_ms", "response_time_ms"),
    ]:
        values = _extract_metric_values(results, metric)
        n = len(values)
        mean_val = statistics.mean(values) if values else 0.0

        # Backward-compatible avg_ keys
        avg_key_map = {
            "emissions_g": "avg_emissions_g",
            "emissions_per_request_mg": "avg_emissions_per_request_mg",
            "rps": "avg_rps",
            "response_time_ms": "avg_response_time_ms",
        }
        out[avg_key_map[metric]] = round(mean_val, 3 if "emissions" in metric else 2)

        # Extended statistics
        if n >= 2:
            std_val = statistics.stdev(values)  # ddof=1
            stderr = std_val / math.sqrt(n)
            if HAS_SCIPY:
                t_crit = sp_stats.t.ppf(1 - ALPHA / 2, df=n - 1)
            else:
                # Rough fallback for n>=2 without scipy
                t_crit = 2.0  # approximate
            ci_low = mean_val - t_crit * stderr
            ci_high = mean_val + t_crit * stderr

            out[f"stat_{metric}_mean"] = round(mean_val, 6)
            out[f"stat_{metric}_std"] = round(std_val, 6)
            out[f"stat_{metric}_stderr"] = round(stderr, 6)
            out[f"stat_{metric}_ci_low"] = round(ci_low, 6)
            out[f"stat_{metric}_ci_high"] = round(ci_high, 6)
            out[f"stat_{metric}_n"] = n
        else:
            out[f"stat_{metric}_mean"] = round(mean_val, 6)
            out[f"stat_{metric}_n"] = n

    return out


def calculate_averages(results: List[Dict]) -> Dict:
    """Backward-compatible wrapper around calculate_statistics()."""
    return calculate_statistics(results)


# ---------------------------------------------------------------------------
# Statistical tests (require scipy)
# ---------------------------------------------------------------------------

def run_anova(grouped_by_framework: Dict[str, List[float]], metric: str) -> Dict:
    """Run one-way ANOVA across framework groups for a given metric.

    Args:
        grouped_by_framework: {framework_key: [metric_values]}
        metric: metric name (for labeling)

    Returns dict with f_statistic, p_value, significant, warning.
    """
    if not HAS_SCIPY:
        return {"warning": "scipy not installed; ANOVA skipped"}

    groups = list(grouped_by_framework.values())
    keys = list(grouped_by_framework.keys())

    if len(groups) < 2:
        return {"warning": "Need at least 2 groups for ANOVA", "significant": False}

    # Check for zero-variance groups (all values identical)
    valid_groups = []
    for g in groups:
        if len(g) < 2:
            return {
                "warning": "Each group needs at least 2 observations for ANOVA",
                "significant": False,
            }
        valid_groups.append(g)

    # Suppress warnings about constant input
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        f_stat, p_value = sp_stats.f_oneway(*valid_groups)

    # Handle NaN (e.g., all groups have zero variance)
    if math.isnan(f_stat) or math.isnan(p_value):
        return {
            "f_statistic": None,
            "p_value": None,
            "significant": False,
            "warning": "ANOVA returned NaN (all groups may have zero variance)",
            "metric": metric,
            "groups": keys,
        }

    return {
        "f_statistic": round(f_stat, 4),
        "p_value": round(p_value, 6),
        "significant": p_value < ALPHA,
        "metric": metric,
        "groups": keys,
        "n_groups": len(keys),
    }


def run_pairwise_tests(
    grouped_by_framework: Dict[str, List[float]], metric: str
) -> List[Dict]:
    """Run pairwise Welch's t-tests with Bonferroni correction.

    Returns a list of dicts, one per pair, with means, p-values, Cohen's d,
    and significance classification.
    """
    if not HAS_SCIPY:
        return []

    keys = sorted(grouped_by_framework.keys())
    pairs = list(combinations(keys, 2))
    num_comparisons = len(pairs)

    results = []
    for fw_a, fw_b in pairs:
        vals_a = grouped_by_framework[fw_a]
        vals_b = grouped_by_framework[fw_b]

        if len(vals_a) < 2 or len(vals_b) < 2:
            results.append({
                "fw_a": fw_a,
                "fw_b": fw_b,
                "warning": "Need >= 2 observations per group",
            })
            continue

        mean_a = statistics.mean(vals_a)
        mean_b = statistics.mean(vals_b)

        # Welch's t-test (unequal variances)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            t_stat, p_raw = sp_stats.ttest_ind(vals_a, vals_b, equal_var=False)

        if math.isnan(t_stat) or math.isnan(p_raw):
            results.append({
                "fw_a": fw_a, "fw_b": fw_b,
                "mean_a": round(mean_a, 6), "mean_b": round(mean_b, 6),
                "warning": "t-test returned NaN",
            })
            continue

        # Bonferroni correction
        p_corrected = min(p_raw * num_comparisons, 1.0)

        # Cohen's d (pooled std)
        std_a = statistics.stdev(vals_a)
        std_b = statistics.stdev(vals_b)
        n_a, n_b = len(vals_a), len(vals_b)
        pooled_std = math.sqrt(
            ((n_a - 1) * std_a**2 + (n_b - 1) * std_b**2) / (n_a + n_b - 2)
        )

        if pooled_std > 0:
            cohens_d = abs(mean_a - mean_b) / pooled_std
        else:
            cohens_d = 0.0

        # Classify effect size
        if cohens_d < 0.2:
            effect_label = "negligible"
        elif cohens_d < 0.5:
            effect_label = "small"
        elif cohens_d < 0.8:
            effect_label = "medium"
        else:
            effect_label = "large"

        results.append({
            "fw_a": fw_a,
            "fw_b": fw_b,
            "mean_a": round(mean_a, 6),
            "mean_b": round(mean_b, 6),
            "t_statistic": round(t_stat, 4),
            "p_raw": round(p_raw, 6),
            "p_corrected": round(p_corrected, 6),
            "significant": p_corrected < ALPHA,
            "cohens_d": round(cohens_d, 4),
            "effect_size": effect_label,
            "num_comparisons": num_comparisons,
        })

    return results


def determine_statistical_winner(
    grouped_by_framework: Dict[str, List[float]],
    metric: str,
    direction: str = "lower",
    reliability_counts: Optional[Dict[str, int]] = None,
) -> Dict:
    """Determine the best framework with statistical qualification.

    Args:
        grouped_by_framework: {framework_key: [metric_values]}
        metric: metric name
        direction: "lower" if lower is better, "higher" if higher is better
        reliability_counts: optional {reliable: N, marginal: N, unreliable: N}
            from build_reliability_summary()["overall"]; used to append caveats.

    Returns dict with winner, is_significant, statement string.
    """
    if not grouped_by_framework:
        return {"winner": None, "is_significant": False, "statement": "No data"}

    # Compute means
    means = {k: statistics.mean(v) for k, v in grouped_by_framework.items()}

    if direction == "lower":
        sorted_fws = sorted(means, key=means.get)
    else:
        sorted_fws = sorted(means, key=means.get, reverse=True)

    best = sorted_fws[0]
    best_mean = means[best]

    if len(sorted_fws) < 2:
        return {
            "winner": best,
            "is_significant": False,
            "statement": f"{best} (only one framework)",
        }

    runner_up = sorted_fws[1]
    runner_up_mean = means[runner_up]

    # Check if we can run a t-test
    vals_best = grouped_by_framework[best]
    vals_runner = grouped_by_framework[runner_up]

    if not HAS_SCIPY or len(vals_best) < 2 or len(vals_runner) < 2:
        return {
            "winner": best,
            "is_significant": False,
            "statement": f"{best} ({best_mean:.4f}) — not enough data for significance test",
        }

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        _, p_value = sp_stats.ttest_ind(vals_best, vals_runner, equal_var=False)

    if math.isnan(p_value):
        significant = False
    else:
        significant = p_value < ALPHA

    if significant:
        tag = "[SIG]"
        qualifier = f"significantly better than {runner_up} (p={p_value:.4f})"
    else:
        tag = "[N.S.]"
        qualifier = f"not significantly different from {runner_up} (p={p_value:.4f})"

    statement = f"{tag} {best} ({best_mean:.4f}) — {qualifier}"

    # Append reliability caveat if applicable
    if reliability_counts:
        total_m = sum(reliability_counts.values())
        unreliable_m = reliability_counts.get("unreliable", 0)
        if total_m > 0 and unreliable_m == total_m:
            statement += " [CAVEAT: all measurements below noise floor]"
        elif unreliable_m > 0:
            statement += f" [CAVEAT: {unreliable_m}/{total_m} measurements unreliable]"

    return {
        "winner": best,
        "is_significant": significant,
        "p_value": round(p_value, 6) if not math.isnan(p_value) else None,
        "runner_up": runner_up,
        "statement": statement,
    }


# ---------------------------------------------------------------------------
# Console output: statistical summary
# ---------------------------------------------------------------------------

def _build_framework_metric_groups(
    results: List[Dict], metric: str
) -> Dict[str, List[float]]:
    """Build {framework_key: [values]} for a metric across all results."""
    grouped_fw = group_by_criteria(results, "framework_key")
    out = {}
    for fw_key, items in grouped_fw.items():
        out[fw_key] = _extract_metric_values(items, metric)
    return out


def print_statistical_summary(results: List[Dict]):
    """Print full statistical summary to console."""
    num_runs = _detect_num_runs(results)

    print("\n" + "=" * 100)
    print("  STATISTICAL SUMMARY")
    print("=" * 100)
    print(f"\nDetected runs per config: {num_runs}")
    if num_runs < 3:
        print("  WARNING: Fewer than 3 runs detected. Statistical tests have very low power.")
        print("  Recommendation: re-run with at least -r 5 for meaningful significance testing.")
    print()

    for metric in METRIC_EXTRACTORS:
        fw_groups = _build_framework_metric_groups(results, metric)
        label = METRIC_LABELS[metric]
        direction = METRIC_DIRECTION[metric]

        # --- Descriptive statistics with CIs ---
        print(f"\n--- {label} ---")
        print(f"{'Framework':<15} {'n':<5} {'Mean':<14} {'Std Dev':<14} {'95% CI':<28}")
        print("-" * 80)

        for fw_key in sorted(fw_groups.keys()):
            vals = fw_groups[fw_key]
            n = len(vals)
            mean_val = statistics.mean(vals)
            if n >= 2:
                std_val = statistics.stdev(vals)
                stderr = std_val / math.sqrt(n)
                if HAS_SCIPY:
                    t_crit = sp_stats.t.ppf(1 - ALPHA / 2, df=n - 1)
                else:
                    t_crit = 2.0
                ci_low = mean_val - t_crit * stderr
                ci_high = mean_val + t_crit * stderr
                ci_str = f"[{ci_low:.4f}, {ci_high:.4f}]"
                std_str = f"{std_val:.4f}"
            else:
                ci_str = "N/A (n=1)"
                std_str = "N/A"
            print(f"{fw_key:<15} {n:<5} {mean_val:<14.4f} {std_str:<14} {ci_str:<28}")

        # --- ANOVA ---
        if num_runs >= 2:
            anova = run_anova(fw_groups, metric)
            if "warning" in anova and anova.get("f_statistic") is None:
                print(f"\n  ANOVA: {anova['warning']}")
            elif "f_statistic" in anova:
                sig_str = "YES" if anova["significant"] else "NO"
                print(f"\n  One-Way ANOVA: F={anova['f_statistic']}, p={anova['p_value']}, significant={sig_str}")
            if anova.get("warning"):
                print(f"  Note: {anova['warning']}")

        # --- Pairwise tests ---
        if num_runs >= 2:
            pairwise = run_pairwise_tests(fw_groups, metric)
            if pairwise:
                print(f"\n  Pairwise Welch's t-tests (Bonferroni-corrected, {len(pairwise)} comparisons):")
                print(f"  {'Pair':<25} {'Mean A':<12} {'Mean B':<12} {'p(corr)':<12} {'Cohen d':<10} {'Effect':<12} {'Sig?':<6}")
                print("  " + "-" * 90)
                for pw in pairwise:
                    if "warning" in pw:
                        print(f"  {pw['fw_a']} vs {pw['fw_b']}: {pw['warning']}")
                        continue
                    pair_str = f"{pw['fw_a']} vs {pw['fw_b']}"
                    sig = "YES" if pw["significant"] else "no"
                    print(f"  {pair_str:<25} {pw['mean_a']:<12.4f} {pw['mean_b']:<12.4f} "
                          f"{pw['p_corrected']:<12.6f} {pw['cohens_d']:<10.4f} {pw['effect_size']:<12} {sig:<6}")

        # --- Winner ---
        winner = determine_statistical_winner(fw_groups, metric, direction)
        print(f"\n  Winner: {winner['statement']}")
        print()


def print_per_config_statistical_analysis(results: List[Dict]):
    """Print ANOVA + winners per (load, endpoint) configuration."""
    if not HAS_SCIPY:
        return

    print("\n" + "=" * 100)
    print("  PER-CONFIGURATION STATISTICAL ANALYSIS")
    print("=" * 100)

    # Group by (load, endpoint)
    config_groups: Dict[Tuple[int, str], Dict[str, List[Dict]]] = {}
    for r in results:
        load = r.get("load_size", 0)
        ep = r.get("endpoint_name", "")
        config_groups.setdefault((load, ep), {})
        fw = r.get("framework_key", "")
        config_groups[(load, ep)].setdefault(fw, []).append(r)

    for (load, ep) in sorted(config_groups.keys()):
        fw_results = config_groups[(load, ep)]
        print(f"\n--- Load={load}, Endpoint={ep} ---")

        for metric in ["emissions_g", "rps"]:
            label = METRIC_LABELS[metric]
            direction = METRIC_DIRECTION[metric]
            fw_groups = {}
            for fw_key, items in fw_results.items():
                fw_groups[fw_key] = _extract_metric_values(items, metric)

            anova = run_anova(fw_groups, metric)
            winner = determine_statistical_winner(fw_groups, metric, direction)

            if "f_statistic" in anova and anova["f_statistic"] is not None:
                sig_str = "YES" if anova["significant"] else "NO"
                print(f"  {label}: ANOVA F={anova['f_statistic']}, p={anova['p_value']}, sig={sig_str}")
            print(f"    Winner: {winner['statement']}")


# ---------------------------------------------------------------------------
# Console output: existing tables (updated)
# ---------------------------------------------------------------------------

def print_comparison_table(results: List[Dict], group_by: str = "framework"):
    """Print a comparison table grouped by criteria."""

    grouped = group_by_criteria(results, group_by)

    print("\n" + "=" * 100)
    print(f"  COMPARISON BY {group_by.upper()}")
    print("=" * 100)

    # Table header
    print(f"\n{'Framework':<15} {'Load':<8} {'Endpoint':<10} {'Emissions':<15} {'Per Req':<12} {'RPS':<10} {'Avg Time':<12}")
    print(f"{'':15} {'':8} {'':10} {'(g CO2)':<15} {'(mg CO2)':<12} {'':10} {'(ms)':<12}")
    print("-" * 100)

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

    print("=" * 100)


def print_framework_summary(results: List[Dict]):
    """Print summary comparing all frameworks, with significance qualifiers."""

    grouped = group_by_criteria(results, "framework_key")

    print("\n" + "=" * 100)
    print("  FRAMEWORK SUMMARY (All Tests Combined)")
    print("=" * 100)
    print(f"\n{'Framework':<15} {'Tests':<8} {'Avg Emissions':<18} {'Per Request':<15} {'Avg RPS':<12} {'Avg Time':<12}")
    print(f"{'':15} {'':8} {'(g CO2)':<18} {'(mg CO2)':<15} {'':12} {'(ms)':<12}")
    print("-" * 100)

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

    print("=" * 100)

    # Winners — with statistical qualification when data allows
    if summaries:
        num_runs = _detect_num_runs(results)

        if num_runs >= 2 and HAS_SCIPY:
            rel_summary = build_reliability_summary(results)
            rel_counts = rel_summary["overall"]
            print("\n  WINNERS (statistically qualified):")
            for metric, desc in [
                ("emissions_g", "Lowest Total Emissions"),
                ("emissions_per_request_mg", "Lowest Per-Request Emissions"),
                ("rps", "Highest Throughput"),
                ("response_time_ms", "Fastest Response Time"),
            ]:
                fw_groups = _build_framework_metric_groups(results, metric)
                direction = METRIC_DIRECTION[metric]
                winner = determine_statistical_winner(fw_groups, metric, direction,
                                                      reliability_counts=rel_counts)
                print(f"  {desc}: {winner['statement']}")
        else:
            # Fallback: simple min/max (legacy behavior)
            print("\n  WINNERS:")
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
    """Analyze how each framework scales with load."""

    print("\n" + "=" * 100)
    print("  LOAD SCALING ANALYSIS")
    print("=" * 100)

    grouped_by_framework = group_by_criteria(results, "framework_key")

    for framework_key in sorted(grouped_by_framework.keys()):
        items = grouped_by_framework[framework_key]
        framework_name = items[0].get('framework', framework_key)

        grouped_by_load = group_by_criteria(items, "load_size")

        print(f"\n{framework_name}:")
        print(f"{'  Load':<10} {'Emissions (g)':<15} {'Per Req (mg)':<15} {'RPS':<12} {'Avg Time (ms)':<15}")
        print("  " + "-" * 65)

        for load in sorted(grouped_by_load.keys()):
            load_items = grouped_by_load[load]
            avg = calculate_averages(load_items)

            print(f"  {load:<10} {avg['avg_emissions_g']:<15.3f} "
                  f"{avg['avg_emissions_per_request_mg']:<15.3f} "
                  f"{avg['avg_rps']:<12.2f} {avg['avg_response_time_ms']:<15.2f}")


def print_endpoint_analysis(results: List[Dict]):
    """Analyze performance by endpoint type."""

    print("\n" + "=" * 100)
    print("  ENDPOINT TYPE ANALYSIS")
    print("=" * 100)

    grouped_by_endpoint = group_by_criteria(results, "endpoint_name")

    for endpoint in sorted(grouped_by_endpoint.keys()):
        items = grouped_by_endpoint[endpoint]
        print(f"\n{endpoint.upper()} Endpoint:")

        grouped_by_framework = group_by_criteria(items, "framework_key")

        print(f"{'  Framework':<15} {'Tests':<8} {'Avg Emissions':<15} {'Per Req':<12} {'RPS':<10}")
        print("  " + "-" * 60)

        for framework_key in sorted(grouped_by_framework.keys()):
            framework_items = grouped_by_framework[framework_key]
            framework_name = framework_items[0].get('framework', framework_key)
            avg = calculate_averages(framework_items)

            print(f"  {framework_name:<15} {avg['count']:<8} {avg['avg_emissions_g']:<15.3f} "
                  f"{avg['avg_emissions_per_request_mg']:<12.3f} {avg['avg_rps']:<10.2f}")


# ---------------------------------------------------------------------------
# Markdown report generation
# ---------------------------------------------------------------------------

def generate_markdown_report(results: List[Dict], output_file="test_results/REPORT.md"):
    """Generate a detailed markdown report with optional statistical sections."""

    num_runs = _detect_num_runs(results)

    with open(output_file, 'w') as f:
        f.write("# Carbon Footprint Comparison Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Total Test Results: {len(results)}\n\n")
        if num_runs >= 2:
            f.write(f"Independent Runs per Configuration: {num_runs}\n\n")

        # ---- Framework Summary ----
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

        # ---- Measurement Reliability ----
        rel_summary = build_reliability_summary(results)
        rel_overall = rel_summary["overall"]
        rel_total = sum(rel_overall.values())

        f.write("\n## Measurement Reliability\n\n")
        f.write("CodeCarbon's accuracy depends on test duration relative to its ~15-second sampling window.\n\n")
        f.write("### Reliability Classification\n\n")
        f.write("| Classification | Duration | Meaning |\n")
        f.write("|---------------|----------|--------|\n")
        f.write("| Reliable | >= 15s | At least one full CodeCarbon sampling window |\n")
        f.write("| Marginal | 5-15s | Partial sampling — energy values have higher uncertainty |\n")
        f.write("| Unreliable | < 5s | Below noise floor — energy comparisons are not meaningful |\n\n")

        f.write(f"**Overall**: {rel_overall['reliable']}/{rel_total} reliable, "
                f"{rel_overall['marginal']}/{rel_total} marginal, "
                f"{rel_overall['unreliable']}/{rel_total} unreliable\n\n")

        # Per-framework reliability table
        by_fw = rel_summary["by_framework"]
        if by_fw:
            f.write("### Per-Framework Reliability\n\n")
            f.write("| Framework | Reliable | Marginal | Unreliable |\n")
            f.write("|-----------|----------|----------|------------|\n")
            for fw_key in sorted(by_fw.keys()):
                counts = by_fw[fw_key]
                f.write(f"| {fw_key} | {counts['reliable']} | {counts['marginal']} | {counts['unreliable']} |\n")
            f.write("\n")

        # Measurement Limitations
        f.write("### Measurement Limitations\n\n")
        f.write("The following are known limitations of the energy measurement methodology:\n\n")
        f.write("1. **DRAM Energy Estimation**: CodeCarbon estimates RAM power using a constant "
                "(0.375 W/GB) based on total system RAM, not per-process DRAM usage. "
                "Memory-intensive frameworks (Java, Go) may have underestimated energy footprints. "
                "This is a platform limitation that cannot be fixed in software.\n")
        f.write("2. **System-Wide Tracking**: CodeCarbon uses machine-level tracking mode, which "
                "captures energy consumption from all processes on the system, not just the "
                "framework under test. Background processes contribute noise.\n")

        # Detect power method from results
        power_methods = set()
        for r in results:
            pm = r.get("energy_metadata", {}).get("power_measurement_method", "")
            if pm:
                power_methods.add(pm)
        if power_methods:
            method_str = "; ".join(sorted(power_methods))
            f.write(f"3. **Power Measurement Method**: Detected: {method_str}. "
                    "TDP-based estimation uses a constant CPU power value rather than actual "
                    "hardware counters (RAPL), which may not capture workload-dependent power variation.\n")
        f.write("\n")

        # ---- Statistical Summary (only if multiple runs) ----
        if num_runs >= 2 and HAS_SCIPY:
            f.write("\n## Statistical Summary\n\n")
            f.write(f"All statistical tests use **alpha = {ALPHA}** (95% confidence level).\n")
            f.write(f"Number of independent runs per configuration: **{num_runs}**\n\n")

            for metric in METRIC_EXTRACTORS:
                label = METRIC_LABELS[metric]
                direction = METRIC_DIRECTION[metric]
                fw_groups = _build_framework_metric_groups(results, metric)

                # 95% CI table
                f.write(f"### {label}\n\n")
                f.write("#### Descriptive Statistics (95% CI)\n\n")
                f.write("| Framework | n | Mean | Std Dev | 95% CI |\n")
                f.write("|-----------|---|------|---------|--------|\n")

                for fw_key in sorted(fw_groups.keys()):
                    vals = fw_groups[fw_key]
                    n = len(vals)
                    mean_val = statistics.mean(vals)
                    if n >= 2:
                        std_val = statistics.stdev(vals)
                        stderr = std_val / math.sqrt(n)
                        t_crit = sp_stats.t.ppf(1 - ALPHA / 2, df=n - 1)
                        ci_low = mean_val - t_crit * stderr
                        ci_high = mean_val + t_crit * stderr
                        f.write(f"| {fw_key} | {n} | {mean_val:.4f} | {std_val:.4f} | [{ci_low:.4f}, {ci_high:.4f}] |\n")
                    else:
                        f.write(f"| {fw_key} | {n} | {mean_val:.4f} | N/A | N/A |\n")

                # ANOVA
                anova = run_anova(fw_groups, metric)
                f.write("\n#### One-Way ANOVA\n\n")
                if "f_statistic" in anova and anova["f_statistic"] is not None:
                    sig_str = "Yes" if anova["significant"] else "No"
                    f.write(f"- **F-statistic**: {anova['f_statistic']}\n")
                    f.write(f"- **p-value**: {anova['p_value']}\n")
                    f.write(f"- **Significant at alpha={ALPHA}**: {sig_str}\n")
                elif "warning" in anova:
                    f.write(f"- {anova['warning']}\n")

                # Pairwise tests
                pairwise = run_pairwise_tests(fw_groups, metric)
                if pairwise:
                    f.write(f"\n#### Pairwise Welch's t-tests (Bonferroni-corrected, {len(pairwise)} comparisons)\n\n")
                    f.write("| Pair | Mean A | Mean B | p (corrected) | Cohen's d | Effect Size | Significant? |\n")
                    f.write("|------|--------|--------|---------------|-----------|-------------|-------------|\n")
                    for pw in pairwise:
                        if "warning" in pw:
                            f.write(f"| {pw['fw_a']} vs {pw['fw_b']} | — | — | — | — | {pw['warning']} | — |\n")
                            continue
                        sig = "Yes" if pw["significant"] else "No"
                        f.write(f"| {pw['fw_a']} vs {pw['fw_b']} | {pw['mean_a']:.4f} | {pw['mean_b']:.4f} | "
                                f"{pw['p_corrected']:.6f} | {pw['cohens_d']:.4f} | {pw['effect_size']} | {sig} |\n")

                # Winner
                winner = determine_statistical_winner(fw_groups, metric, direction,
                                                      reliability_counts=rel_overall)
                f.write(f"\n**Winner**: {winner['statement']}\n\n")

        # ---- Detailed Results ----
        f.write("\n## Detailed Results\n\n")
        f.write("| Framework | Load | Endpoint | Emissions (g) | Per Req (mg) | RPS | Mean Time (ms) |")
        if num_runs >= 2:
            f.write(" Run |")
        f.write("\n")
        f.write("|-----------|------|----------|---------------|--------------|-----|----------------|")
        if num_runs >= 2:
            f.write("-----|")
        f.write("\n")

        for result in sorted(results, key=lambda x: (
            x.get('framework', ''), x.get('load_size', 0),
            x.get('endpoint_name', ''), x.get('run_id', 0)
        )):
            f.write(f"| {result.get('framework', 'N/A')} | {result.get('load_size', 0)} | "
                    f"{result.get('endpoint_name', 'N/A')} | {result.get('emissions_g', 0):.3f} | "
                    f"{result.get('avg_emissions_per_request_mg', 0):.3f} | "
                    f"{result.get('requests_per_second', 0):.2f} | "
                    f"{result.get('response_time_stats', {}).get('mean_ms', 0):.2f} |")
            if num_runs >= 2:
                f.write(f" {result.get('run_id', '-')} |")
            f.write("\n")

        # ---- Key Findings ----
        f.write("\n## Key Findings\n\n")

        grouped = group_by_criteria(results, "framework_key")
        summaries = []
        for framework_key in grouped.keys():
            items = grouped[framework_key]
            framework_name = items[0].get('framework', framework_key)
            avg = calculate_averages(items)
            summaries.append({"name": framework_name, "key": framework_key, **avg})

        if summaries:
            if num_runs >= 2 and HAS_SCIPY:
                for metric, desc in [
                    ("emissions_g", "Most Energy Efficient"),
                    ("rps", "Highest Throughput"),
                ]:
                    fw_groups = _build_framework_metric_groups(results, metric)
                    direction = METRIC_DIRECTION[metric]
                    winner = determine_statistical_winner(fw_groups, metric, direction,
                                                          reliability_counts=rel_overall)
                    f.write(f"- **{desc}**: {winner['statement']}\n")
            else:
                min_emissions = min(summaries, key=lambda x: x['avg_emissions_g'])
                max_rps = max(summaries, key=lambda x: x['avg_rps'])
                f.write(f"- **Most Energy Efficient**: {min_emissions['name']} "
                        f"({min_emissions['avg_emissions_g']:.3f}g CO2 average)\n")
                f.write(f"- **Highest Throughput**: {max_rps['name']} "
                        f"({max_rps['avg_rps']:.2f} requests/second)\n")

        # ---- Methodology notes ----
        if num_runs >= 2 and HAS_SCIPY:
            f.write("\n## Statistical Methodology\n\n")
            f.write("- **Repetitions**: Each framework/load/endpoint configuration was tested "
                    f"{num_runs} independent times using round-robin ordering to reduce temporal correlation.\n")
            f.write(f"- **Significance Level**: alpha = {ALPHA} (95% confidence)\n")
            f.write("- **Confidence Intervals**: 95% CIs computed using the t-distribution.\n")
            f.write("- **Omnibus Test**: One-way ANOVA (F-test) to detect any differences across frameworks.\n")
            f.write("- **Pairwise Tests**: Welch's t-test (unequal variances assumed) for all framework pairs.\n")
            f.write("- **Multiple Comparisons Correction**: Bonferroni (p_corrected = p_raw * num_comparisons).\n")
            f.write("- **Effect Size**: Cohen's d with pooled standard deviation; "
                    "classified as negligible (<0.2), small (0.2-0.5), medium (0.5-0.8), or large (>0.8).\n")
            f.write("- **Measurement Reliability**: Each test is classified as reliable (>=15s), "
                    "marginal (5-15s), or unreliable (<5s) based on duration relative to "
                    "CodeCarbon's sampling window. Winner statements include caveats when "
                    "unreliable measurements are present.\n")

    print(f"\n  Markdown report saved to: {output_file}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Main analysis function."""
    print("\n" + "=" * 100)
    print("CARBON FOOTPRINT ANALYSIS REPORT")
    print("=" * 100)

    results = load_test_results()

    if not results:
        print("\n  No test results found in test_results/ directory")
        print("   Run tests first using: python test_carbon_comprehensive.py --suite")
        return

    num_runs = _detect_num_runs(results)
    print(f"\n  Loaded {len(results)} test results (detected {num_runs} run(s) per config)")

    # Measurement reliability assessment
    print_reliability_summary(results)

    # Generate various analysis reports
    print_comparison_table(results)
    print_framework_summary(results)
    print_load_analysis(results)
    print_endpoint_analysis(results)

    # Statistical analysis (only when multiple runs available)
    if num_runs >= 2:
        if HAS_SCIPY:
            print_statistical_summary(results)
            print_per_config_statistical_analysis(results)
        else:
            print("\n  WARNING: scipy is not installed. Statistical analysis requires scipy.")
            print("   Install with: pip install scipy numpy")
    else:
        print("\n  NOTE: Only 1 run per configuration detected — statistical analysis skipped.")
        print("   To enable statistical significance testing, re-run benchmarks with:")
        print("     python test_carbon_comprehensive.py --suite -r 5")

    # Generate markdown report
    generate_markdown_report(results)

    print("\n" + "=" * 100)
    print("  ANALYSIS COMPLETE")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    main()
