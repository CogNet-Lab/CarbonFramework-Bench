import time
import hashlib
import httpx
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import User
from .serializers import UserSerializer

START_TIME = time.time()

# Root endpoint
@api_view(['GET'])
def root(request):
    return Response({
        "service": "Weather Analytics Service",
        "framework": "Django",
        "version": "1.0.0",
        "status": "running",
        "uptime_seconds": int(time.time() - START_TIME)
    })

# Health check endpoint
@api_view(['GET'])
def health(request):
    uptime = int(time.time() - START_TIME)
    return Response({
        "status": "healthy",
        "framework": "django",
        "uptime_seconds": uptime,
        "uptime_ms": uptime * 1000,
        "timestamp": int(time.time() * 1000)
    })

# Heavy computation function
def heavy_compute(size, iterations):
    start = time.time()
    a = [i for i in range(size)]
    total = 0
    
    for iteration in range(iterations):
        for x in a:
            total += (x * x) % (size + 1)
    
    h = hashlib.sha256(str(total).encode()).hexdigest()
    elapsed_ms = int((time.time() - start) * 1000)
    
    return {
        "result_hash": h,
        "total_sum": total,
        "matrix_size": size,
        "iterations": iterations,
        "elapsed_ms": elapsed_ms
    }

# Heavy analytics endpoint
@api_view(['GET'])
def analytics_heavy(request):
    size = int(request.GET.get('size', 5000))
    iterations = int(request.GET.get('iterations', 5))
    result = heavy_compute(size, iterations)
    
    return Response({
        "endpoint": "heavy_analytics",
        "framework": "django",
        **result
    })

# Light analytics endpoint
@api_view(['GET'])
def analytics_light(request):
    start = time.time()
    result = sum(i ** 2 for i in range(1000))
    elapsed_ms = int((time.time() - start) * 1000)
    
    return Response({
        "endpoint": "light_analytics",
        "framework": "django",
        "result": result,
        "elapsed_ms": elapsed_ms
    })

# Medium analytics endpoint
@api_view(['GET'])
def analytics_medium(request):
    size = int(request.GET.get('size', 2000))
    iterations = int(request.GET.get('iterations', 3))
    result = heavy_compute(size, iterations)
    
    return Response({
        "endpoint": "medium_analytics",
        "framework": "django",
        **result
    })

# External API simulation endpoint
@api_view(['GET'])
def weather_external(request):
    delay_ms = int(request.GET.get('delay_ms', 100))
    start = time.time()
    
    time.sleep(delay_ms / 1000.0)
    
    weather_data = {
        "temperature": 25.5,
        "humidity": 65,
        "wind_speed": 12.3,
        "conditions": "Partly Cloudy",
        "location": "Colombo, LK"
    }
    
    elapsed_ms = int((time.time() - start) * 1000)
    
    return Response({
        "endpoint": "external_api",
        "framework": "django",
        "data": weather_data,
        "simulated_delay_ms": delay_ms,
        "elapsed_ms": elapsed_ms
    })

# Real weather API fetch endpoint
@api_view(['GET'])
def weather_fetch(request):
    city = request.GET.get('city', 'Colombo')
    start = time.time()
    
    try:
        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast?latitude=6.9271&longitude=79.8612&current_weather=true",
            timeout=5.0
        )
        
        if response.status_code == 200:
            data = response.json()
            weather_data = data.get("current_weather", {})
        else:
            raise Exception("API unavailable")
    except:
        weather_data = {
            "temperature": 28.0,
            "windspeed": 10.5,
            "weathercode": 1,
            "note": "Mock data"
        }
    
    elapsed_ms = int((time.time() - start) * 1000)
    
    return Response({
        "endpoint": "weather_fetch",
        "framework": "django",
        "city": city,
        "data": weather_data,
        "elapsed_ms": elapsed_ms
    })

# CRUD operations for User model
@api_view(['POST'])
def create_user(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        serializer = UserSerializer(user)
        return Response(serializer.data)
    except User.DoesNotExist:
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['PUT'])
def update_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except User.DoesNotExist:
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
def delete_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except User.DoesNotExist:
        return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)