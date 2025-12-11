package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"time"

	"github.com/segmentio/kafka-go"
)

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

	// 2) HTTP handler'ları kaydet
	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/users", usersHandler)
	http.HandleFunc("/users/create", createUserHandler)

	log.Println("user-service running on :8081")
	if err := http.ListenAndServe(":8081", nil); err != nil {
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
	tenantID := r.Header.Get("X-Tenant-Id")
	if tenantID == "" {
		http.Error(w, "missing X-Tenant-Id header", http.StatusBadRequest)
		return
	}

	var user User
	if err := json.NewDecoder(r.Body).Decode(&user); err != nil {
		http.Error(w, "invalid body", http.StatusBadRequest)
		return
	}

	// Fake ID
	user.ID = 100 + int(time.Now().Unix()%900)
	user.TenantID = tenantID

	// --- Kafka publish ---
	if writer == nil {
		log.Println("Kafka writer is nil, skipping publish")
	} else {
		eventBytes, _ := json.Marshal(user)

		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		err := writer.WriteMessages(ctx,
			kafka.Message{
				Value: eventBytes,
			},
		)
		if err != nil {
			log.Println("Failed to publish event:", err)
			// İster burada 500 dön, ister sadece logla.
			// http.Error(w, "Kafka publish error", http.StatusInternalServerError)
			// return
		} else {
			log.Println("Event published:", string(eventBytes))
		}
	}
	// --- Kafka publish son ---

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(user)
}


func usersHandler(w http.ResponseWriter, r *http.Request) {
	tenantID := r.Header.Get("X-Tenant-Id")
	if tenantID == "" {
		http.Error(w, "missing X-Tenant-Id header", http.StatusBadRequest)
		return
	}

	users := []User{
		{ID: 1, Email: "alice@example.com", Name: "Alice", TenantID: "tenant-a"},
		{ID: 2, Email: "bob@example.com", Name: "Bob", TenantID: "tenant-b"},
	}

	var filtered []User
	for _, u := range users {
		if u.TenantID == tenantID {
			filtered = append(filtered, u)
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(filtered)
}
