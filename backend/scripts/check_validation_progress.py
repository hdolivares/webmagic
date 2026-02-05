"""
Check progress of website validation tasks.

Shows real-time stats on validation status across all businesses.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db_session_sync
from models.business import Business
from sqlalchemy import func, and_


def get_validation_stats():
    """Get comprehensive validation statistics."""
    with get_db_session_sync() as db:
        # Total businesses
        total = db.query(func.count(Business.id)).scalar()
        
        # Businesses with websites
        with_websites = db.query(func.count(Business.id)).filter(
            Business.website_url.isnot(None)
        ).scalar()
        
        # Status breakdown
        status_counts = {}
        statuses = ['pending', 'valid', 'invalid', 'no_website', 'error', None]
        
        for status in statuses:
            if status is None:
                # Count NULL status (legacy data)
                count = db.query(func.count(Business.id)).filter(
                    and_(
                        Business.website_url.isnot(None),
                        Business.website_validation_status.is_(None)
                    )
                ).scalar()
                status_counts['unknown'] = count
            else:
                count = db.query(func.count(Business.id)).filter(
                    Business.website_validation_status == status
                ).scalar()
                status_counts[status] = count
        
        # Quality score stats (for valid websites)
        quality_scores = db.query(
            Business.website_validation_result
        ).filter(
            and_(
                Business.website_validation_status == 'valid',
                Business.website_validation_result.isnot(None)
            )
        ).all()
        
        scores = [
            result[0].get('quality_score', 0) 
            for result in quality_scores 
            if result[0]
        ]
        
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Recently validated
        recently_validated = db.query(func.count(Business.id)).filter(
            and_(
                Business.website_validated_at.isnot(None),
                Business.website_validated_at >= func.now() - func.cast('1 hour', func.Interval)
            )
        ).scalar()
        
        return {
            'total': total,
            'with_websites': with_websites,
            'status_counts': status_counts,
            'avg_quality_score': avg_score,
            'recently_validated': recently_validated,
            'total_scores': len(scores)
        }


def display_progress_bar(current, total, label="Progress", width=50):
    """Display a progress bar."""
    if total == 0:
        percentage = 0
    else:
        percentage = (current / total) * 100
    
    filled = int(width * current / total) if total > 0 else 0
    bar = '█' * filled + '░' * (width - filled)
    
    print(f"{label}: [{bar}] {percentage:.1f}% ({current}/{total})")


def main():
    print("\n" + "="*70)
    print("📊 WEBSITE VALIDATION PROGRESS")
    print("="*70 + "\n")
    
    stats = get_validation_stats()
    
    # Overall stats
    print("📈 Overall Statistics:")
    print(f"  • Total businesses: {stats['total']}")
    print(f"  • With websites: {stats['with_websites']}")
    print(f"  • Recently validated (last hour): {stats['recently_validated']}")
    
    # Status breakdown
    print(f"\n🔍 Validation Status:")
    
    status_labels = {
        'valid': '✅ Valid',
        'invalid': '❌ Invalid',
        'pending': '⏳ Pending',
        'no_website': '🚫 No Website',
        'error': '⚠️  Error',
        'unknown': '❓ Unknown (not validated)'
    }
    
    # Calculate progress
    validated_count = sum([
        stats['status_counts'].get('valid', 0),
        stats['status_counts'].get('invalid', 0),
        stats['status_counts'].get('error', 0)
    ])
    
    pending_count = sum([
        stats['status_counts'].get('pending', 0),
        stats['status_counts'].get('unknown', 0)
    ])
    
    for status, label in status_labels.items():
        count = stats['status_counts'].get(status, 0)
        if count > 0:
            percentage = (count / stats['with_websites']) * 100 if stats['with_websites'] > 0 else 0
            print(f"  {label:25} {count:6} ({percentage:5.1f}%)")
    
    # Progress bars
    print(f"\n📊 Validation Progress:")
    
    if stats['with_websites'] > 0:
        display_progress_bar(
            validated_count,
            stats['with_websites'],
            label="Validated  ",
            width=40
        )
        
        display_progress_bar(
            pending_count,
            stats['with_websites'],
            label="Pending    ",
            width=40
        )
        
        # Quality metrics
        if stats['total_scores'] > 0:
            print(f"\n⭐ Quality Metrics (Valid Websites):")
            print(f"  • Average quality score: {stats['avg_quality_score']:.1f}/100")
            print(f"  • Websites with scores: {stats['total_scores']}")
            
            # Score distribution
            print(f"\n  Score distribution:")
            score_ranges = [
                (0, 30, "Low (0-30)"),
                (30, 60, "Medium (30-60)"),
                (60, 100, "High (60-100)")
            ]
            
            # This would require more detailed query, simplified for now
            print(f"    (Detailed distribution available via API)")
    
    # Next steps
    print(f"\n📝 Next Steps:")
    if pending_count > 0:
        print(f"  • {pending_count} websites pending validation")
        print(f"  • Run: python scripts/revalidate_all_websites.py --status pending")
    
    if stats['status_counts'].get('invalid', 0) > 0:
        print(f"  • {stats['status_counts'].get('invalid', 0)} websites marked invalid")
        print(f"  • Review and re-validate: python scripts/revalidate_all_websites.py --status invalid")
    
    if validated_count == stats['with_websites']:
        print(f"  ✅ All websites have been validated!")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()

