# CarbonFramework-Bench: A Comprehensive Web Framework Carbon Footprint Benchmarking Tool

A research-grade framework for measuring and comparing the carbon emissions of popular web frameworks under standardized load conditions. It is designed for academic research, sustainable software engineering evaluation, and fair comparison of framework energy efficiency across multiple programming language ecosystems.

## Features

### Supported Web Frameworks
| Framework | Language | Runtime | Server | Database Driver |
|-----------|----------|---------|--------|-----------------|
| **FastAPI** | Python 3.11 | Uvicorn (ASGI) | Async | asyncpg |
| **Django** | Python 3.x | Gunicorn (WSGI) | Sync | psycopg2 |
| **Spring Boot** | Java 17 | Embedded Tomcat | Spring WebFlux | Spring Data JPA |
| **Micronaut** | Java 17 | Netty | Reactive | Micronaut Data JDBC |
| **Gin** | Go | Native | Goroutines | database/sql + pq |
| **Chi** | Go | Native | Goroutines | database/sql + pq |

### Benchmark Endpoints
| Endpoint | Type | Description | Parameters |
|----------|------|-------------|------------|
| `/api/v1/weather/analytics/light` | CPU-bound | Simple array computation | - |
| `/api/v1/weather/analytics/medium` | CPU-bound | Moderate computation | `size=2000`, `iterations=3` |
| `/api/v1/weather/analytics/heavy` | CPU-bound | Intensive computation | `size=5000`, `iterations=5` |
| `/api/v1/weather/external` | I/O-bound | Simulated external delay | `delay_ms=100` |
| `/api/v1/weather/fetch` | I/O-bound | External API call | `city=Colombo` |
| `/api/v1/db/users` (GET) | Database | Read all users | - |
| `/api/v1/db/users` (POST) | Database | Create a user | `name`, `email` |

### Load Configurations
| Load Level | Requests | Execution Mode | Concurrency |
|------------|----------|----------------|-------------|
| **Light** | 100 | Sequential | 1 |
| **Medium** | 1,000 | Concurrent | Up to 100 workers |
| **Heavy** | 10,000 | Concurrent | Up to 100 workers |

---

## Evaluation Metrics

This framework provides a comprehensive set of metrics to evaluate framework performance and environmental impact.

#### **Carbon Metrics**
- **Total Emissions** (g CO2) - Total carbon emissions during test execution
- **Per-Request Emissions** (mg CO2) - Average emissions per individual request

#### **Performance Metrics**
- **Latency Percentiles** (min, mean, median, p95, p99, max) in milliseconds
- **QPS** (Queries Per Second / Requests Per Second)
- **Success Rate** (%) - Ratio of successful to total requests

#### **Resource Metrics**
- **Container CPU Utilization** (%) — Average and peak CPU during load test (via `docker stats`)
- **Container Memory Usage** (MB) — Average, peak, and baseline memory during load test
- **Startup Time** (seconds) — Cold-start time from container start to first health response

#### **Analysis Dimensions**
- **Framework Comparison** - Side-by-side ranking of all frameworks
- **Load Scaling Analysis** - How each framework scales from 100 to 10,000 requests
- **Endpoint Type Analysis** - Performance breakdown by workload type (light/medium/heavy)

---

## Installation

### Prerequisites

- Docker & Docker Compose
- Python 3.8+

### Setup

```bash
# Clone repository and navigate into it
git clone https://github.com/CogNet-Lab/CarbonFramework-Bench.git
cd CarbonFramework-Bench

# Install test dependencies
pip install -r requirements.txt
```

### Build and Start All Framework Services

```bash
# Start all frameworks (each in its own Docker container with dedicated PostgreSQL)
cd fastapi-carbon-test && docker-compose up -d --build && cd ..
cd django-carbon-test && docker-compose up -d --build && cd ..
cd springboot-carbon-test && docker-compose up -d --build && cd ..
cd micronaut-carbon-test && docker-compose up -d --build && cd ..
cd gin-carbon-test && docker-compose up -d --build && cd ..
cd chi-carbon-test && docker-compose up -d --build && cd ..

# Or on Windows PowerShell
.\start-all.ps1
```

### Verify Services

```bash
# Expect 12 containers (6 apps + 6 databases)
docker ps

# Test health endpoints
curl http://localhost:8000/api/v1/health  # FastAPI
curl http://localhost:8001/api/v1/health  # Django
curl http://localhost:8002/api/v1/health  # Spring Boot
curl http://localhost:8003/api/v1/health  # Micronaut
curl http://localhost:8004/api/v1/health  # Gin
curl http://localhost:8005/api/v1/health  # Chi
```

---

## Quick Start

### 1. Run a Quick Test

```bash
cd scripts

# Quick test on a single framework (defaults: 100 requests, light endpoint)
python quick_test.py fastapi

# With custom load and endpoint
python quick_test.py gin 1000 heavy
```

### 2. Run the Full Benchmark Suite

The full suite runs 6 frameworks x 3 loads x 3 endpoints = **54 tests**.

