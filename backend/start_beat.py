"""
Start Celery Beat scheduler for periodic tasks.
"""
from celery_app import celery_app

if __name__ == "__main__":
    # Start beat scheduler
    celery_app.Beat().run()
