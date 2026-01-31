#!/bin/sh
# Kong API Gateway Initialization Script
# Configures services, routes, and plugins for Sprint-1

set -e

KONG_ADMIN_URL="${KONG_ADMIN_URL:-http://kong:8001}"
MAX_RETRIES=30
RETRY_INTERVAL=2

echo "=========================================="
echo "Kong Gateway Initialization"
echo "=========================================="

# Wait for Kong Admin API
echo "Waiting for Kong Admin API..."
i=1
while [ $i -le $MAX_RETRIES ]; do
    if wget -q -O /dev/null "$KONG_ADMIN_URL/status" 2>/dev/null; then
        echo "Kong Admin API is ready!"
        break
    fi
    echo "  Attempt $i/$MAX_RETRIES - waiting ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
    i=$((i + 1))
done

if ! wget -q -O /dev/null "$KONG_ADMIN_URL/status" 2>/dev/null; then
    echo "ERROR: Kong Admin API not available"
    exit 1
fi

# ==========================================
# Register Services
# ==========================================
echo ""
echo "Registering services..."

echo "  -> Creating auth-service..."
wget -q -O /dev/null --post-data "name=auth-service&url=http://auth-service:8000&retries=3&connect_timeout=10000&read_timeout=60000&write_timeout=60000" \
    "$KONG_ADMIN_URL/services" 2>/dev/null || echo "    (may already exist)"

# ==========================================
# Create Routes
# ==========================================
echo ""
echo "Creating routes..."

# Public: Login (no auth)
echo "  -> Creating auth-login route..."
wget -q -O /dev/null --post-data "name=auth-login&paths[]=/api/v1/auth/login&methods[]=POST&methods[]=OPTIONS&strip_path=false" \
    "$KONG_ADMIN_URL/services/auth-service/routes" 2>/dev/null || echo "    (may already exist)"

# Public: Validate (no auth)
echo "  -> Creating auth-validate route..."
wget -q -O /dev/null --post-data "name=auth-validate&paths[]=/api/v1/auth/validate&methods[]=POST&methods[]=OPTIONS&strip_path=false" \
    "$KONG_ADMIN_URL/services/auth-service/routes" 2>/dev/null || echo "    (may already exist)"

# Protected: Auth endpoints
echo "  -> Creating auth-protected route..."
wget -q -O /dev/null --post-data "name=auth-protected&paths[]=/api/v1/auth&methods[]=GET&methods[]=POST&methods[]=PUT&methods[]=DELETE&methods[]=OPTIONS&strip_path=false" \
    "$KONG_ADMIN_URL/services/auth-service/routes" 2>/dev/null || echo "    (may already exist)"

# Protected: Users endpoints
echo "  -> Creating users-routes..."
wget -q -O /dev/null --post-data "name=users-routes&paths[]=/api/v1/users&methods[]=GET&methods[]=POST&methods[]=PUT&methods[]=DELETE&methods[]=OPTIONS&strip_path=false" \
    "$KONG_ADMIN_URL/services/auth-service/routes" 2>/dev/null || echo "    (may already exist)"

# Protected: Admin endpoints
echo "  -> Creating admin-routes..."
wget -q -O /dev/null --post-data "name=admin-routes&paths[]=/api/v1/admin&methods[]=GET&methods[]=POST&methods[]=PUT&methods[]=DELETE&methods[]=OPTIONS&strip_path=false" \
    "$KONG_ADMIN_URL/services/auth-service/routes" 2>/dev/null || echo "    (may already exist)"

# Protected: Projects endpoints
echo "  -> Creating projects-routes..."
wget -q -O /dev/null --post-data "name=projects-routes&paths[]=/api/v1/projects&methods[]=GET&methods[]=POST&methods[]=PUT&methods[]=DELETE&methods[]=OPTIONS&strip_path=false" \
    "$KONG_ADMIN_URL/services/auth-service/routes" 2>/dev/null || echo "    (may already exist)"

