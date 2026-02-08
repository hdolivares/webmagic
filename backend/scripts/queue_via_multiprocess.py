"""
Queue validation using multiprocessing to avoid hangs.
"""
import os
import sys
from multiprocessing import Process, Queue
import time

os.chdir('/var/www/webmagic/backend')
sys.path.insert(0, '/var/www/webmagic/backend')

def queue_tasks_worker(business_ids, result_queue):
    """Worker process that queues tasks."""
    try:
        from tasks.validation_tasks import batch_validate_websites
        
        batch_size = 10
        tasks_queued = 0
        
        for i in range(0, len(business_ids), batch_size):
            batch = business_ids[i:i + batch_size]
            batch_validate_websites.delay(batch)
            tasks_queued += 1
            
            if tasks_queued % 10 == 0:
                result_queue.put(f"Queued {tasks_queued} batches")
        
        result_queue.put(f"SUCCESS:{tasks_queued}")
    except Exception as e:
        result_queue.put(f"ERROR:{str(e)}")

if __name__ == '__main__':
    # Get business IDs
    import psycopg2
    from urllib.parse import urlparse
    from dotenv import load_dotenv
    
    load_dotenv()
    DATABASE_URL = os.getenv('DATABASE_URL')
    parsed = urlparse(DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://'))
    
    print("Fetching businesses...")
    conn = psycopg2.connect(
        host=parsed.hostname, port=parsed.port,
        user=parsed.username, password=parsed.password,
        dbname=parsed.path.lstrip('/')
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT id FROM businesses 
        WHERE website_validation_status = 'pending'
          AND website_url IS NOT NULL AND website_url != ''
        LIMIT 500
    """)
    business_ids = [str(row[0]) for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    print(f"Found {len(business_ids)} businesses")
    
    if not business_ids:
        print("No businesses to queue!")
        sys.exit(0)
    
    # Queue in separate process with timeout
    result_queue = Queue()
    worker = Process(target=queue_tasks_worker, args=(business_ids, result_queue))
    
    print("Starting worker process...")
    worker.start()
    
    # Monitor with timeout
    start_time = time.time()
    timeout = 30
    
    while worker.is_alive():
        if time.time() - start_time > timeout:
            print(f"Worker timeout after {timeout}s, terminating...")
            worker.terminate()
            worker.join(timeout=5)
            break
        
        # Check for messages
        try:
            msg = result_queue.get(timeout=1)
            print(f"  {msg}")
            if msg.startswith("SUCCESS:"):
                count = msg.split(":")[1]
                print(f"\n✓ Successfully queued {count} batches!")
                break
            elif msg.startswith("ERROR:"):
                error = msg.split(":", 1)[1]
                print(f"\n✗ Error: {error}")
                break
        except:
            pass
    
    worker.join(timeout=2)
    print("\nMonitor Celery logs:")
    print("  tail -f /var/log/webmagic/celery.log")
