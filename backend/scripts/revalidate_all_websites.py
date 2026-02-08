"""
Re-validate all existing business websites using Playwright.

This script queues Playwright validation for existing businesses in the database.
Useful for:
- Re-checking websites that were marked invalid with old simple validation
- Getting quality scores for existing businesses
- Updating validation data with comprehensive Playwright analysis

Usage:
    # Validate all businesses with websites
    python scripts/revalidate_all_websites.py --all
    
    # Validate only businesses marked as "invalid" (re-check them)
    python scripts/revalidate_all_websites.py --status invalid
    
    # Validate businesses with no validation data
    python scripts/revalidate_all_websites.py --status pending
    
    # Dry run (see what would be validated without actually queuing)
    python scripts/revalidate_all_websites.py --all --dry-run
    
    # Limit to first 100 businesses
    python scripts/revalidate_all_websites.py --all --limit 100
"""
import sys
import os
import argparse
from typing import Optional

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db_session_sync
from models.business import Business
from tasks.validation_tasks import batch_validate_websites
from datetime import datetime


def get_businesses_to_validate(
    status: Optional[str] = None,
    limit: Optional[int] = None
):
    """
    Get businesses that need validation.
    
    Args:
        status: Filter by validation status (pending, invalid, valid, no_website, error)
        limit: Maximum number of businesses to return
        
    Returns:
        List of business IDs and names
    """
    with get_db_session_sync() as db:
        # Base query: businesses with websites
        query = db.query(Business).filter(
            Business.website_url.isnot(None)
        )
        
        # Filter by status if specified
        if status:
            query = query.filter(Business.website_validation_status == status)
        
        # Order by: never validated first, then oldest validation
        query = query.order_by(
            Business.website_validated_at.asc().nullsfirst()
        )
        
        # Apply limit if specified
        if limit:
            query = query.limit(limit)
        
        businesses = query.all()
        
        return [
            {
                "id": str(b.id),
                "name": b.name,
                "website_url": b.website_url,
                "current_status": b.website_validation_status or "unknown",
                "last_validated": b.website_validated_at.isoformat() if b.website_validated_at else "never"
            }
            for b in businesses
        ]


def queue_validations(business_ids: list[str], batch_size: int = 10):
    """
    Queue validation tasks for businesses.
    
    Args:
        business_ids: List of business UUIDs
        batch_size: Number of businesses per Celery task
        
    Returns:
        List of queued task IDs
    """
    tasks = []
    
    # Queue in batches
    for i in range(0, len(business_ids), batch_size):
        batch = business_ids[i:i + batch_size]
        task = batch_validate_websites.delay(batch)
        tasks.append({
            "batch_number": i // batch_size + 1,
            "businesses_count": len(batch),
            "task_id": task.id
        })
    
    return tasks