# Health check
echo "  -> Creating health-check route..."
wget -q -O /dev/null --post-data "name=health-check&paths[]=/health&methods[]=GET&strip_path=false" \
    "$KONG_ADMIN_URL/services/auth-service/routes" 2>/dev/null || echo "    (may already exist)"

# ==========================================
# Enable Global Plugins
# ==========================================
echo ""
echo "Enabling plugins..."

# CORS (Global)
# Allow origins from environment variable or use defaults
# Format: comma-separated list, e.g., "http://localhost:3000,http://localhost:8080,http://72.62.17.132:8080"
CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,http://localhost:8080}"

echo "  -> Configuring CORS with origins: $CORS_ORIGINS..."

# Check if CORS plugin already exists
CORS_PLUGINS=$(wget -q -O - "$KONG_ADMIN_URL/plugins?name=cors" 2>/dev/null)
CORS_PLUGIN_ID=$(echo "$CORS_PLUGINS" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

# Build CORS origins for curl format (space-separated -d flags)
# Convert comma-separated list to multiple -d flags
CORS_CURL_PARAMS=""
for origin in $(echo "$CORS_ORIGINS" | tr ',' ' '); do
    CORS_CURL_PARAMS="$CORS_CURL_PARAMS -d config.origins=$origin"
done

if [ -n "$CORS_PLUGIN_ID" ]; then
    # Update existing CORS plugin
    echo "    Updating existing CORS plugin: $CORS_PLUGIN_ID..."
    # Use docker run with alpine/curl since busybox wget doesn't support PATCH/DELETE
    if command -v docker >/dev/null 2>&1; then
        docker run --rm --network crm-network alpine/curl:latest -sS -X PATCH \
            "http://kong:8001/plugins/$CORS_PLUGIN_ID" \
            $CORS_CURL_PARAMS \
            >/dev/null 2>&1 && echo "    ✓ CORS plugin updated successfully" || echo "    ✗ Failed to update CORS plugin"
    else
        echo "    ⚠ Docker not available, cannot update CORS plugin"
    fi
else
    # Create new CORS plugin
    echo "    Creating new CORS plugin..."
    # Build CORS POST data - convert comma-separated list to Kong array format
    CORS_DATA="name=cors"
    CORS_ORIGINS_PARAM=$(echo "$CORS_ORIGINS" | sed 's/,/\&config.origins[]=/g')
    CORS_DATA="${CORS_DATA}&config.origins[]=${CORS_ORIGINS_PARAM}"
    
    # Add methods, headers, and other CORS config
    CORS_DATA="${CORS_DATA}&config.methods[]=GET&config.methods[]=POST&config.methods[]=PUT&config.methods[]=DELETE&config.methods[]=PATCH&config.methods[]=OPTIONS&config.headers[]=Accept&config.headers[]=Content-Type&config.headers[]=Authorization&config.headers[]=X-Request-ID&config.credentials=true&config.max_age=3600"
    
    wget -q -O /dev/null --post-data "$CORS_DATA" \
        "$KONG_ADMIN_URL/plugins" 2>/dev/null && echo "    ✓ CORS plugin created successfully" || echo "    ✗ Failed to create CORS plugin"
fi

# Rate Limiting (Global)
echo "  -> Enabling rate limiting..."
wget -q -O /dev/null --post-data "name=rate-limiting&config.minute=100&config.policy=local&config.fault_tolerant=true" \
    "$KONG_ADMIN_URL/plugins" 2>/dev/null || echo "    (may already exist)"

# ==========================================
# Verification
# ==========================================
echo ""
echo "=========================================="
echo "Configuration Complete!"
echo "=========================================="
echo ""
echo "Kong Gateway is ready!"
echo "  Proxy: http://localhost:8000"
echo "  Admin: http://localhost:8001"
echo ""
echo "Testing endpoints..."
echo "  Login: POST http://localhost:8000/api/v1/auth/login"
echo "  Validate: POST http://localhost:8000/api/v1/auth/validate"
echo "  Users/Me: GET http://localhost:8000/api/v1/users/me"
