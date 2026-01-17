#!/usr/bin/env bash
#
# Setup PostgreSQL database for SENTINEL compliance audits
#
# Usage: ./scripts/setup_compliance_db.sh
#

set -e

echo "🔧 Setting up SENTINEL compliance database..."

# Check if PostgreSQL is running
if ! docker-compose ps postgres | grep -q "Up"; then
    echo "❌ PostgreSQL is not running. Start it with: docker-compose up -d postgres"
    exit 1
fi

# Apply schema
echo "📋 Applying compliance audit schema..."
docker-compose exec -T postgres psql -U neutron -d neutron < neutron/compliance/schema.sql

echo "✅ Compliance database setup complete!"
echo ""
echo "Verify with:"
echo "  docker-compose exec postgres psql -U neutron -d neutron -c '\\dt compliance*'"