def main():
    parser = argparse.ArgumentParser(
        description="Re-validate business websites using Playwright",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate all businesses
  python scripts/revalidate_all_websites.py --all
  
  # Re-validate only businesses marked as invalid
  python scripts/revalidate_all_websites.py --status invalid
  
  # Validate businesses that have never been validated
  python scripts/revalidate_all_websites.py --status pending
  
  # Dry run to see what would be validated
  python scripts/revalidate_all_websites.py --all --dry-run --limit 10
  
  # Validate first 50 businesses with custom batch size
  python scripts/revalidate_all_websites.py --all --limit 50 --batch-size 20
        """
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate all businesses with websites (ignoring current status)"
    )
    
    parser.add_argument(
        "--status",
        type=str,
        choices=["pending", "invalid", "valid", "no_website", "error"],
        help="Only validate businesses with this status"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of businesses to validate"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of businesses per validation task (default: 10)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be validated without actually queuing tasks"
    )
    
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt (for automated/CI runs)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.all and not args.status:
        parser.error("Must specify either --all or --status")
    
    if args.all and args.status:
        parser.error("Cannot specify both --all and --status")
    
    print("\n" + "="*70)
    print("🔄 RE-VALIDATE BUSINESS WEBSITES WITH PLAYWRIGHT")
    print("="*70 + "\n")
    
    # Get businesses to validate
    print("📊 Querying database...")
    
    status_filter = None if args.all else args.status
    businesses = get_businesses_to_validate(
        status=status_filter,
        limit=args.limit
    )
    
    if not businesses:
        print("\n❌ No businesses found matching criteria")
        print("\nCriteria:")
        print(f"  - Status filter: {status_filter or 'all'}")
        print(f"  - Limit: {args.limit or 'none'}")
        return
    
    print(f"\n✅ Found {len(businesses)} businesses to validate\n")
    
    # Show summary
    print("📋 Summary:")
    print(f"  - Total businesses: {len(businesses)}")
    print(f"  - Status filter: {status_filter or 'all'}")
    print(f"  - Batch size: {args.batch_size}")
    print(f"  - Estimated batches: {(len(businesses) + args.batch_size - 1) // args.batch_size}")
    
    # Show status breakdown
    status_counts = {}
    for b in businesses:
        status = b["current_status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"\n  Status breakdown:")
    for status, count in sorted(status_counts.items()):
        print(f"    - {status}: {count}")
    
    # Show sample businesses
    print(f"\n  Sample businesses (first 5):")
    for b in businesses[:5]:
        print(f"    • {b['name']}")
        print(f"      URL: {b['website_url']}")
        print(f"      Current status: {b['current_status']}")
        print(f"      Last validated: {b['last_validated']}")
        print()
    
    if len(businesses) > 5:
        print(f"    ... and {len(businesses) - 5} more\n")
    
    # Dry run check
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No tasks will be queued")
        print("\nWhat would happen:")
        print(f"  1. Queue {len(businesses)} businesses for validation")
        print(f"  2. Split into {(len(businesses) + args.batch_size - 1) // args.batch_size} batches of {args.batch_size}")
        print(f"  3. Each business will be validated with Playwright")
        print(f"  4. Results will update database with:")
        print(f"     - website_validation_status (valid/invalid)")
        print(f"     - website_validation_result (quality score, contact info, etc.)")
        print(f"     - website_validated_at (timestamp)")
        print("\n✅ Dry run complete - no changes made")
        return
    
    # Confirm
    if not args.yes:
        print("\n⚠️  READY TO QUEUE VALIDATION TASKS")
        print("\nThis will:")
        print(f"  • Queue {len(businesses)} businesses for Playwright validation")
        print(f"  • Update their validation status and results in the database")
        print(f"  • Each validation takes ~5-10 seconds")
        print(f"  • Total estimated time: ~{(len(businesses) * 7) // 60} minutes")
        
        confirm = input("\n❓ Proceed? (yes/no): ").strip().lower()
        
        if confirm != "yes":
            print("\n❌ Cancelled - no tasks queued")
            return
    
    # Queue validations
    print(f"\n🚀 Queuing validation tasks...")
    
    business_ids = [b["id"] for b in businesses]
    tasks = queue_validations(business_ids, batch_size=args.batch_size)
    
    print(f"\n✅ Successfully queued {len(tasks)} validation batches!")
    print(f"\n📊 Task Details:")
    for task in tasks[:10]:  # Show first 10 batches
        print(f"  Batch {task['batch_number']}: {task['businesses_count']} businesses (task: {task['task_id']})")
    
    if len(tasks) > 10:
        print(f"  ... and {len(tasks) - 10} more batches")
    
    print(f"\n📈 Monitoring:")
    print(f"  • Check Celery logs: tail -f /var/log/webmagic/celery.log")
    print(f"  • Check validation stats: curl https://web.lavish.solutions/api/v1/validation/stats")
    print(f"  • View results in database: SELECT website_validation_status, COUNT(*) FROM businesses GROUP BY website_validation_status;")
    
    print(f"\n⏱️  Estimated completion: ~{(len(businesses) * 7) // 60} minutes")
    print(f"\n✨ Validation tasks queued successfully!")


if __name__ == "__main__":
    main()

