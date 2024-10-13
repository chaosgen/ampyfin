package main

import (
	"bufio"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

// LogEntry represents a log entry structure
type LogEntry struct {
	Line      string `json:"line"`
	Timestamp string `json:"timestamp"`
	Level     string `json:"level"`
}

var (
	userTokens      = map[string]string{"user1": "password1"} // Simple user store
	requestCount    = make(map[string]int)
	requestMutex    sync.Mutex
	requestLimit    = 100
	timeWindow      = time.Minute
	logLevels       = []string{"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
)

// AnalyzeLogs analyzes logs with time range and pagination
func analyzeLogs(queries []string, logLevel string, limit int, offset int, startTime, endTime time.Time) ([]LogEntry, int, error) {
	file, err := os.Open("system.log")
	if err != nil {
		return nil, 0, fmt.Errorf("error opening log file: %w", err)
	}
	defer file.Close()

	var results []LogEntry
	var matchCount int
	scanner := bufio.NewScanner(file)

	for scanner.Scan() {
		line := scanner.Text()

		// Check if the line contains a log level if specified
		if logLevel != "" && !strings.Contains(line, logLevel) {
			continue
		}

		timestamp := extractTimestamp(line)
		logTime, err := time.Parse("2006-01-02 15:04:05", timestamp) // Adjust format as per your log's timestamp
		if err != nil || logTime.Before(startTime) || logTime.After(endTime) {
			continue
		}

		for _, query := range queries {
			if strings.Contains(line, query) {
				results = append(results, LogEntry{Line: line, Level: extractLogLevel(line), Timestamp: timestamp})
				matchCount++
				break
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, 0, fmt.Errorf("error reading log file: %w", err)
	}

	// Implement pagination
	if offset > len(results) {
		return []LogEntry{}, 0, nil
	}
	end := offset + limit
	if end > len(results) {
		end = len(results)
	}
	return results[offset:end], matchCount, nil
}

// Extract log level
func extractLogLevel(line string) string {
	parts := strings.Split(line, " ")
	if len(parts) > 2 {
		return parts[2]
	}
	return ""
}

// Extract timestamp
func extractTimestamp(line string) string {
	parts := strings.Split(line, " ")
	if len(parts) > 1 {
		return parts[0] + " " + parts[1]
	}
	return ""
}

// Export logs to CSV
func exportLogsToCSV(entries []LogEntry, filename string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// Write header
	writer.Write([]string{"Timestamp", "Level", "Line"})

	// Write log entries
	for _, entry := range entries {
		writer.Write([]string{entry.Timestamp, entry.Level, entry.Line})
	}
	return nil
}

// User authentication
func authenticate(username, password string) bool {
	if pass, ok := userTokens[username]; ok {
		return pass == password
	}
	return false
}

// Rate limiting
func isRateLimited(userIP string) bool {
	requestMutex.Lock()
	defer requestMutex.Unlock()

	if count, ok := requestCount[userIP]; ok && count >= requestLimit {
		return true
	}

	requestCount[userIP]++
	time.AfterFunc(timeWindow, func() {
		requestMutex.Lock()
		defer requestMutex.Unlock()
		requestCount[userIP]--
	})
	return false
}

func main() {
	http.HandleFunc("/logs", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		userIP := r.RemoteAddr
		if isRateLimited(userIP) {
			http.Error(w, "Rate limit exceeded", http.StatusTooManyRequests)
			return
		}

		username, password, ok := r.BasicAuth()
		if !ok || !authenticate(username, password) {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}

		queries := r.URL.Query()["q"]
		logLevel := r.URL.Query().Get("level")
		limitStr := r.URL.Query().Get("limit")
		offsetStr := r.URL.Query().Get("offset")
		startTimeStr := r.URL.Query().Get("start")
		endTimeStr := r.URL.Query().Get("end")
		export := r.URL.Query().Get("export")

		if len(queries) == 0 {
			http.Error(w, "Query parameter 'q' is required", http.StatusBadRequest)
			return
		}

		// Convert limit and offset from string to int
		limit := 10 // Default limit
		offset := 0 // Default offset

		if limitStr != "" {
			var err error
			limit, err = strconv.Atoi(limitStr)
			if err != nil || limit < 0 {
				http.Error(w, "Invalid limit parameter", http.StatusBadRequest)
				return
			}
		}
		if offsetStr != "" {
			var err error
			offset, err = strconv.Atoi(offsetStr)
			if err != nil || offset < 0 {
				http.Error(w, "Invalid offset parameter", http.StatusBadRequest)
				return
			}
		}

		// Parse time range if provided
		startTime := time.Time{}
		endTime := time.Now()

		if startTimeStr != "" {
			var err error
			startTime, err = time.Parse("2006-01-02T15:04:05", startTimeStr) // Expecting ISO 8601 format
			if err != nil {
				http.Error(w, "Invalid start time format", http.StatusBadRequest)
				return
			}
		}
		if endTimeStr != "" {
			var err error
			endTime, err = time.Parse("2006-01-02T15:04:05", endTimeStr) // Expecting ISO 8601 format
			if err != nil {
				http.Error(w, "Invalid end time format", http.StatusBadRequest)
				return
			}
		}

		// Analyze logs with the provided queries
		results, matchCount, err := analyzeLogs(queries, logLevel, limit, offset, startTime, endTime)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		if export == "true" {
			err := exportLogsToCSV(results, "exported_logs.csv")
			if err != nil {
				http.Error(w, "Failed to export logs", http.StatusInternalServerError)
				return
			}
			w.Write([]byte("Logs exported successfully to exported_logs.csv"))
			return
		}

		// Return results as JSON
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"count":  matchCount,
			"results": results,
		})
	})

	log.Println("Starting Log Analyzer server on :8083")
	log.Fatal(http.ListenAndServe(":8083", nil))
}

