package main

import (
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
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

	// Set Gin to release mode for production
	gin.SetMode(gin.ReleaseMode)
	r := gin.Default()

	// Root endpoint
	r.GET("/", rootHandler)

	// Health check
	r.GET("/api/v1/health", healthHandler)

	// Analytics endpoints
	r.GET("/api/v1/weather/analytics/heavy", analyticsHeavy)
	r.GET("/api/v1/weather/analytics/light", analyticsLight)
	r.GET("/api/v1/weather/analytics/medium", analyticsMedium)

	// I/O endpoints
	r.GET("/api/v1/weather/external", weatherExternal)
	r.GET("/api/v1/weather/fetch", weatherFetch)

	// Database endpoints
	r.GET("/api/v1/db/users", getUsers)
	r.POST("/api/v1/db/users", createUser)

	log.Println("🚀 Gin server starting on :8000")
	r.Run(":8000")
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

func rootHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"service":        "Weather Analytics Service",
		"framework":      "Gin",
		"version":        "1.0.0",
		"status":         "running",
		"uptime_seconds": int(time.Since(startTime).Seconds()),
	})
}

func healthHandler(c *gin.Context) {
	uptimeMs := time.Since(startTime).Milliseconds()
	c.JSON(http.StatusOK, gin.H{
		"status":         "healthy",
		"framework":      "gin",
		"uptime_seconds": uptimeMs / 1000,
		"uptime_ms":      uptimeMs,
		"timestamp":      time.Now().UnixMilli(),
	})
}

func analyticsHeavy(c *gin.Context) {
	size := parseIntParam(c, "size", 5000)
	iterations := parseIntParam(c, "iterations", 5)

	result := heavyCompute(size, iterations)
	c.JSON(http.StatusOK, gin.H{
		"endpoint":    "heavy_analytics",
		"framework":   "gin",
		"result_hash": result.ResultHash,
		"total_sum":   result.TotalSum,
		"matrix_size": result.MatrixSize,
		"iterations":  result.Iterations,
		"elapsed_ms":  result.ElapsedMs,
	})
}

func analyticsLight(c *gin.Context) {
	start := time.Now()

	var result int64
	for i := 0; i < 1000; i++ {
		result += int64(i * i)
	}

	elapsedMs := time.Since(start).Milliseconds()

	c.JSON(http.StatusOK, gin.H{
		"endpoint":   "light_analytics",
		"framework":  "gin",
		"result":     result,
		"elapsed_ms": elapsedMs,
	})
}

func analyticsMedium(c *gin.Context) {
	size := parseIntParam(c, "size", 2000)
	iterations := parseIntParam(c, "iterations", 3)

	result := heavyCompute(size, iterations)
	c.JSON(http.StatusOK, gin.H{
		"endpoint":    "medium_analytics",
		"framework":   "gin",
		"result_hash": result.ResultHash,
		"total_sum":   result.TotalSum,
		"matrix_size": result.MatrixSize,
		"iterations":  result.Iterations,
		"elapsed_ms":  result.ElapsedMs,
	})
}

func weatherExternal(c *gin.Context) {
	delayMs := parseIntParam(c, "delay_ms", 100)
	start := time.Now()

	time.Sleep(time.Duration(delayMs) * time.Millisecond)

	weatherData := gin.H{
		"temperature": 25.5,
		"humidity":    65,
		"wind_speed":  12.3,
		"conditions":  "Partly Cloudy",
		"location":    "Colombo, LK",
	}

	elapsedMs := time.Since(start).Milliseconds()

	c.JSON(http.StatusOK, gin.H{
		"endpoint":           "external_api",
		"framework":          "gin",
		"data":               weatherData,
		"simulated_delay_ms": delayMs,
		"elapsed_ms":         elapsedMs,
	})
}

func weatherFetch(c *gin.Context) {
	city := c.DefaultQuery("city", "Colombo")
	start := time.Now()

	weatherData := gin.H{
		"temperature": 28.0,
		"windspeed":   10.5,
		"weathercode": 1,
		"note":        "Mock data",
	}

	elapsedMs := time.Since(start).Milliseconds()

	c.JSON(http.StatusOK, gin.H{
		"endpoint":   "weather_fetch",
		"framework":  "gin",
		"city":       city,
		"data":       weatherData,
		"elapsed_ms": elapsedMs,
	})
}

func getUsers(c *gin.Context) {
	rows, err := db.Query("SELECT id, name, email, created_at FROM users")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
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

	c.JSON(http.StatusOK, users)
}

func createUser(c *gin.Context) {
	var input struct {
		Name  string `json:"name"`
		Email string `json:"email"`
	}

	if err := c.BindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var user User
	err := db.QueryRow(
		"INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id, name, email, created_at",
		input.Name, input.Email,
	).Scan(&user.ID, &user.Name, &user.Email, &user.CreatedAt)

	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, user)
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

func parseIntParam(c *gin.Context, param string, defaultValue int) int {
	if val := c.Query(param); val != "" {
		if intVal, err := strconv.Atoi(val); err == nil {
			return intVal
		}
	}
	return defaultValue
}

func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
