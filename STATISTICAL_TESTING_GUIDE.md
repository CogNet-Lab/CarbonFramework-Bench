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
