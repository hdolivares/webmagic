"""
Development server startup script.
"""
import uvicorn
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))


def main():
    """Start the FastAPI development server."""
    print(">> Starting WebMagic API Server...")
    print(">> API Docs will be available at: http://localhost:8000/docs")
    print(">> Health check: http://localhost:8000/health")
    print("\n" + "=" * 60 + "\n")
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
