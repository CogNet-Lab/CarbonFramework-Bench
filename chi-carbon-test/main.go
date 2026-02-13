package main

import (
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	_ "github.com/lib/pq"
)

var (
	startTime time.Time
	db        *sql.DB
)

type User struct {
	ID        int64     `json:"id"`
	Name      string    `json:"name"`
	Email     string    `json:"email"`
	CreatedAt time.Time `json:"created_at"`
}

type ComputeResult struct {
	ResultHash string `json:"result_hash"`
	TotalSum   int64  `json:"total_sum"`
	MatrixSize int    `json:"matrix_size"`
	Iterations int    `json:"iterations"`
	ElapsedMs  int64  `json:"elapsed_ms"`
}

func main() {
	startTime = time.Now()

	// Initialize database
	initDB()
	defer db.Close()

	r := chi.NewRouter()

	// Middleware
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	// Root endpoint
	r.Get("/", rootHandler)

	// Health check
	r.Get("/api/v1/health", healthHandler)

	// Analytics endpoints
	r.Get("/api/v1/weather/analytics/heavy", analyticsHeavy)
	r.Get("/api/v1/weather/analytics/light", analyticsLight)
	r.Get("/api/v1/weather/analytics/medium", analyticsMedium)

	// I/O endpoints
	r.Get("/api/v1/weather/external", weatherExternal)
	r.Get("/api/v1/weather/fetch", weatherFetch)

	// Database endpoints
	r.Get("/api/v1/db/users", getUsers)
	r.Post("/api/v1/db/users", createUser)

	log.Println("🚀 Chi server starting on :8000")
	http.ListenAndServe(":8000", r)
}

func initDB() {
	dbHost := getEnv("DB_HOST", "localhost")
	dbPort := getEnv("DB_PORT", "5432")
	dbName := getEnv("DB_NAME", "mydb")
	dbUser := getEnv("DB_USER", "postgres")
	dbPassword := getEnv("DB_PASSWORD", "1234")

	connStr := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		dbHost, dbPort, dbUser, dbPassword, dbName)

	var err error
	db, err = sql.Open("postgres", connStr)
	if err != nil {
		log.Printf("⚠️  Database connection warning: %v", err)
		return
	}

	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(2)
	db.SetConnMaxLifetime(30 * time.Second)

	if err = db.Ping(); err != nil {
		log.Printf("⚠️  Database ping warning: %v", err)
	} else {
		log.Println("✓ Database connected")
	}
}

func rootHandler(w http.ResponseWriter, r *http.Request) {
	respondJSON(w, http.StatusOK, map[string]interface{}{
		"service":        "Weather Analytics Service",
		"framework":      "Chi",
		"version":        "1.0.0",
		"status":         "running",
		"uptime_seconds": int(time.Since(startTime).Seconds()),
	})
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	uptimeMs := time.Since(startTime).Milliseconds()
	respondJSON(w, http.StatusOK, map[string]interface{}{
		"status":         "healthy",
		"framework":      "chi",
		"uptime_seconds": uptimeMs / 1000,
		"uptime_ms":      uptimeMs,
		"timestamp":      time.Now().UnixMilli(),
	})
}

func analyticsHeavy(w http.ResponseWriter, r *http.Request) {
	size := parseIntParam(r, "size", 5000)
	iterations := parseIntParam(r, "iterations", 5)

	result := heavyCompute(size, iterations)
	respondJSON(w, http.StatusOK, map[string]interface{}{
		"endpoint":    "heavy_analytics",
		"framework":   "chi",
		"result_hash": result.ResultHash,
		"total_sum":   result.TotalSum,
		"matrix_size": result.MatrixSize,
		"iterations":  result.Iterations,
		"elapsed_ms":  result.ElapsedMs,
	})
}

func analyticsLight(w http.ResponseWriter, r *http.Request) {
	start := time.Now()

	var result int64
	for i := 0; i < 1000; i++ {
		result += int64(i * i)
	}

	elapsedMs := time.Since(start).Milliseconds()

	respondJSON(w, http.StatusOK, map[string]interface{}{
		"endpoint":   "light_analytics",
		"framework":  "chi",
		"result":     result,
		"elapsed_ms": elapsedMs,
	})
}

