#!/bin/bash
# PostgreSQL Diagnostic Script for KIRP

set -e

echo "=== KIRP PostgreSQL Diagnostic ==="
echo ""

# Check if container is running
if ! docker ps | grep -q kirp-postgres; then
    echo "❌ ERROR: kirp-postgres container is not running"
    exit 1
fi

echo "✅ PostgreSQL container is running"
echo ""

# Check connection
echo "Testing connection..."
docker exec kirp-postgres psql -U kirp_user -d kirp -c "SELECT version();" || {
    echo "❌ ERROR: Cannot connect to database 'kirp'"
    echo ""
    echo "Checking what databases exist:"
    docker exec kirp-postgres psql -U kirp_user -d postgres -c "\l"
    exit 1
}

echo "✅ Connection successful"
echo ""

# List databases
echo "Available databases:"
docker exec kirp-postgres psql -U kirp_user -d postgres -c "\l"
echo ""

# Check if kirp database exists
echo "Checking if 'kirp' database exists..."
DB_EXISTS=$(docker exec kirp-postgres psql -U kirp_user -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='kirp'")
if [ "$DB_EXISTS" = "1" ]; then
    echo "✅ Database 'kirp' exists"
else
    echo "❌ ERROR: Database 'kirp' does not exist"
    echo "Creating database..."
    docker exec kirp-postgres psql -U kirp_user -d postgres -c "CREATE DATABASE kirp;"
    echo "✅ Database 'kirp' created"
fi
echo ""

# Check tables
echo "Tables in 'kirp' database:"
docker exec kirp-postgres psql -U kirp_user -d kirp -c "\dt" || echo "No tables found (migrations may not have run)"
echo ""

# Check extensions
echo "Installed extensions:"
docker exec kirp-postgres psql -U kirp_user -d kirp -c "SELECT * FROM pg_extension;"
echo ""

# Check user permissions
echo "User permissions:"
docker exec kirp-postgres psql -U kirp_user -d kirp -c "\du kirp_user"
echo ""

echo "=== Diagnostic Complete ==="
