# 🚀 Getting Started - Carbon Footprint Framework Comparison

## What Has Been Created

I've built a complete carbon footprint testing infrastructure for 6 web frameworks:

### ✅ Frameworks Implemented
1. **FastAPI** (Python) - Port 8000
2. **Django** (Python) - Port 8001  
3. **Spring Boot** (Java) - Port 8002
4. **Micronaut** (Java) - Port 8003
5. **Gin** (Go) - Port 8004
6. **Chi** (Go) - Port 8005

All frameworks implement **identical APIs** with:
- Health check endpoint
- Light/Medium/Heavy analytics endpoints (CPU-intensive)
- I/O-bound endpoints
- Database operations (PostgreSQL)

## 📦 What You Need to Install

```powershell
# Install CodeCarbon and requests for testing
pip install codecarbon requests
```

## 🎯 Step-by-Step Guide

### Step 1: Start All Frameworks

```powershell
# Option A: Use the automated script
.\start-all.ps1

# Option B: Start manually (example for one framework)
cd fastapi-carbon-test
docker-compose up -d --build
cd ..
```

This will:
- Build Docker images for each framework
- Start PostgreSQL databases (separate for each)
- Start application containers
- Initialize databases with shared schema

### Step 2: Verify Services are Running

```powershell
# Check all containers
docker ps

# Should see 12 containers (6 apps + 6 databases)
```

Test health endpoints:
```powershell
# Test FastAPI
curl http://localhost:8000/api/v1/health

# Test Django  
curl http://localhost:8001/api/v1/health

# Test Spring Boot
curl http://localhost:8002/api/v1/health

# Test Micronaut
curl http://localhost:8003/api/v1/health

# Test Gin
curl http://localhost:8004/api/v1/health

# Test Chi
curl http://localhost:8005/api/v1/health
```

### Step 3: Run Tests

Navigate to scripts directory:
```powershell
cd scripts
```

#### Option A: Run Full Test Suite (Recommended)
Tests all frameworks with all load levels (100, 1000, 10000) and all endpoints:

```powershell
python test_carbon_comprehensive.py --suite
```

⏰ **This will take a while** (approximately 15-30 minutes for all combinations)

#### Option B: Run Quick Tests

Single framework test:
```powershell
# FastAPI with 100 requests on light endpoint
python quick_test.py fastapi

# Django with 1000 requests on light endpoint  
python quick_test.py django 1000

# Gin with 10000 requests on heavy endpoint
python quick_test.py gin 10000 heavy
```

#### Option C: Run Specific Tests

```powershell
# Specific framework + load + endpoint
python test_carbon_comprehensive.py -f fastapi -l 100 -e light
python test_carbon_comprehensive.py -f springboot -l 1000 -e medium
python test_carbon_comprehensive.py -f gin -l 10000 -e heavy
```

### Step 4: Analyze Results

After running tests:

```powershell
python analyze_results.py
```

This generates:
- **Console output** with comprehensive tables and comparisons
- **test_results/REPORT.md** - Markdown report you can share

## 📊 Understanding the Results

### Metrics Collected

1. **Carbon Emissions**
   - Total emissions in grams (g CO2)
   - Per-request emissions in milligrams (mg CO2)

2. **Performance**
   - Requests per second (RPS/throughput)
   - Response times (min, mean, median, p95, p99, max)
   - Success/error rates

3. **Analysis**
   - Framework comparison
   - Load scaling behavior
   - Endpoint type performance

### Test Files Location

Results are saved in `test_results/`:
- `{framework}_{endpoint}_{load}_{timestamp}.json` - Individual tests
- `comparison_suite_{timestamp}.json` - Full suite results
- `codecarbon_*.csv` - Raw CodeCarbon data
- `REPORT.md` - Markdown analysis report

## 🎨 Example Test Scenarios

