# Statistical Significance Testing Guide

This document explains the statistical significance testing feature added to CarbonFramework-Bench and provides step-by-step instructions for running benchmarks with statistical rigor.

## What Changed

### Problem

Previously, the benchmarking framework ran each configuration exactly once and picked "winners" by simple min/max of point estimates. This meant claims like "Django achieves the lowest emissions" had **no statistical evidence** — a single measurement can easily be an outlier due to CPU thermal state, background processes, or network jitter.

Additionally, a **duplicate-counting bug** in `analyze_results.py` caused each result to appear twice in the analysis (once from individual JSON files and once from the combined `comparison_suite_*.json` file).

### Solution

The following capabilities were added:

1. **Multiple independent runs** (`--runs/-r N` flag) with round-robin ordering
2. **Descriptive statistics** with 95% confidence intervals (t-distribution)
3. **One-way ANOVA** to detect if any framework differs significantly
4. **Pairwise Welch's t-tests** with Bonferroni correction for all framework pairs
5. **Cohen's d effect sizes** (negligible / small / medium / large)
6. **Significance-qualified winner statements** — `[SIG]` or `[N.S.]` markers
7. **Bug fix**: `comparison_suite_*.json` files are now skipped during analysis to prevent duplicate counting

### Files Modified

| File | Changes |
|------|---------|
| `requirements.txt` | Added `scipy>=1.10.0` and `numpy>=1.24.0` |
| `scripts/test_carbon_comprehensive.py` | Added `--runs/-r` flag, `run_id` tracking, round-robin suite ordering |
| `scripts/analyze_results.py` | Fixed duplicate bug, added all statistical analysis functions and report sections |
| `scripts/quick_test.py` | Added `runs` passthrough argument |
| `CLAUDE.md` | Updated documentation for new features |

## Step-by-Step Execution

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs `scipy` and `numpy` in addition to existing dependencies.

### Step 2: Start Framework Services

Start all frameworks you want to benchmark:

```bash
# Start all frameworks (from repo root)
cd fastapi-carbon-test && docker-compose up -d --build && cd ..
cd django-carbon-test && docker-compose up -d --build && cd ..
cd springboot-carbon-test && docker-compose up -d --build && cd ..
cd micronaut-carbon-test && docker-compose up -d --build && cd ..
cd gin-carbon-test && docker-compose up -d --build && cd ..
cd chi-carbon-test && docker-compose up -d --build && cd ..

# Verify all containers are running
docker ps    # Expect 12 containers (6 apps + 6 dbs)
```

### Step 3: Run Benchmarks with Multiple Runs

```bash
cd scripts
```

**Option A: Full suite (recommended for publication)**
```bash
# 5 runs per config (default) — 270 tests, ~5-10 hours
python test_carbon_comprehensive.py --suite

# Or explicitly set run count
python test_carbon_comprehensive.py --suite -r 5
```

**Option B: Quicker suite (minimum for significance)**
```bash
# 3 runs per config — 162 tests, ~3-6 hours
python test_carbon_comprehensive.py --suite -r 3
```

**Option C: Test a single framework first**
```bash
# Quick validation: 1 framework, 1 config, 3 runs
python test_carbon_comprehensive.py -f fastapi -l 100 -e light -r 3

# Or using the convenience wrapper
python quick_test.py fastapi 100 light 3
```

**Option D: Single run (legacy behavior, no statistics)**
```bash
python test_carbon_comprehensive.py --suite -r 1
```

### Step 4: Analyze Results

```bash
python analyze_results.py
```

This will print:
1. **Comparison tables** — raw results grouped by framework
2. **Framework summary** — averages across all tests
3. **Load scaling analysis** — how each framework scales
4. **Endpoint analysis** — performance by endpoint type
5. **Statistical summary** (when >= 2 runs detected):
   - Descriptive statistics with 95% CIs per framework per metric
   - One-Way ANOVA results per metric
   - Pairwise Welch's t-tests with Bonferroni correction
   - Cohen's d effect sizes
   - Significance-qualified winner statements
6. **Per-configuration analysis** — ANOVA + winners per (load, endpoint) pair
7. **Markdown report** — saved to `test_results/REPORT.md`

### Step 5: Review the Report

```bash
# View the generated report
cat test_results/REPORT.md
```

The report includes (when multiple runs are present):
- Framework summary table
- Statistical Summary section with CI tables, ANOVA, and pairwise tests for each metric
- Detailed per-test results (with run IDs)
- Significance-qualified Key Findings
- Statistical Methodology notes

## Understanding the Output

### Winner Qualifiers

- **`[SIG]`** — The winner is statistically significantly better than the runner-up (p < 0.05 after Bonferroni correction). You can confidently claim this framework performs better.
- **`[N.S.]`** — Not statistically significant. The observed difference could be due to random variation. You should NOT claim one framework is better than another.

