# app.py
import time
import hashlib
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncpg
import os
import uvicorn
import httpx

# Environment variables with defaults
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@db:5432/mydb")
EXTERNAL_API_URL = os.getenv("EXTERNAL_URL", "https://api.open-meteo.com/v1/forecast")

app = FastAPI(
    title="Weather Analytics Service - FastAPI",
    description="High-performance weather analytics API for carbon footprint research",
    version="1.0.0"
)

# Startup time tracking
START_TIME = time.time()

# Database connection pool
@app.on_event("startup")
async def startup():
    """Initialize database connection pool on startup"""
    try:
        # Only create DB pool if DATABASE_URL is properly configured
        if "db:" in DATABASE_URL or "localhost" in DATABASE_URL:
            app.state.db = await asyncpg.create_pool(
                DATABASE_URL, 
                min_size=2, 
                max_size=10,
                timeout=30
            )
            print(f"✓ Database connection pool created")
        else:
            print("⚠ Database URL not configured, skipping DB pool")
            app.state.db = None
    except Exception as e:
        print(f"⚠ Database connection failed: {e}")
        app.state.db = None

@app.on_event("shutdown")
async def shutdown():
    """Clean up database connections on shutdown"""
    if hasattr(app.state, "db") and app.state.db:
        await app.state.db.close()
        print("✓ Database connection pool closed")

# Models
class UserIn(BaseModel):
    name: str
    email: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str

# ============================================================================
# HEALTH & INFO ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Weather Analytics Service",
        "framework": "FastAPI",
        "version": "1.0.0",
        "status": "running",
        "uptime_seconds": int(time.time() - START_TIME)
    }

@app.get("/api/v1/health")
async def health():
    """Health check endpoint for monitoring"""
    uptime = int(time.time() - START_TIME)
    return {
        "status": "healthy",
        "framework": "fastapi",
        "uptime_seconds": uptime,
        "uptime_ms": uptime * 1000,
        "timestamp": int(time.time() * 1000)
    }

# ============================================================================
# CPU-INTENSIVE ENDPOINTS
# ============================================================================

def heavy_compute(size: int, iterations: int) -> dict:
    """
    CPU-intensive computation for performance testing
    Simulates heavy analytics workload
    """
    start = time.time()
    
    # Matrix-like computation
    a = [i for i in range(size)]
    total = 0
    
    for iteration in range(iterations):
        for x in a:
            total += (x * x) % (size + 1)
    
    # Add some hashing for realistic CPU load
    h = hashlib.sha256(str(total).encode()).hexdigest()
    
    elapsed_ms = int((time.time() - start) * 1000)
    
    return {
        "result_hash": h,
        "total_sum": total,
        "matrix_size": size,
        "iterations": iterations,
        "elapsed_ms": elapsed_ms
    }

@app.get("/api/v1/weather/analytics/heavy")
async def analytics_heavy(size: int = 5000, iterations: int = 5):
    """
    CPU-heavy endpoint for carbon footprint testing
    Simulates complex weather analytics computation
    
    Query Parameters:
    - size: Matrix size for computation (default: 5000)
    - iterations: Number of iterations (default: 5)
    """
    # Run in thread pool to avoid blocking event loop
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, heavy_compute, size, iterations)
    
    return {
        "endpoint": "heavy_analytics",
        "framework": "fastapi",
        **result
    }

@app.get("/api/v1/weather/analytics/light")
async def analytics_light():
    """
    Light computation endpoint for baseline testing
    """
    start = time.time()
    
    # Simple computation
    result = sum(i ** 2 for i in range(1000))
    
    elapsed_ms = int((time.time() - start) * 1000)
    
    return {
        "endpoint": "light_analytics",
        "framework": "fastapi",
        "result": result,
        "elapsed_ms": elapsed_ms
    }

