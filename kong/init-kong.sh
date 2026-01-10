#!/bin/bash
# Kong initialization script for Card Service
# This script configures Kong with the Card Service routes and plugins

set -e

KONG_ADMIN_URL=${KONG_ADMIN_URL:-http://kong:8001}
CARD_SERVICE_URL=${CARD_SERVICE_URL:-http://card-service:8000}

echo "Waiting for Kong Admin API to be ready..."
until curl -s $KONG_ADMIN_URL > /dev/null; do
  echo "Waiting for Kong Admin API..."
  sleep 2
done

echo "Kong Admin API is ready!"

# Create service
echo "Creating Card Service..."
curl -i -X POST $KONG_ADMIN_URL/services/ \
  --data "name=card-service" \
  --data "url=$CARD_SERVICE_URL" || echo "Service may already exist"

# Create routes
echo "Creating routes..."

# Pokemon list route
curl -i -X POST $KONG_ADMIN_URL/services/card-service/routes \
  --data "name=card-service-pokemon-list" \
  --data "paths[]=/api/pokemon" \
  --data "methods[]=GET" \
  --data "methods[]=OPTIONS" || echo "Route may already exist"

# Pokemon detail route (with regex)
curl -i -X POST $KONG_ADMIN_URL/services/card-service/routes \
  --data "name=card-service-pokemon-detail" \
  --data "paths[]=~/api/pokemon/[^/]+" \
  --data "methods[]=GET" \
  --data "methods[]=OPTIONS" || echo "Route may already exist"

# Compare route
curl -i -X POST $KONG_ADMIN_URL/services/card-service/routes \
  --data "name=card-service-compare" \
  --data "paths[]=/api/compare" \
  --data "methods[]=GET" \
  --data "methods[]=OPTIONS" || echo "Route may already exist"

# Types route
curl -i -X POST $KONG_ADMIN_URL/services/card-service/routes \
  --data "name=card-service-types" \
  --data "paths[]=/api/types" \
  --data "methods[]=GET" \
  --data "methods[]=OPTIONS" || echo "Route may already exist"

# Abilities route
curl -i -X POST $KONG_ADMIN_URL/services/card-service/routes \
  --data "name=card-service-abilities" \
  --data "paths[]=/api/abilities" \
  --data "methods[]=GET" \
  --data "methods[]=OPTIONS" || echo "Route may already exist"

# Evolution route
curl -i -X POST $KONG_ADMIN_URL/services/card-service/routes \
  --data "name=card-service-evolution" \
  --data "paths[]=~/api/evolution/[^/]+" \
  --data "methods[]=GET" \
  --data "methods[]=OPTIONS" || echo "Route may already exist"

# Coverage route
curl -i -X POST $KONG_ADMIN_URL/services/card-service/routes \
  --data "name=card-service-coverage" \
  --data "paths[]=/api/coverage" \
  --data "methods[]=GET" \
  --data "methods[]=OPTIONS" || echo "Route may already exist"

# Average route
curl -i -X POST $KONG_ADMIN_URL/services/card-service/routes \
  --data "name=card-service-average" \
  --data "paths[]=/api/average" \
  --data "methods[]=GET" \
  --data "methods[]=OPTIONS" || echo "Route may already exist"

# Enable CORS plugin
echo "Enabling CORS plugin..."
curl -i -X POST $KONG_ADMIN_URL/services/card-service/plugins \
  --data "name=cors" \
  --data "config.origins=*" \
  --data "config.methods=GET,POST,PUT,DELETE,OPTIONS,PATCH" \
  --data "config.headers=Accept,Accept-Version,Content-Length,Content-MD5,Content-Type,Date,Authorization,X-Auth-Token" \
  --data "config.exposed_headers=X-Auth-Token" \
  --data "config.credentials=true" \
  --data "config.max_age=3600" || echo "Plugin may already exist"

# Enable rate limiting
echo "Enabling rate limiting..."
curl -i -X POST $KONG_ADMIN_URL/services/card-service/plugins \
  --data "name=rate-limiting" \
  --data "config.minute=100" \
  --data "config.hour=1000" \
  --data "config.policy=local" || echo "Plugin may already exist"

# Enable request ID
echo "Enabling request ID..."
curl -i -X POST $KONG_ADMIN_URL/services/card-service/plugins \
  --data "name=request-id" \
  --data "config.header_name=X-Request-ID" \
  --data "config.echo_downstream=true" || echo "Plugin may already exist"

echo "Kong initialization complete!"
