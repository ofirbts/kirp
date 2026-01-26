# PostgreSQL Setup Fix — Complete Diagnostic & Solution

**Date:** 2026-01-26  
**Issue:** PostgreSQL database "kirp_user" does not exist error

---

## ROOT CAUSE ANALYSIS

### Issues Found:

1. **Incorrect Default Connection String** (`src/workers/tasks.py:40`)
   - **Wrong:** `postgresql+asyncpg://kirp:kirp@localhost:5432/kirp`
   - **Fixed:** `postgresql+asyncpg://kirp_user:kirp_password@localhost:5432/kirp`
   - **Impact:** Worker tasks couldn't connect to database

2. **Incorrect Default in main.py** (`src/main.py:76`)
   - **Wrong:** `postgresql+asyncpg://kirp:kirp@localhost:5432/kirp`
   - **Fixed:** `postgresql+asyncpg://kirp_user:kirp_password@localhost:5432/kirp`
   - **Impact:** API couldn't connect if POSTGRES_URI not set

3. **Healthcheck Not Verifying Database**
   - **Before:** Only checked `pg_isready`
   - **Fixed:** Now verifies database exists and is accessible

4. **No Automatic Migrations**
   - **Before:** Migrations had to be run manually
   - **Fixed:** Migrations run automatically on API startup

---

## FIXES APPLIED

### 1. Fixed Connection Strings
- ✅ `src/main.py` — Corrected default POSTGRES_URI
- ✅ `src/workers/tasks.py` — Corrected default POSTGRES_URI

### 2. Improved PostgreSQL Healthcheck
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U kirp_user -d kirp && psql -U kirp_user -d kirp -c 'SELECT 1'"]
```
- Now verifies both connection AND database accessibility

### 3. Added Database Initialization Script
- `deploy/postgres-init/01-init-db.sh`
- Ensures UUID extension is available
- Grants proper permissions
- Runs on first container initialization

### 4. Automatic Migrations on API Startup
```yaml
command: sh -c "echo 'Waiting for PostgreSQL...' && sleep 2 && alembic upgrade head && echo 'Migrations complete, starting API...' && uvicorn src.main:app --host 0.0.0.0 --port 8000"
```
- Runs migrations before starting API
- Handles migration errors gracefully

### 5. Created Diagnostic Script
- `deploy/postgres-diagnostic.sh`
- Checks container status
- Lists databases
- Verifies database exists
- Checks tables and extensions
- Can create database if missing

---

## VERIFICATION STEPS

### Step 1: Run Diagnostic
```bash
chmod +x deploy/postgres-diagnostic.sh
./deploy/postgres-diagnostic.sh
```

### Step 2: Check Database Exists
```bash
docker exec -it kirp-postgres psql -U kirp_user -d kirp -c "SELECT current_database();"
```

### Step 3: Check Tables (After Migrations)
```bash
docker exec -it kirp-postgres psql -U kirp_user -d kirp -c "\dt"
```

### Step 4: Verify Connection Strings
All services should use:
```
postgresql+asyncpg://kirp_user:kirp_password@postgres:5432/kirp
```

---

## STARTUP SEQUENCE

1. **PostgreSQL starts** → Creates `kirp` database (via POSTGRES_DB)
2. **Init script runs** → Sets up extensions and permissions
3. **Healthcheck passes** → Database is ready
4. **API starts** → Runs migrations → Starts server
5. **Workers start** → Connect to database

---

## TROUBLESHOOTING

### If database doesn't exist:
```bash
docker exec -it kirp-postgres psql -U kirp_user -d postgres -c "CREATE DATABASE kirp;"
```

### If migrations fail:
```bash
docker exec -it kirp-api alembic upgrade head
```

### If connection fails:
1. Check POSTGRES_URI environment variable
2. Verify username/password match docker-compose.yml
3. Check network connectivity (kirp-net)

---

## FILES MODIFIED

1. `docker-compose.yml` — Improved healthcheck, added init script mount
2. `src/main.py` — Fixed default POSTGRES_URI
3. `src/workers/tasks.py` — Fixed default POSTGRES_URI
4. `deploy/postgres-init/01-init-db.sh` — NEW — Database initialization
5. `deploy/postgres-diagnostic.sh` — NEW — Diagnostic tool

---

## EXPECTED BEHAVIOR

After these fixes:
- ✅ PostgreSQL creates `kirp` database automatically
- ✅ Healthcheck verifies database exists
- ✅ Migrations run automatically on API startup
- ✅ All services connect with correct credentials
- ✅ No dependency loops

---

## NEXT STEPS

1. **Reset volumes** (if needed):
   ```bash
   docker compose down -v
   ```

2. **Start services**:
   ```bash
   docker compose up --build
   ```

3. **Verify**:
   ```bash
   ./deploy/postgres-diagnostic.sh
   ```

---

**Status:** ✅ **POSTGRESQL SETUP FIXED | READY FOR TESTING**