```bash
cd scripts
python test_carbon_comprehensive.py --suite
```

### 3. Run a Specific Test

```bash
cd scripts

# Specify framework, load size, and endpoint
python test_carbon_comprehensive.py -f fastapi -l 100 -e light
python test_carbon_comprehensive.py -f springboot -l 1000 -e medium
python test_carbon_comprehensive.py -f gin -l 10000 -e heavy
```

### 4. Analyze Results

```bash
cd scripts
python analyze_results.py
```

This generates:
- Console output with comparison tables and winner analysis
- `test_results/REPORT.md` - Markdown report

---

## Configuration

### Framework Configuration

Framework ports and metadata are defined in the `FRAMEWORKS` dict in `scripts/test_carbon_comprehensive.py`:

```python
FRAMEWORKS = {
    "fastapi":     {"port": 8000, "name": "FastAPI",      "folder": "fastapi-carbon-test"},
    "django":      {"port": 8001, "name": "Django",        "folder": "django-carbon-test"},
    "springboot":  {"port": 8002, "name": "Spring Boot",   "folder": "springboot-carbon-test"},
    "micronaut":   {"port": 8003, "name": "Micronaut",     "folder": "micronaut-carbon-test"},
    "gin":         {"port": 8004, "name": "Gin",           "folder": "gin-carbon-test"},
    "chi":         {"port": 8005, "name": "Chi",           "folder": "chi-carbon-test"},
}
```

### Test Parameters

```python
TEST_LOADS = [100, 1000, 10000]

ENDPOINTS = {
    "light":  "/api/v1/weather/analytics/light",
    "medium": "/api/v1/weather/analytics/medium",
    "heavy":  "/api/v1/weather/analytics/heavy",
}
```

### Docker Compose (per-framework)

Each framework directory contains a `docker-compose.yml` that orchestrates:
- An application container (framework-specific runtime)
- A dedicated PostgreSQL 15 instance (isolated per framework)
- Volume-mounted `init.sql` for consistent database schema
- Health checks for both app and database services

### Port Mapping

| Framework | App Port | Database Port |
|-----------|----------|---------------|
| FastAPI | 8000 | 5432 |
| Django | 8001 | 5433 |
| Spring Boot | 8002 | 5434 |
| Micronaut | 8003 | 5435 |
| Gin | 8004 | 5436 |
| Chi | 8005 | 5437 |

---

## Output Formats

### JSON Results (per test)

```json
{
  "framework": "FastAPI",
  "framework_key": "fastapi",
  "load_size": 1000,
  "endpoint_name": "light",
  "endpoint_path": "/api/v1/weather/analytics/light",
  "timestamp": "2026-01-15T10:30:00",
  "duration_seconds": 12.34,
  "emissions_kg": 0.005123,
  "emissions_g": 5.123,
  "success_count": 1000,
  "error_count": 0,
  "success_rate": 100.0,
  "requests_per_second": 81.04,
  "avg_emissions_per_request_mg": 5.123,
  "response_time_stats": {
    "min_ms": 10.5,
    "max_ms": 245.2,
    "mean_ms": 12.35,
    "median_ms": 11.8,
    "p95_ms": 18.4,
    "p99_ms": 22.1
  },
  "container_metrics": {
    "container_name": "fastapi-carbon-test-app-1",
    "sample_count": 12,
    "cpu_percent_avg": 15.3,
    "cpu_percent_max": 42.1,
    "memory_mb_avg": 156.3,
    "memory_mb_max": 210.5,
    "memory_mb_baseline": 120.0
  }
}
```

### Markdown Report (`test_results/REPORT.md`)

The generated report includes:
- **Framework Summary** table with averaged metrics across all tests
- **Detailed Results** table with every individual test result
- **Key Findings** with winners for energy efficiency and throughput

### CodeCarbon CSV

Raw energy consumption data from CodeCarbon is saved as `test_results/codecarbon_*.csv` for further analysis.

### Result File Naming

```
test_results/
├── {framework}_{endpoint}_{load}_{timestamp}.json    # Individual tests
├── comparison_suite_{timestamp}.json                  # Full suite aggregate
├── startup_times_{timestamp}.json                     # Startup time measurements
├── codecarbon_{framework}_{endpoint}_{load}.csv       # Raw CodeCarbon data
└── REPORT.md                                          # Generated analysis
```

---

## Project Structure

```
CarbonFramework-Bench/
├── fastapi-carbon-test/            # FastAPI (Python) implementation
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── app.py                      # Application source
│   └── requirements.txt
├── django-carbon-test/             # Django (Python) implementation
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── api/                        # Django app with views.py
├── springboot-carbon-test/         # Spring Boot (Java) implementation
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── pom.xml                     # Maven build
├── micronaut-carbon-test/          # Micronaut (Java) implementation
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── build.gradle                # Gradle build
├── gin-carbon-test/                # Gin (Go) implementation
│   ├── Dockerfile                  # Multi-stage build
│   ├── docker-compose.yml
│   └── go.mod
├── chi-carbon-test/                # Chi (Go) implementation
│   ├── Dockerfile                  # Multi-stage build
│   ├── docker-compose.yml
│   └── go.mod
├── scripts/
│   ├── test_carbon_comprehensive.py  # Main test runner with CodeCarbon tracking
│   ├── analyze_results.py            # Results analysis & report generation
│   ├── quick_test.py                 # Convenience wrapper for single tests
│   └── universal_carbon_test.py      # Legacy test script
├── init.sql                        # Shared PostgreSQL schema (users table)
├── requirements.txt                # Python dependencies for test scripts
├── start-all.ps1                   # PowerShell: start all frameworks
└── stop-all.ps1                    # PowerShell: stop all frameworks
```