### Scenario 1: Compare All Frameworks (Light Load)
```powershell
# Test each framework with 100 requests
python test_carbon_comprehensive.py -f fastapi -l 100 -e light
python test_carbon_comprehensive.py -f django -l 100 -e light
python test_carbon_comprehensive.py -f springboot -l 100 -e light
python test_carbon_comprehensive.py -f micronaut -l 100 -e light
python test_carbon_comprehensive.py -f gin -l 100 -e light
python test_carbon_comprehensive.py -f chi -l 100 -e light

# Analyze
python analyze_results.py
```

### Scenario 2: Test Single Framework Under Different Loads
```powershell
# Test FastAPI with increasing loads
python test_carbon_comprehensive.py -f fastapi -l 100 -e medium
python test_carbon_comprehensive.py -f fastapi -l 1000 -e medium
python test_carbon_comprehensive.py -f fastapi -l 10000 -e medium

python analyze_results.py
```

### Scenario 3: Compare Endpoint Types
```powershell
# Test different workload types on Gin
python test_carbon_comprehensive.py -f gin -l 1000 -e light
python test_carbon_comprehensive.py -f gin -l 1000 -e medium
python test_carbon_comprehensive.py -f gin -l 1000 -e heavy

python analyze_results.py
```

## 🛠️ Troubleshooting

### Services Won't Start

```powershell
# Check logs
cd {framework}-carbon-test
docker-compose logs -f

# Rebuild
docker-compose down -v
docker-compose up -d --build
```

### Port Conflicts

Edit `docker-compose.yml` in each framework folder to change ports.

### Go Modules (Gin/Chi)

If Go modules fail to download:
```powershell
cd gin-carbon-test
# or cd chi-carbon-test

# Run go mod tidy in container
docker-compose run app go mod tidy
docker-compose up -d --build
```

### Java Build Issues (Spring Boot/Micronaut)

```powershell
# Clean rebuild
docker-compose down -v
docker system prune -f
docker-compose up -d --build
```

## 🧹 Cleanup

### Stop All Services
```powershell
.\stop-all.ps1
```

### Remove All Data
```powershell
# Stop and remove volumes
cd fastapi-carbon-test && docker-compose down -v && cd ..
cd django-carbon-test && docker-compose down -v && cd ..
cd springboot-carbon-test && docker-compose down -v && cd ..
cd micronaut-carbon-test && docker-compose down -v && cd ..
cd gin-carbon-test && docker-compose down -v && cd ..
cd chi-carbon-test && docker-compose down -v && cd ..
```

## 📈 What to Expect

### Test Duration
- **100 requests**: ~10-30 seconds per test
- **1,000 requests**: ~1-3 minutes per test
- **10,000 requests**: ~5-15 minutes per test

### Full Suite
- **54 total tests** (6 frameworks × 3 loads × 3 endpoints)
- **Total time**: 1-2 hours

### Results Insight
You'll discover:
- Which framework is most energy-efficient
- How frameworks scale with load
- Performance vs. carbon footprint trade-offs
- Best framework for your use case

## 🎯 Next Steps

1. ✅ Start all frameworks: `.\start-all.ps1`
2. ✅ Run a quick test: `cd scripts && python quick_test.py fastapi`
3. ✅ Run full suite: `python test_carbon_comprehensive.py --suite`
4. ✅ Analyze results: `python analyze_results.py`
5. ✅ Review: `cat test_results/REPORT.md`

## 📚 Additional Resources

- Check `README.md` for detailed documentation
- View logs: `docker-compose logs -f app`
- Test individual endpoints manually: See README.md API section

## 💡 Tips

1. **Start Small**: Test with 100 requests first
2. **Wait Between Tests**: Give services 5-10 seconds between tests
3. **Monitor Resources**: Use `docker stats` to watch resource usage
4. **Save Results**: Results are cumulative - analyze anytime
5. **Compare Iteratively**: Test 2-3 frameworks at a time for easier comparison

---

Happy Testing! 🌱