### ANOVA Results

- **Significant ANOVA** (p < 0.05) means at least one framework differs from the others. Check pairwise tests to see which pairs differ.
- **Non-significant ANOVA** means no detectable difference between any frameworks for that metric.

### Cohen's d Effect Sizes

| d value | Classification | Interpretation |
|---------|---------------|----------------|
| < 0.2 | Negligible | Practically no difference |
| 0.2-0.5 | Small | Minor difference |
| 0.5-0.8 | Medium | Moderate difference |
| > 0.8 | Large | Substantial difference |

### Confidence Intervals

The 95% CI means: if we repeated the entire experiment many times, 95% of the calculated intervals would contain the true mean. Overlapping CIs between frameworks suggest the difference may not be significant.

## Backward Compatibility

- **Old results** (without `run_id`): Still load and analyze correctly. Statistical sections are skipped, and the old-style report is generated.
- **Existing CLI usage**: All existing commands work identically. `--runs` defaults to 5 for `--suite` and 1 for single tests.
- **`calculate_averages()`**: Still works and returns the same fields as before, plus additional `stat_*` fields when n >= 2.
- **Without scipy**: If scipy is not installed, all statistical analysis is gracefully skipped with a warning message.

## Round-Robin Ordering

The suite uses round-robin ordering instead of running all runs of one config consecutively:

```
Round 1: fastapi/100/light → fastapi/100/medium → ... → chi/10000/heavy
Round 2: fastapi/100/light → fastapi/100/medium → ... → chi/10000/heavy
Round 3: ...
```

This design spreads measurements across time so that temporal factors (CPU thermal state, background processes, network conditions) affect all frameworks equally, making the independence assumption required by ANOVA and t-tests more defensible.

## Recommended Run Counts

| Purpose | Runs | Total Tests | Est. Time |
|---------|------|-------------|-----------|
| Quick validation | 1 | 54 | ~1-2 hours |
| Minimum significance | 3 | 162 | ~3-6 hours |
| Recommended | 5 | 270 | ~5-10 hours |
| High confidence | 10 | 540 | ~10-20 hours |

## Measurement Reliability

### The Problem

A reviewer identified three concerns about the energy measurement methodology:

1. **Unreported tracking mode**: CodeCarbon can use RAPL (hardware counters) or TDP (software estimation) for power measurement. The method significantly affects accuracy, but previously no metadata was captured — only the final `emissions_kg` float.

2. **Noise floor for small tests**: CodeCarbon samples energy at ~15-second intervals. Tests completing in <5 seconds (e.g., 100-request light tests at ~1.8s) fall below this sampling window, producing unreliable energy readings. Some tests returned `emissions_kg ≈ 0`.

3. **Missing DRAM energy**: CodeCarbon estimates RAM power using a constant (0.375 W/GB) based on total system RAM, not per-process DRAM usage. Memory-intensive frameworks (Java/Go with larger runtimes) may have underestimated energy footprints. This is a hardware/platform limitation that cannot be fixed in software.

### What Was Done

**Concern 1 — Energy metadata capture**: Each test now extracts rich metadata from CodeCarbon's CSV immediately after `tracker.stop()` (before the next test overwrites it). The JSON result includes an `energy_metadata` dict with:
- `tracking_mode` (e.g., "machine" for system-wide tracking)
- `power_measurement_method` ("TDP-based" or "Hardware-based (RAPL/powermetrics)")
- Energy breakdown: `cpu_energy_kwh`, `gpu_energy_kwh`, `ram_energy_kwh`
- Hardware info: `cpu_model`, `cpu_count`, `ram_total_size_gb`
- CodeCarbon version, OS, region

**Concern 2 — Reliability classification**: Each test is classified based on duration:

| Classification | Duration | Meaning |
|---------------|----------|---------|
| **Reliable** | >= 15s | At least one full CodeCarbon sampling window |
| **Marginal** | 5–15s | Partial sampling — higher uncertainty |
| **Unreliable** | < 5s | Below noise floor — energy values are not meaningful |

Warnings are printed to the console for unreliable/marginal tests. The analysis report includes a "Measurement Reliability" section with per-framework breakdowns. Winner statements include `[CAVEAT]` annotations when unreliable measurements are present.

**Concern 3 — DRAM limitation**: Documented in the analysis report's "Measurement Limitations" section. This cannot be fixed in software — it requires hardware-level DRAM energy monitoring (e.g., Intel RAPL DRAM domain), which is not available on all platforms.

### The `--min-duration` Flag

To ensure reliable energy measurements for short tests, use `--min-duration`:

