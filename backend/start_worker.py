"""
Start Celery worker for processing background tasks.
"""
import sys
from celery_app import celery_app

if __name__ == "__main__":
    # Start worker
    celery_app.worker_main([
        "worker",
        "--loglevel=info",
        "--concurrency=4",
        "--queues=scraping,generation,campaigns,monitoring",
        "--max-tasks-per-child=100",
    ])
