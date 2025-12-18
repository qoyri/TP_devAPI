FROM caddy:2.9-alpine

# Install openssl for cert generation
RUN apk add --no-cache openssl

# Create certs directory
RUN mkdir -p /etc/caddy/certs

# Generate self-signed certificate
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/caddy/certs/key.pem \
    -out /etc/caddy/certs/cert.pem \
    -subj "/C=FR/ST=France/L=Paris/O=DevAPI/CN=localhost"

# Copy Caddyfile configuration
COPY Caddyfile /etc/caddy/Caddyfile

EXPOSE 8443

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile"]