```bash
# Pad tests to at least 15 seconds
python test_carbon_comprehensive.py -f fastapi -l 100 -e light --min-duration 15

# Full suite with reliable measurements
python test_carbon_comprehensive.py --suite --min-duration 15

# Via quick_test.py
python quick_test.py fastapi 100 light 1 --min-duration 15
```

When the load test finishes in less than `--min-duration` seconds, the tracker continues running (with `time.sleep()`) until the minimum is reached. This ensures CodeCarbon captures at least one full sampling window. The padding time is recorded in the result JSON as `padding_seconds`.

**Default**: `--min-duration 0` (no padding — preserves existing behavior).

**Recommendation**: Use `--min-duration 15` for any test configuration where the load completes in under 15 seconds (typically 100-request and 1000-request tests with light/medium endpoints).

### Known Limitations

These limitations are inherent to the measurement platform and are documented in the generated report:

1. **DRAM energy is estimated, not measured**: RAM power = 0.375 W/GB * total system RAM. Not per-process. Java and Go frameworks with larger runtime memory footprints may have underestimated energy consumption.
2. **System-wide tracking**: CodeCarbon uses machine-level tracking, capturing energy from all processes — not just the framework under test. Background process energy is included as noise.
3. **TDP-based power on macOS/non-RAPL systems**: On systems without Intel RAPL (e.g., Apple Silicon), CodeCarbon uses TDP (Thermal Design Power) as a constant power estimate. This does not capture workload-dependent power variation.
4. **CSV overwrite**: CodeCarbon CSV filenames use `test_id` without run_id, so multiple runs overwrite the same file. Metadata is extracted immediately after each `tracker.stop()` to avoid data loss.

## Container Resource Metrics

### Overview

In addition to energy and performance metrics, the framework now captures container-level CPU and memory usage during each load test, and supports separate container cold-start time measurement.

### Metrics Collected

| Metric | Source | Description |
|--------|--------|-------------|
| **Avg Container CPU (%)** | `docker stats` polling | Mean CPU utilization during load phase |
| **Peak Container CPU (%)** | `docker stats` polling | Maximum CPU sample during load phase |
| **Avg Container Memory (MB)** | `docker stats` polling | Mean memory usage during load phase |
| **Peak Container Memory (MB)** | `docker stats` polling | Maximum memory sample during load phase |
| **Baseline Memory (MB)** | `docker stats` first sample | Memory at start of load (pre-load footprint) |
| **Startup Time (s)** | Health endpoint polling | Time from `docker start` to first successful health response |

### How They're Collected

**Container monitoring** uses a `ContainerMonitor` class that runs `docker stats --no-stream` in a background thread at 1-second intervals. Key design decisions:

- **App container only**: The PostgreSQL instance is identical across all frameworks, so database metrics add noise without analytical value. Only the framework app container is monitored.
- **Load phase only**: The monitor starts immediately before the load test and stops immediately after, before any `--min-duration` padding sleep. This ensures metrics reflect actual workload resource usage, not idle time.
- **No new dependencies**: Uses only Python stdlib (`threading`, `subprocess`) and the Docker CLI that's already required by the project.

**Startup time** is measured separately via `--measure-startup`:
1. `docker stop` the app container
2. Wait 2s for full stop
3. `docker start` and record start time
4. Poll health endpoint every 0.5s until 200 response
5. Startup time = elapsed time from step 3 to step 4

### Statistical Treatment

Container resource metrics (CPU%, Memory) are treated as additional metrics in the analysis pipeline:

- **Descriptive statistics**: Mean, std dev, 95% CIs per framework (same as emissions/RPS)
- **ANOVA**: One-way ANOVA across frameworks to detect differences
- **Pairwise tests**: Welch's t-tests with Bonferroni correction
- **Effect sizes**: Cohen's d with the same classification thresholds
- **Winners**: Significance-qualified (`[SIG]`/`[N.S.]`) — lower is better for both CPU% and memory

Startup times are analyzed separately (from `startup_times_*.json` files) with mean/std/min/max per framework.

### Backward Compatibility

Old result files without `container_metrics` are handled gracefully:
- The metric extractors return `None` for missing container metrics
- `_extract_metric_values()` filters out `None` values
- Analysis sections are gated on data availability (skip if no container data)
- Console tables show "N/A" for missing values

### Commands

```bash
# Container metrics are collected automatically during load tests
python test_carbon_comprehensive.py -f fastapi -l 100 -e light

# Measure startup times (restarts containers!)
python test_carbon_comprehensive.py --measure-startup
python test_carbon_comprehensive.py --measure-startup -f fastapi --startup-runs 5

# Via quick_test.py
python quick_test.py --startup
python quick_test.py --startup fastapi
```
