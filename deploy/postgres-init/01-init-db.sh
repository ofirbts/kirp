#!/bin/bash
set -e

echo "PostgreSQL initialization script starting..."

# The database 'kirp' is automatically created by POSTGRES_DB
# This script ensures extensions and permissions are set up

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Ensure uuid extension is available
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    -- Grant all privileges (already granted by default, but explicit)
    GRANT ALL PRIVILEGES ON DATABASE kirp TO kirp_user;
    
    -- Verify database is ready
    SELECT 'Database kirp initialized successfully' AS status;
EOSQL

echo "PostgreSQL initialization completed successfully."
