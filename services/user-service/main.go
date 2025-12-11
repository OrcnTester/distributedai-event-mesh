package main

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/segmentio/kafka-go"
)


// ==== Tenant Context Types ====
type TenantInfo struct {
	TenantID string
	UserID string
}

// ==== Context key type
type tenantKeyType string

const tenantKey tenantKeyType = "tenantInfo"

// parseDevToken simulates JWT parsing.
// Dev format: "tenant-id:user-id"
func parseDevToken(authHeader string)(*TenantInfo, error){
	if authHeader == "" {
		return nil, errors.New("missing Authorization header")
	}

	if !strings.HasPrefix(authHeader, "Bearer "){
		return nil, errors.New("invalid Authorization header format")
	}

	token := strings.TrimPrefix(authHeader, "Bearer ")
	parts := strings.Split(token, ":")
	if len(parts) != 2 {
		return nil, errors.New("invalid token format, expected tenant-id:user-id")
	}

	return &TenantInfo{
		TenantID: parts[0],
		UserID: parts[1],
	}, nil
}

func tenantMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ti, err := parseDevToken(r.Header.Get("Authorization"))
		if err != nil {
			log.Println("Auth error:", err)
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}

		ctx := context.WithValue(r.Context(), tenantKey, ti)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// Helper: handler içinde tenant erişimi
func getTenantInfo(r *http.Request) *TenantInfo {
	ti, _ := r.Context().Value(tenantKey).(*TenantInfo)
	return ti
}

type User struct {
	ID       int    `json:"id"`
	Email    string `json:"email"`
	Name     string `json:"name"`
	TenantID string `json:"tenantId"`
}

var writer *kafka.Writer

func main() {
	// 1) Kafka writer'ı initialize et
	writer = kafka.NewWriter(kafka.WriterConfig{
		Brokers:  []string{"redpanda:9092"}, // docker-compose içindeki redpanda service adı
		Topic:    "user.events",            // ai-gateway'in dinlediği topic
		Balancer: &kafka.LeastBytes{},
	})
	defer writer.Close()
	
	mux := http.NewServeMux()

	// Public endpoint
	mux.HandleFunc("/health", healthHandler)

	// Protected endpoints (require Authorization)
	mux.Handle("/users", tenantMiddleware(http.HandlerFunc(usersHandler)))
	mux.Handle("/users/create", tenantMiddleware(http.HandlerFunc(createUserHandler)))

	log.Println("user-service running on :8081")
	if err := http.ListenAndServe(":8081", mux); err != nil {
		log.Fatal(err)
	}
}


func healthHandler(w http.ResponseWriter, r *http.Request) {
	resp := map[string]string{
		"status":  "OK",
		"service": "user-service",
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}
func createUserHandler(w http.ResponseWriter, r *http.Request) {
	tenant := getTenantInfo(r)
	if tenant == nil {
		http.Error(w, "missing tenant", http.StatusUnauthorized)
		return
	}

	var user User
	if err := json.NewDecoder(r.Body).Decode(&user); err != nil {
		http.Error(w, "invalid body", http.StatusBadRequest)
		return
	}

	// Fake ID
	user.ID = 100 + int(time.Now().Unix()%900)
	user.TenantID = tenant.TenantID

	// Publish event to Kafka
	eventBytes, _ := json.Marshal(user)
	err := writer.WriteMessages(context.Background(),
		kafka.Message{
			Value: eventBytes,
		},
	)

	if err != nil {
		log.Println("Failed to publish event:", err)
		http.Error(w, "Kafka publish error", http.StatusInternalServerError)
		return
	}

	log.Printf("Event published (tenant=%s user=%d)", tenant.TenantID, user.ID)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(user)
}


func usersHandler(w http.ResponseWriter, r *http.Request) {
	tenant := getTenantInfo(r)
	if tenant == nil {
		http.Error(w, "missing tenant", http.StatusUnauthorized)
		return
	}

// Demo data
	users := []User{
		{ID: 1, Email: "alice@example.com", Name: "Alice", TenantID: "tenant-a"},
		{ID: 2, Email: "bob@example.com", Name: "Bob", TenantID: "tenant-b"},
	}

	var filtered []User
	for _, u := range users {
		if u.TenantID == tenant.TenantID {
			filtered = append(filtered, u)
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(filtered)
}
