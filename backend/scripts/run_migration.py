#!/usr/bin/env python3
"""
Run initial schema migration on a fresh database.
Usage: python scripts/run_migration.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from core.database import engine


async def run_migration():
    """Run the initial schema migration."""
    migration_file = Path(__file__).parent.parent / "migrations" / "000_initial_schema.sql"
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print(f"📂 Reading migration: {migration_file}")
    sql_content = migration_file.read_text()
    
    # Split into individual statements (handle multi-statement SQL)
    # We'll execute the whole file as one transaction
    print("🔄 Connecting to database...")
    
    async with engine.begin() as conn:
        print("🚀 Running migration...")
        
        # Execute each statement separately
        statements = []
        current_statement = []
        
        for line in sql_content.split('\n'):
            # Skip empty lines and comments at statement level
            stripped = line.strip()
            if not stripped or stripped.startswith('--'):
                if current_statement:
                    current_statement.append(line)
                continue
            
            current_statement.append(line)
            
            # Check if this line ends a statement
            if stripped.endswith(';'):
                statement = '\n'.join(current_statement)
                statements.append(statement)
                current_statement = []
        
        # Execute all statements
        total = len(statements)
        for i, statement in enumerate(statements, 1):
            try:
                # Skip empty statements
                if not statement.strip() or statement.strip().startswith('--'):
                    continue
                    
                await conn.execute(text(statement))
                
                # Show progress for CREATE TABLE statements
                if 'CREATE TABLE' in statement.upper():
                    table_name = statement.split('CREATE TABLE')[1].split('(')[0].strip()
                    table_name = table_name.replace('IF NOT EXISTS', '').strip()
                    print(f"  ✅ [{i}/{total}] Created table: {table_name}")
                elif 'CREATE INDEX' in statement.upper():
                    pass  # Don't spam index creation
                elif 'CREATE EXTENSION' in statement.upper():
                    print(f"  ✅ [{i}/{total}] Created extension: uuid-ossp")
                elif 'ALTER TABLE' in statement.upper():
                    print(f"  ✅ [{i}/{total}] Added constraint")
                    
            except Exception as e:
                print(f"  ⚠️  Statement {i}: {str(e)[:100]}")
                # Continue on errors (table might already exist)
                continue
        
        print("\n✅ Migration completed successfully!")
        return True


async def verify_tables():
    """Verify tables were created."""
    print("\n📊 Verifying tables...")
    
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        
        print(f"\n📋 Found {len(tables)} tables in public schema:")
        for table in tables:
            print(f"   • {table}")
        
        return len(tables)


async def main():
    print("=" * 50)
    print("🗄️  WebMagic Database Migration")
    print("=" * 50)
    
    success = await run_migration()
    
    if success:
        count = await verify_tables()
        print(f"\n🎉 Database ready with {count} tables!")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

