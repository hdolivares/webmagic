import sys
sys.path.insert(0, '/var/www/webmagic/backend')
from core.database import get_db_session_sync
from sqlalchemy import text

# Update to claude-3-5-sonnet-20240620 (most common valid model)
with get_db_session_sync() as db:
    db.execute(text("UPDATE system_settings SET value = 'claude-3-5-sonnet-20240620' WHERE key = 'llm_model'"))
    db.commit()
    result = db.execute(text("SELECT value FROM system_settings WHERE key = 'llm_model'"))
    new_value = result.fetchone()[0]
    print(f"Model updated to: {new_value}")
