# WebMagic Quick Start Guide

Get WebMagic running locally in 5 minutes! 🚀

## 1️⃣ Install Redis

**Windows (Choose one):**

### Option A: Redis for Windows
```bash
# Download installer:
https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.msi

# After install, start Redis:
redis-server
```

### Option B: WSL (Recommended)
```bash
# Install Ubuntu on WSL
wsl --install Ubuntu

# Inside WSL:
wsl
sudo apt update
sudo apt install redis-server
redis-server
```

### Verify Redis:
```bash
redis-cli ping
# Should return: PONG
```

## 2️⃣ Configure Environment

```bash
# Navigate to backend
cd backend

# Copy environment template
copy env.template .env

# Edit .env with your credentials
notepad .env
```

**Required settings:**
```bash
DATABASE_URL=postgresql://...  # Your Supabase URL
SECRET_KEY=your-secret-key
ANTHROPIC_API_KEY=sk-ant-...
REDIS_URL=redis://localhost:6379/0
```

## 3️⃣ Install Dependencies

### Backend:
```bash
cd backend
pip install -r requirements.txt
```

### Frontend:
```bash
cd frontend
npm install
```

## 4️⃣ Run Health Check

```bash
# From project root
python check_services.py
```

This will verify:
- ✓ Redis is running
- ✓ Database connection works
- ✓ Configuration is valid

## 5️⃣ Start Services

### Option A: All at Once (Windows)
```bash
# From project root
start_all.bat
```

This opens 4 windows:
- API (http://localhost:8000)
- Celery Worker
- Celery Beat
- Frontend (http://localhost:3000)

### Option B: Manually

**Terminal 1 - API:**
```bash
cd backend
python start.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - Celery Worker (Optional):**
```bash
cd backend
python start_worker.py
```

**Terminal 4 - Celery Beat (Optional):**
```bash
cd backend
python start_beat.py
```

## 6️⃣ Access WebMagic

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

**Default login:**
- Email: (your admin email from database)
- Password: (your admin password)

## 7️⃣ Run Tests

```bash
# Test all phases
python test_all.py

# Test individual phases
python backend/test_api.py        # Phase 1
python backend/test_phase2.py     # Phase 2
python backend/test_phase3.py     # Phase 3
python backend/test_phase4.py     # Phase 4
python backend/test_phase5.py     # Phase 5

# Test conductor
python backend/conductor.py --status
python backend/conductor.py --mode once
```

## 8️⃣ Verify Everything Works

### ✅ API Test
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

### ✅ Frontend Test
Open browser: http://localhost:3000
- Should see login page
- Login should work
- All pages should load

### ✅ Celery Test
```bash
cd backend
python -c "from tasks.monitoring import health_check; import asyncio; print(asyncio.run(health_check()))"
# Should return health status
```

## 🚨 Troubleshooting

### Redis Not Running
```bash
# Check if Redis is installed
redis-cli --version

# Start Redis
redis-server

# Test connection
redis-cli ping
```

### Database Connection Failed
```bash
# Check DATABASE_URL in .env
cat backend/.env | findstr DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

### Port Already in Use
```bash
# Check what's using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /F /PID <PID>
```

### Frontend Won't Start
```bash
# Clear cache
cd frontend
rm -rf node_modules
npm install

# Check for port conflicts (3000)
netstat -ano | findstr :3000
```

### Celery Can't Connect
```bash
# Verify Redis is running
redis-cli ping

# Check REDIS_URL in .env
echo $REDIS_URL

# Restart Redis
# Windows: Close redis-server window and restart
# WSL: wsl sudo service redis-server restart
```

## 📚 Next Steps

Once everything is running:

1. **Read the full guide**: `LOCAL_TESTING.md`
2. **Test each phase** individually
3. **Run integration tests** end-to-end
4. **Monitor performance** and resource usage
5. **Document any issues** for VPS deployment

## 🎯 Ready for Production?

After local testing passes:
- [ ] All services start successfully
- [ ] All tests pass
- [ ] Frontend loads and works
- [ ] Can scrape and qualify leads
- [ ] Can generate websites (test 1-2)
- [ ] Can create and send campaigns
- [ ] Conductor runs complete cycle
- [ ] No critical errors in logs

**Then you're ready for VPS deployment!** 🚀

---

## Quick Reference

| Service | URL | Command |
|---------|-----|---------|
| API | http://localhost:8000 | `python backend/start.py` |
| API Docs | http://localhost:8000/docs | Same as above |
| Frontend | http://localhost:3000 | `cd frontend && npm run dev` |
| Health Check | - | `python check_services.py` |
| Run Tests | - | `python test_all.py` |
| Conductor | - | `python backend/conductor.py --status` |

**Stop all services:**
- Windows: Close all terminal windows or Ctrl+C in start_all.bat
- Manual: Ctrl+C in each terminal
