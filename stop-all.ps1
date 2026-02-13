# Stop all framework containers

Write-Host "`n[*] Stopping all framework containers..." -ForegroundColor Yellow
Write-Host "====================================`n" -ForegroundColor Yellow

$frameworks = @(
    "fastapi-carbon-test",
    "django-carbon-test",
    "springboot-carbon-test",
    "micronaut-carbon-test",
    "gin-carbon-test",
    "chi-carbon-test"
)

foreach ($framework in $frameworks) {
    Write-Host "`n[+] Stopping $framework..." -ForegroundColor Cyan
    
    if (Test-Path $framework) {
        Set-Location $framework
        docker-compose down
        Set-Location ..
        Write-Host "[OK] $framework stopped" -ForegroundColor Green
    }
}

Write-Host "`n[DONE] All containers stopped!`n" -ForegroundColor Green
