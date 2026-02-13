package com.carbon.test.controller;

import com.carbon.test.model.User;
import com.carbon.test.repository.UserRepository;
import io.micronaut.http.annotation.*;
import io.micronaut.http.client.HttpClient;
import io.micronaut.http.client.annotation.Client;
import jakarta.inject.Inject;

import java.security.MessageDigest;
import java.util.*;

@Controller
public class WeatherController {
    
    private final long startTime = System.currentTimeMillis();
    
    @Inject
    private UserRepository userRepository;
    
    @Inject
    @Client("https://api.open-meteo.com")
    private HttpClient httpClient;
    
    @Get("/")
    public Map<String, Object> root() {
        Map<String, Object> response = new HashMap<>();
        response.put("service", "Weather Analytics Service");
        response.put("framework", "Micronaut");
        response.put("version", "1.0.0");
        response.put("status", "running");
        response.put("uptime_seconds", (System.currentTimeMillis() - startTime) / 1000);
        return response;
    }
    
    @Get("/api/v1/health")
    public Map<String, Object> health() {
        long uptimeMs = System.currentTimeMillis() - startTime;
        Map<String, Object> response = new HashMap<>();
        response.put("status", "healthy");
        response.put("framework", "micronaut");
        response.put("uptime_seconds", uptimeMs / 1000);
        response.put("uptime_ms", uptimeMs);
        response.put("timestamp", System.currentTimeMillis());
        return response;
    }
    
    @Get("/api/v1/weather/analytics/heavy")
    public Map<String, Object> analyticsHeavy(
            @QueryValue(defaultValue = "5000") int size,
            @QueryValue(defaultValue = "5") int iterations) {
        return heavyCompute(size, iterations, "heavy_analytics");
    }
    
    @Get("/api/v1/weather/analytics/light")
    public Map<String, Object> analyticsLight() {
        long start = System.currentTimeMillis();
        
        long result = 0;
        for (int i = 0; i < 1000; i++) {
            result += (long) i * i;
        }
        
        long elapsedMs = System.currentTimeMillis() - start;
        
        Map<String, Object> response = new HashMap<>();
        response.put("endpoint", "light_analytics");
        response.put("framework", "micronaut");
        response.put("result", result);
        response.put("elapsed_ms", elapsedMs);
        return response;
    }
    
    @Get("/api/v1/weather/analytics/medium")
    public Map<String, Object> analyticsMedium(
            @QueryValue(defaultValue = "2000") int size,
            @QueryValue(defaultValue = "3") int iterations) {
        return heavyCompute(size, iterations, "medium_analytics");
    }
    
    @Get("/api/v1/weather/external")
    public Map<String, Object> weatherExternal(
            @QueryValue(defaultValue = "100") int delay_ms) throws InterruptedException {
        long start = System.currentTimeMillis();
        
        Thread.sleep(delay_ms);
        
        Map<String, Object> weatherData = new HashMap<>();
        weatherData.put("temperature", 25.5);
        weatherData.put("humidity", 65);
        weatherData.put("wind_speed", 12.3);
        weatherData.put("conditions", "Partly Cloudy");
        weatherData.put("location", "Colombo, LK");
        
        long elapsedMs = System.currentTimeMillis() - start;
        
        Map<String, Object> response = new HashMap<>();
        response.put("endpoint", "external_api");
        response.put("framework", "micronaut");
        response.put("data", weatherData);
        response.put("simulated_delay_ms", delay_ms);
        response.put("elapsed_ms", elapsedMs);
        return response;
    }
    
    @Get("/api/v1/weather/fetch")
    public Map<String, Object> weatherFetch(
            @QueryValue(defaultValue = "Colombo") String city) {
        long start = System.currentTimeMillis();
        
        Map<String, Object> weatherData = new HashMap<>();
        try {
            String response = httpClient.toBlocking()
                    .retrieve("/v1/forecast?latitude=6.9271&longitude=79.8612&current_weather=true");
            weatherData.put("raw_response", response);
        } catch (Exception e) {
            weatherData.put("temperature", 28.0);
            weatherData.put("windspeed", 10.5);
            weatherData.put("weathercode", 1);
            weatherData.put("note", "Mock data (external API unavailable)");
        }
        
        long elapsedMs = System.currentTimeMillis() - start;
        
        Map<String, Object> result = new HashMap<>();
        result.put("endpoint", "weather_fetch");
        result.put("framework", "micronaut");
        result.put("city", city);
        result.put("data", weatherData);
        result.put("elapsed_ms", elapsedMs);
        return result;
    }
    
    @Get("/api/v1/db/users")
    public Iterable<User> getUsers() {
        return userRepository.findAll();
    }
    
    @Post("/api/v1/db/users")
    public User createUser(@Body Map<String, String> body) {
        User user = new User(body.get("name"), body.get("email"));
        return userRepository.save(user);
    }
    
    private Map<String, Object> heavyCompute(int size, int iterations, String endpoint) {
        long start = System.currentTimeMillis();
        
        List<Integer> a = new ArrayList<>();
        for (int i = 0; i < size; i++) {
            a.add(i);
        }
        
        long total = 0;
        for (int iteration = 0; iteration < iterations; iteration++) {
            for (int x : a) {
                total += ((long) x * x) % (size + 1);
            }
        }
        
        String hash = "";
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hashBytes = md.digest(String.valueOf(total).getBytes());
            StringBuilder sb = new StringBuilder();
            for (byte b : hashBytes) {
                sb.append(String.format("%02x", b));
            }
            hash = sb.toString();
        } catch (Exception e) {
            hash = "error";
        }
        
        long elapsedMs = System.currentTimeMillis() - start;
        
        Map<String, Object> response = new HashMap<>();
        response.put("endpoint", endpoint);
        response.put("framework", "micronaut");
        response.put("result_hash", hash);
        response.put("total_sum", total);
        response.put("matrix_size", size);
        response.put("iterations", iterations);
        response.put("elapsed_ms", elapsedMs);
        return response;
    }
}