func analyticsMedium(w http.ResponseWriter, r *http.Request) {
	size := parseIntParam(r, "size", 2000)
	iterations := parseIntParam(r, "iterations", 3)

	result := heavyCompute(size, iterations)
	respondJSON(w, http.StatusOK, map[string]interface{}{
		"endpoint":    "medium_analytics",
		"framework":   "chi",
		"result_hash": result.ResultHash,
		"total_sum":   result.TotalSum,
		"matrix_size": result.MatrixSize,
		"iterations":  result.Iterations,
		"elapsed_ms":  result.ElapsedMs,
	})
}

func weatherExternal(w http.ResponseWriter, r *http.Request) {
	delayMs := parseIntParam(r, "delay_ms", 100)
	start := time.Now()

	time.Sleep(time.Duration(delayMs) * time.Millisecond)

	weatherData := map[string]interface{}{
		"temperature": 25.5,
		"humidity":    65,
		"wind_speed":  12.3,
		"conditions":  "Partly Cloudy",
		"location":    "Colombo, LK",
	}

	elapsedMs := time.Since(start).Milliseconds()

	respondJSON(w, http.StatusOK, map[string]interface{}{
		"endpoint":           "external_api",
		"framework":          "chi",
		"data":               weatherData,
		"simulated_delay_ms": delayMs,
		"elapsed_ms":         elapsedMs,
	})
}

func weatherFetch(w http.ResponseWriter, r *http.Request) {
	city := r.URL.Query().Get("city")
	if city == "" {
		city = "Colombo"
	}
	start := time.Now()

	weatherData := map[string]interface{}{
		"temperature": 28.0,
		"windspeed":   10.5,
		"weathercode": 1,
		"note":        "Mock data",
	}

	elapsedMs := time.Since(start).Milliseconds()

	respondJSON(w, http.StatusOK, map[string]interface{}{
		"endpoint":   "weather_fetch",
		"framework":  "chi",
		"city":       city,
		"data":       weatherData,
		"elapsed_ms": elapsedMs,
	})
}

func getUsers(w http.ResponseWriter, r *http.Request) {
	rows, err := db.Query("SELECT id, name, email, created_at FROM users")
	if err != nil {
		respondJSON(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}
	defer rows.Close()

	var users []User
	for rows.Next() {
		var u User
		if err := rows.Scan(&u.ID, &u.Name, &u.Email, &u.CreatedAt); err != nil {
			continue
		}
		users = append(users, u)
	}

	respondJSON(w, http.StatusOK, users)
}

func createUser(w http.ResponseWriter, r *http.Request) {
	var input struct {
		Name  string `json:"name"`
		Email string `json:"email"`
	}

	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}

	var user User
	err := db.QueryRow(
		"INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id, name, email, created_at",
		input.Name, input.Email,
	).Scan(&user.ID, &user.Name, &user.Email, &user.CreatedAt)

	if err != nil {
		respondJSON(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	respondJSON(w, http.StatusCreated, user)
}

func heavyCompute(size, iterations int) ComputeResult {
	start := time.Now()

	a := make([]int, size)
	for i := 0; i < size; i++ {
		a[i] = i
	}

	var total int64
	for iteration := 0; iteration < iterations; iteration++ {
		for _, x := range a {
			total += int64(x*x) % int64(size+1)
		}
	}

	hash := sha256.Sum256([]byte(fmt.Sprintf("%d", total)))
	hashStr := hex.EncodeToString(hash[:])

	elapsedMs := time.Since(start).Milliseconds()

	return ComputeResult{
		ResultHash: hashStr,
		TotalSum:   total,
		MatrixSize: size,
		Iterations: iterations,
		ElapsedMs:  elapsedMs,
	}
}

func parseIntParam(r *http.Request, param string, defaultValue int) int {
	if val := r.URL.Query().Get(param); val != "" {
		if intVal, err := strconv.Atoi(val); err == nil {
			return intVal
		}
	}
	return defaultValue
}

func respondJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