@app.get("/api/v1/weather/analytics/medium")
async def analytics_medium(size: int = 2000, iterations: int = 3):
    """
    Medium computation endpoint for moderate load testing
    """
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, heavy_compute, size, iterations)
    
    return {
        "endpoint": "medium_analytics",
        "framework": "fastapi",
        **result
    }

# ============================================================================
# I/O-BOUND ENDPOINTS
# ============================================================================

@app.get("/api/v1/weather/external")
async def weather_external(delay_ms: int = 100):
    """
    I/O-bound endpoint that simulates external API calls
    Tests network latency and async I/O performance
    
    Query Parameters:
    - delay_ms: Simulated delay in milliseconds (default: 100)
    """
    start = time.time()
    
    # Simulate I/O delay
    await asyncio.sleep(delay_ms / 1000.0)
    
    # Mock weather data
    weather_data = {
        "temperature": 25.5,
        "humidity": 65,
        "wind_speed": 12.3,
        "conditions": "Partly Cloudy",
        "location": "Colombo, LK"
    }
    
    elapsed_ms = int((time.time() - start) * 1000)
    
    return {
        "endpoint": "external_api",
        "framework": "fastapi",
        "data": weather_data,
        "simulated_delay_ms": delay_ms,
        "elapsed_ms": elapsed_ms
    }

@app.get("/api/v1/weather/fetch")
async def weather_fetch(city: str = "Colombo"):
    """
    Fetch real weather data (or simulate if external API is unavailable)
    Tests real external API integration
    """
    start = time.time()
    
    try:
        # Try to fetch real data (example with Open-Meteo API)
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Colombo coordinates: 6.9271° N, 79.8612° E
            url = "https://api.open-meteo.com/v1/forecast?latitude=6.9271&longitude=79.8612&current_weather=true"
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                weather_data = data.get("current_weather", {})
            else:
                raise Exception("API unavailable")
                
    except Exception as e:
        # Fallback to mock data
        weather_data = {
            "temperature": 28.0,
            "windspeed": 10.5,
            "weathercode": 1,
            "note": "Mock data (external API unavailable)"
        }
    
    elapsed_ms = int((time.time() - start) * 1000)
    
    return {
        "endpoint": "weather_fetch",
        "framework": "fastapi",
        "city": city,
        "data": weather_data,
        "elapsed_ms": elapsed_ms
    }

# ============================================================================
# DATABASE CRUD ENDPOINTS (Optional - requires DB)
# ============================================================================

@app.post("/api/v1/users", status_code=201, response_model=UserOut)
async def create_user(u: UserIn):
    """Create a new user (requires database)"""
    if not app.state.db:
        raise HTTPException(status_code=503, detail="Database not configured")
    
    try:
        async with app.state.db.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO users(name, email) VALUES($1, $2) RETURNING id, name, email",
                u.name, u.email
            )
        return dict(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/v1/users/{user_id}", response_model=UserOut)
async def get_user(user_id: int):
    """Get user by ID (requires database)"""
    if not app.state.db:
        raise HTTPException(status_code=503, detail="Database not configured")
    
    try:
        async with app.state.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, email FROM users WHERE id=$1",
                user_id
            )
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.put("/api/v1/users/{user_id}", response_model=UserOut)
async def update_user(user_id: int, u: UserIn):
    """Update user by ID (requires database)"""
    if not app.state.db:
        raise HTTPException(status_code=503, detail="Database not configured")
    
    try:
        async with app.state.db.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE users SET name=$1, email=$2 WHERE id=$3 RETURNING id, name, email",
                u.name, u.email, user_id
            )
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.delete("/api/v1/users/{user_id}", status_code=204)
async def delete_user(user_id: int):
    """Delete user by ID (requires database)"""
    if not app.state.db:
        raise HTTPException(status_code=503, detail="Database not configured")
    
    try:
        async with app.state.db.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM users WHERE id=$1",
                user_id
            )
        
        # asyncpg returns a string like "DELETE 1" or "DELETE 0"
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="User not found")
        
        return
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        workers=1,
        log_level="info"
    )