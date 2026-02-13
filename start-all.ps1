# Quick Start Script for Windows PowerShell
# Run all framework containers

Write-Host "`n[*] Starting all framework containers..." -ForegroundColor Green
Write-Host "====================================`n" -ForegroundColor Green

$frameworks = @(
    @{Name="FastAPI"; Path="fastapi-carbon-test"; Port=8000},
    @{Name="Django"; Path="django-carbon-test"; Port=8001},
    @{Name="Spring Boot"; Path="springboot-carbon-test"; Port=8002},
    @{Name="Micronaut"; Path="micronaut-carbon-test"; Port=8003},
    @{Name="Gin"; Path="gin-carbon-test"; Port=8004},
    @{Name="Chi"; Path="chi-carbon-test"; Port=8005}
)

foreach ($framework in $frameworks) {
    Write-Host "`n[+] Starting $($framework.Name)..." -ForegroundColor Cyan
    
    if (Test-Path $framework.Path) {
        Set-Location $framework.Path
        docker-compose up -d --build
        Set-Location ..
        Write-Host "[OK] $($framework.Name) started on port $($framework.Port)" -ForegroundColor Green
    } else {
        Write-Host "[!] Directory $($framework.Path) not found!" -ForegroundColor Yellow
    }
}

Write-Host "`n`n[*] Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "`n`n[*] Checking service health..." -ForegroundColor Cyan
Write-Host "====================================`n" -ForegroundColor Cyan

foreach ($framework in $frameworks) {
    $url = "http://localhost:$($framework.Port)/api/v1/health"
    try {
        $response = Invoke-WebRequest -Uri $url -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "[OK] $($framework.Name) is healthy on port $($framework.Port)" -ForegroundColor Green
        }
    } catch {
        Write-Host "[X] $($framework.Name) is not responding on port $($framework.Port)" -ForegroundColor Red
    }
}

Write-Host "`n`n[DONE] Setup complete!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "  1. cd scripts" -ForegroundColor White
Write-Host "  2. python test_carbon_comprehensive.py --suite" -ForegroundColor White
Write-Host "  3. python analyze_results.py" -ForegroundColor White
Write-Host "`n"
