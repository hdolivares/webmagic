"""
Quick health check for all WebMagic services.
"""
import requests
import redis
import sys
import psycopg2
from urllib.parse import urlparse

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def check_redis(url="redis://localhost:6379/0"):
    """Check Redis connection."""
    try:
        r = redis.from_url(url)
        r.ping()
        print(f"{GREEN}✓ Redis is running{RESET}")
        return True
    except Exception as e:
        print(f"{RED}✗ Redis is NOT running{RESET}")
        print(f"  Error: {str(e)}")
        return False


def check_database():
    """Check PostgreSQL connection."""
    try:
        import os
        from dotenv import load_dotenv
        
        # Load .env from backend/
        env_path = os.path.join('backend', '.env')
        load_dotenv(env_path)
        
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            print(f"{YELLOW}⚠ DATABASE_URL not found in .env{RESET}")
            return False
        
        # Parse URL
        result = urlparse(db_url)
        conn = psycopg2.connect(
            dbname=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        conn.close()
        
        print(f"{GREEN}✓ Database connection successful{RESET}")
        return True
        
    except Exception as e:
        print(f"{RED}✗ Database connection failed{RESET}")
        print(f"  Error: {str(e)}")
        return False


def check_api(url="http://localhost:8000"):
    """Check FastAPI server."""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            print(f"{GREEN}✓ API is running{RESET}")
            print(f"  URL: {url}")
            print(f"  Docs: {url}/docs")
            return True
        else:
            print(f"{YELLOW}⚠ API responded with status {response.status_code}{RESET}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"{RED}✗ API is NOT running{RESET}")
        print(f"  Start with: python backend/start.py")
        return False
    except Exception as e:
        print(f"{RED}✗ API check failed{RESET}")
        print(f"  Error: {str(e)}")
        return False


def check_frontend(url="http://localhost:3000"):
    """Check frontend dev server."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"{GREEN}✓ Frontend is running{RESET}")
            print(f"  URL: {url}")
            return True
        else:
            print(f"{YELLOW}⚠ Frontend responded with status {response.status_code}{RESET}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"{RED}✗ Frontend is NOT running{RESET}")
        print(f"  Start with: cd frontend && npm run dev")
        return False
    except Exception as e:
        print(f"{RED}✗ Frontend check failed{RESET}")
        print(f"  Error: {str(e)}")
        return False


def check_celery():
    """Check Celery workers."""
    try:
        from celery_app import celery_app
        
        # Check if workers are active
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        if stats:
            worker_count = len(stats)
            print(f"{GREEN}✓ Celery workers running ({worker_count} worker(s)){RESET}")
            for worker, stat in stats.items():
                print(f"  - {worker}")
            return True
        else:
            print(f"{RED}✗ No Celery workers running{RESET}")
            print(f"  Start with: python backend/start_worker.py")
            return False
            
    except Exception as e:
        print(f"{RED}✗ Celery check failed{RESET}")
        print(f"  Error: {str(e)}")
        print(f"  Start with: python backend/start_worker.py")
        return False


def main():
    """Run all health checks."""
    print("\n" + "="*60)
    print("WebMagic Health Check".center(60))
    print("="*60 + "\n")
    
    results = {}
    
    # Check services
    print("Checking services...\n")
    
    results['Redis'] = check_redis()
    results['Database'] = check_database()
    results['API'] = check_api()
    results['Frontend'] = check_frontend()
    
    # Celery check (optional, might not be running)
    print("\nChecking background workers...\n")
    results['Celery'] = check_celery()
    
    # Summary
    print("\n" + "="*60)
    print("Summary".center(60))
    print("="*60 + "\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for service, status in results.items():
        status_str = f"{GREEN}RUNNING{RESET}" if status else f"{RED}STOPPED{RESET}"
        print(f"{service:.<40} {status_str}")
    
    print(f"\n{passed}/{total} services running\n")
    
    if passed == total:
        print(f"{GREEN}All services are running! ✨{RESET}")
        return True
    elif results.get('API') and results.get('Redis'):
        print(f"{YELLOW}Core services are running (API + Redis){RESET}")
        print(f"{YELLOW}Optional services need attention{RESET}")
        return True
    else:
        print(f"{RED}Critical services are missing!{RESET}")
        print("\nTo start all services:")
        print("  Windows: start_all.bat")
        print("  Manual: See LOCAL_TESTING.md")
        return False


if __name__ == "__main__":
    try:
        import sys
        sys.path.insert(0, 'backend')
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