---

## Methodology

### Key Principles

- **Isolation**: Each framework runs in its own Docker container with a dedicated PostgreSQL instance, preventing resource contention.
- **Identical APIs**: All 6 frameworks implement the same API contract with equivalent computation logic, ensuring fair comparison.
- **Consistent Data**: A shared `init.sql` schema initializes all databases with the same structure and seed data.
- **Warmup Phase**: 50 warmup requests are sent to each framework before testing to stabilize JIT compilation and connection pools.
- **Statistical Rigor**: Response time statistics include min, max, mean, median, p95, and p99 percentiles.
- **Reproducibility**: All configurations are version-controlled; Docker ensures consistent runtime environments.

### Test Execution Flow

1. Health check to verify the framework is running
2. Warmup phase (50 requests to health endpoint)
3. CodeCarbon emissions tracker starts
4. Container resource monitor starts (polls CPU% and memory via `docker stats`)
5. Load test executes (sequential for <= 100 requests, concurrent otherwise)
6. Container resource monitor stops (captures load-phase metrics only)
7. Optional padding sleep if `--min-duration` requires a longer measurement window
8. CodeCarbon tracker stops and records emissions
9. Results are computed (latency stats, RPS, emissions per request, container metrics)
10. Results saved to JSON and CodeCarbon CSV

### Expected Test Duration

| Load | Duration per Test | Full Suite (54 tests) |
|------|-------------------|-----------------------|
| 100 requests | 10-30 seconds | - |
| 1,000 requests | 1-3 minutes | - |
| 10,000 requests | 5-15 minutes | - |
| **All loads** | - | **1-2 hours** |

---

## Adding New Components

### Adding a New Framework

1. Create a directory: `{framework}-carbon-test/`
2. Implement all API endpoints matching the existing contract (health, analytics, I/O, database).
3. Create a `Dockerfile` with the appropriate runtime.
4. Create a `docker-compose.yml` with:
   - App service on a unique port (8006+)
   - PostgreSQL service on a unique port (5438+)
   - Volume mount for `../init.sql`
   - Health checks for both services
5. Add the framework entry to the `FRAMEWORKS` dict in `scripts/test_carbon_comprehensive.py`.

### Adding a New Endpoint

1. Implement the endpoint in all 6 framework applications.
2. Add the endpoint path to the `ENDPOINTS` dict in `scripts/test_carbon_comprehensive.py`.

---

## Troubleshooting

### Port Conflicts

If ports are already in use, stop existing services:
```bash
cd {framework}-carbon-test
docker-compose down
```

### Database Connection Failures

Each framework has its own PostgreSQL instance. Verify the database container is running:
```bash
docker ps | grep db
```

### Java Build Issues (Spring Boot / Micronaut)

```bash
cd {framework}-carbon-test
docker-compose down -v
docker system prune -f
docker-compose up -d --build
```

### Go Module Issues (Gin / Chi)

```bash
cd {framework}-carbon-test
docker-compose run app go mod tidy
docker-compose up -d --build
```

### View Logs

```bash
cd {framework}-carbon-test
docker-compose logs -f app
```

### Stop All Services

```bash
# Windows PowerShell
.\stop-all.ps1

# Or manually per framework
cd fastapi-carbon-test && docker-compose down -v && cd ..
cd django-carbon-test && docker-compose down -v && cd ..
cd springboot-carbon-test && docker-compose down -v && cd ..
cd micronaut-carbon-test && docker-compose down -v && cd ..
cd gin-carbon-test && docker-compose down -v && cd ..
cd chi-carbon-test && docker-compose down -v && cd ..
```

---

## Citation

If you use this framework in your research, please cite:

```bibtex
@software{CarbonFramework_Bench_2026,
  title={CarbonFramework-Bench: A Comprehensive Web Framework Carbon Footprint Benchmarking Tool},
  author={CogNet Lab},
  year={2026},
  url={https://github.com/CogNet-Lab/CarbonFramework-Bench},
  license={MIT}
}
```

## References

- [CodeCarbon](https://github.com/mlco2/codecarbon) - Track carbon emissions from compute
- [FastAPI](https://fastapi.tiangolo.com/)
- [Django](https://www.djangoproject.com/)
- [Spring Boot](https://spring.io/projects/spring-boot)
- [Micronaut](https://micronaut.io/)
- [Gin](https://gin-gonic.com/)
- [Chi](https://go-chi.io/)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2026 CogNet Lab
