# 1) Build stage
FROM golang:1.25 AS builder

WORKDIR /app

# Go mod dosyalarını kopyala (şimdilik sadece go.mod varsa)
COPY go.mod ./
RUN go mod download

# Tüm kodu kopyala
COPY . .

# Binary derle
RUN go build -o user-service .

# 2) Run stage
FROM gcr.io/distroless/base-debian12

WORKDIR /app

COPY --from=builder /app/user-service .

EXPOSE 8081

ENTRYPOINT ["./user-service"]
