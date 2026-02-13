# Carbon Footprint Framework Comparison

Comprehensive carbon footprint analysis of popular web frameworks using CodeCarbon.

## 🌍 Frameworks Tested

| Framework | Language | Port | Status |
|-----------|----------|------|--------|
| **FastAPI** | Python | 8000 | ✅ |
| **Django** | Python | 8001 | ✅ |
| **Spring Boot** | Java | 8002 | ✅ |
| **Micronaut** | Java | 8003 | ✅ |
| **Gin** | Go | 8004 | ✅ |
| **Chi** | Go | 8005 | ✅ |

## 📁 Project Structure

```
carbon-research/
├── fastapi-carbon-test/          # FastAPI implementation
├── django-carbon-test/           # Django implementation  
├── springboot-carbon-test/       # Spring Boot implementation
├── micronaut-carbon-test/        # Micronaut implementation
├── gin-carbon-test/              # Gin (Go) implementation
├── chi-carbon-test/              # Chi (Go) implementation
├── init.sql                      # Shared PostgreSQL initialization
├── scripts/
│   ├── test_carbon_comprehensive.py  # Main testing script
│   ├── analyze_results.py            # Results analysis & reporting
│   └── universal_carbon_test.py      # Legacy test script
└── test_results/                 # Test results & reports
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.8+
- CodeCarbon: `pip install codecarbon requests`

### 1. Build and Start All Frameworks

```powershell
# FastAPI
cd fastapi-carbon-test
docker-compose up -d --build
cd ..

# Django
cd django-carbon-test
docker-compose up -d --build
cd ..

# Spring Boot
cd springboot-carbon-test
docker-compose up -d --build
cd ..

# Micronaut
cd micronaut-carbon-test
docker-compose up -d --build
cd ..

# Gin (Go)
cd gin-carbon-test
docker-compose up -d --build
cd ..

# Chi (Go)
cd chi-carbon-test
docker-compose up -d --build
cd ..
```

### 2. Verify All Services are Running

```powershell
# Check all containers
docker ps

# Test health endpoints
curl http://localhost:8000/api/v1/health  # FastAPI
curl http://localhost:8001/api/v1/health  # Django
curl http://localhost:8002/api/v1/health  # Spring Boot
curl http://localhost:8003/api/v1/health  # Micronaut
curl http://localhost:8004/api/v1/health  # Gin
curl http://localhost:8005/api/v1/health  # Chi
```

### 3. Run Tests

```powershell
cd scripts

# Run full comparison suite (all frameworks, all loads, all endpoints)
python test_carbon_comprehensive.py --suite

# Run specific test
python test_carbon_comprehensive.py -f fastapi -l 100 -e light

# Run for specific framework with multiple loads
python test_carbon_comprehensive.py -f gin -l 1000 -e medium
```

### 4. Analyze Results

```powershell
python analyze_results.py
```

This generates:
- Console output with detailed comparisons
- `test_results/REPORT.md` - Markdown report

## 📊 Test Configurations

### Load Sizes
- **100 requests** - Light load
- **1,000 requests** - Medium load  
- **10,000 requests** - Heavy load

### Endpoints Tested

| Endpoint | Description | Use Case |
|----------|-------------|----------|
| `/api/v1/weather/analytics/light` | Simple computation | Baseline performance |
| `/api/v1/weather/analytics/medium` | Moderate computation | Typical workload |
| `/api/v1/weather/analytics/heavy` | Intensive computation | CPU-bound tasks |

## 📈 Metrics Collected

- **Carbon Emissions** (g CO2)
- **Emissions per Request** (mg CO2)
- **Requests per Second** (RPS)
- **Response Times** (min, mean, median, p95, p99, max)
- **Success/Error Rates**

## 🔧 Individual Framework Commands

### FastAPI
```powershell
cd fastapi-carbon-test
docker-compose up -d --build
docker-compose logs -f
docker-compose down
```

### Django
```powershell
cd django-carbon-test
docker-compose up -d --build
docker-compose logs -f
docker-compose down
```

### Spring Boot
```powershell
cd springboot-carbon-test
docker-compose up -d --build
docker-compose logs -f
docker-compose down
```

### Micronaut
```powershell
cd micronaut-carbon-test
docker-compose up -d --build
docker-compose logs -f
docker-compose down
```

### Gin
```powershell
cd gin-carbon-test
docker-compose up -d --build
docker-compose logs -f
docker-compose down
```

### Chi
```powershell
cd chi-carbon-test
docker-compose up -d --build
docker-compose logs -f
docker-compose down
```

## 🛠️ Troubleshooting

### Port Conflicts
If ports are already in use, stop existing services:
```powershell
docker-compose down
```

### Database Issues
Each framework has its own PostgreSQL instance on different ports:
- FastAPI: 5432
- Django: 5433
- Spring Boot: 5434
- Micronaut: 5435
- Gin: 5436
- Chi: 5437

### View Logs
```powershell
docker-compose logs -f app
```

### Rebuild Containers
```powershell
docker-compose down -v
docker-compose up -d --build
```

## 📋 API Endpoints

All frameworks implement the same endpoints:

### Health & Info
- `GET /` - Service information
- `GET /api/v1/health` - Health check

### Analytics (CPU-bound)
- `GET /api/v1/weather/analytics/light` - Light computation
- `GET /api/v1/weather/analytics/medium?size=2000&iterations=3` - Medium
- `GET /api/v1/weather/analytics/heavy?size=5000&iterations=5` - Heavy

### I/O Bound
- `GET /api/v1/weather/external?delay_ms=100` - Simulated delay
- `GET /api/v1/weather/fetch?city=Colombo` - External API call

### Database
- `GET /api/v1/db/users` - Get all users
- `POST /api/v1/db/users` - Create user
  ```json
  {"name": "John Doe", "email": "john@example.com"}
  ```

## 📊 Example Results

Results are saved in `test_results/` as:
- Individual test JSONs: `{framework}_{endpoint}_{load}_{timestamp}.json`
- Combined suite results: `comparison_suite_{timestamp}.json`
- Analysis report: `REPORT.md`

## 🎯 Goals

1. ✅ Measure carbon footprint across different frameworks
2. ✅ Compare performance under various loads (100, 1000, 10000 requests)
3. ✅ Identify most energy-efficient frameworks
4. ✅ Analyze performance vs. sustainability trade-offs

## 📝 Notes

- Tests use shared database schema (`init.sql`)
- Each framework runs in isolated Docker container
- CodeCarbon measures energy consumption during tests
- Results include both performance and carbon metrics

## 🤝 Contributing

To add a new framework:
1. Create new directory: `{framework}-carbon-test/`
2. Implement the same API endpoints
3. Add Dockerfile and docker-compose.yml
4. Use unique port number
5. Update `FRAMEWORKS` dict in test script

## 📚 References

- [CodeCarbon](https://github.com/mlco2/codecarbon)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Django](https://www.djangoproject.com/)
- [Spring Boot](https://spring.io/projects/spring-boot)
- [Micronaut](https://micronaut.io/)
- [Gin](https://gin-gonic.com/)
- [Chi](https://go-chi.io/)
