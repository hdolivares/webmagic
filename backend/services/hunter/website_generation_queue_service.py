"""
Website Generation Queue Service.

Manages queueing businesses for website generation and tracks generation status.
Integrates with Celery background tasks for async website generation.
"""
import logging
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func

from core.outreach_enums import OutreachChannel
from models.business import Business
from tasks.generation_sync import generate_site_for_business  # Use SYNC version for Celery

logger = logging.getLogger(__name__)


class WebsiteGenerationQueueService:
    """
    Manages the website generation queue.
    
    Responsibilities:
    - Queue businesses for generation with priority
    - Prevent duplicate queue entries
    - Track generation status (queued, in_progress, completed, failed)
    - Provide queue statistics and health metrics
    - Handle generation retries with exponential backoff
    
    Usage:
        service = WebsiteGenerationQueueService(db)
        result = await service.queue_for_generation(business_id, priority=8)
        if result['status'] == 'queued':
            print(f"Task ID: {result['task_id']}")
    """
    
    MAX_GENERATION_ATTEMPTS = 3
    """Maximum number of generation attempts before marking as failed"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize generation queue service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def queue_for_generation(
        self,
        business_id: UUID,
        priority: int = 5
    ) -> Dict[str, Any]:
        """
        Queue a business for website generation.
        
        Args:
            business_id: Business UUID
            priority: Task priority (1-10, where 10 = highest priority)
                      Default: 5
                      
        Returns:
            Dict with:
                - status: 'queued', 'already_queued', 'already_generated', 'error'
                - task_id: Celery task ID (if newly queued)
                - queued_at: Timestamp when queued
                - message: Human-readable message
        """
        # Validate priority
        priority = max(1, min(10, priority))
        
        # Get business
        result = await self.db.execute(
            select(Business).where(Business.id == business_id)
        )
        business = result.scalar_one_or_none()
        
        if not business:
            logger.error(f"Business not found: {business_id}")
            return {
                'status': 'error',
                'message': 'Business not found'
            }
        
        # **CRITICAL GUARD: Check if business actually needs a website**
        if business.website_validation_status == 'valid':
            logger.warning(
                f"Attempted to queue business {business_id} with VALID website: {business.website_url}. "
                "Skipping generation."
            )
            return {
                'status': 'has_valid_website',
                'website_url': business.website_url,
                'message': 'Business already has a valid website - generation not needed'
            }

        # **GUARD: Do not queue call-later businesses (no SMS, no email)**
        if OutreachChannel.is_call_later(business.outreach_channel):
            logger.info(
                f"Business {business_id} is in call_later bucket (no valid SMS, no email). "
                "Skipping generation until calling flow exists."
            )
            return {
                'status': 'call_later',
                'message': 'Business has no valid SMS or email; in call-later queue for future outreach'
            }
        
        # Check if already queued or in progress — but allow re-dispatch for
        # stuck tasks (queued > 2 h ago, task never even started) or for
        # businesses whose most-recent GeneratedSite has status 'failed'.
        if business.generation_queued_at and not business.generation_completed_at:
            # Is the task genuinely running (started < 2 h ago)?
            stuck_threshold = datetime.utcnow() - timedelta(hours=2)
            task_started = business.generation_started_at is not None
            queued_long_ago = business.generation_queued_at < stuck_threshold

            if task_started and not queued_long_ago:
                # Actively generating — don't duplicate
                logger.info(f"Business {business_id} is actively generating")
                return {
                    'status': 'already_queued',
                    'queued_at': business.generation_queued_at,
                    'message': 'Already in generation queue',
                }

            # Stuck (task never started OR queued > 2h ago): allow re-dispatch
            logger.warning(
                f"Business {business_id} appears stuck "
                f"(queued_at={business.generation_queued_at}, "
                f"started={business.generation_started_at}). Re-dispatching."
            )
            # Reset so the task picks it up cleanly
            business.generation_queued_at = None
            business.generation_started_at = None
            business.website_status = 'none'
            await self.db.flush()
        
        # Check if already has a successfully generated website
        if business.website_status in ['generated', 'deployed', 'sold']:
            logger.info(f"Business {business_id} already has generated website (status: {business.website_status})")
            return {
                'status': 'already_generated',
                'website_status': business.website_status,
                'message': f'Website already {business.website_status}'
            }

        # If the business is 'queued'/'generating' but its latest GeneratedSite
        # has status 'failed', the previous attempt didn't complete successfully.
        # Reset state so we can retry cleanly.
        from models.site import GeneratedSite
        from sqlalchemy import select as _select
        site_result = await self.db.execute(
            _select(GeneratedSite)
            .where(GeneratedSite.business_id == business_id)
            .order_by(GeneratedSite.created_at.desc())
            .limit(1)
        )
        latest_site = site_result.scalar_one_or_none()
        if latest_site and latest_site.status == 'failed':
            logger.info(
                f"Business {business_id} has a failed GeneratedSite — resetting for retry."
            )
            business.generation_queued_at = None
            business.generation_started_at = None
            business.generation_completed_at = None
            business.website_status = 'none'
            await self.db.flush()
        
        # Check generation attempts limit
        if business.generation_attempts >= self.MAX_GENERATION_ATTEMPTS:
            logger.warning(f"Business {business_id} has exceeded max generation attempts ({self.MAX_GENERATION_ATTEMPTS})")
            return {
                'status': 'error',
                'message': f'Max generation attempts ({self.MAX_GENERATION_ATTEMPTS}) exceeded'
            }
        
        # Update business record
        business.generation_queued_at = datetime.utcnow()
        business.generation_attempts = (business.generation_attempts or 0) + 1
        business.website_status = 'queued'
        
        try:
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update business {business_id}: {str(e)}")
            await self.db.rollback()
            return {
                'status': 'error',
                'message': f'Database error: {str(e)}'
            }
        
        # Queue Celery task
        try:
            task = generate_site_for_business.apply_async(
                args=[str(business_id)],
                priority=priority
            )
            
            logger.info(
                f"✅ Queued business {business_id} for generation "
                f"(task: {task.id}, priority: {priority}, attempt: {business.generation_attempts})"
            )
            
            return {
                'status': 'queued',
                'business_id': str(business_id),
                'business_name': business.name,
                'task_id': task.id,
                'priority': priority,
                'attempt': business.generation_attempts,
                'queued_at': business.generation_queued_at,
                'message': 'Successfully queued for generation'
            }
        
        except Exception as e:
            logger.error(f"Failed to queue Celery task for business {business_id}: {str(e)}")
            
            # Rollback business status
            business.website_status = 'none'
            business.generation_queued_at = None
            await self.db.commit()
            
            return {
                'status': 'error',
                'message': f'Failed to queue task: {str(e)}'
            }
    
    async def queue_multiple(
        self,
        business_ids: List[UUID],
        priority: int = 5
    ) -> Dict[str, Any]:
        """
        Queue multiple businesses for generation.
        
        Args:
            business_ids: List of business UUIDs
            priority: Task priority (1-10)
            
        Returns:
            Dict with:
                - total: Total businesses processed
                - queued: Number successfully queued
                - already_queued: Number already in queue
                - already_generated: Number already generated
                - errors: Number of errors
                - results: List of individual results
        """
        results = []
        counts = {
            'queued': 0,
            'already_queued': 0,
            'already_generated': 0,
            'errors': 0
        }
        
        for business_id in business_ids:
            result = await self.queue_for_generation(business_id, priority)
            results.append(result)
            
            status = result['status']
            if status in counts:
                counts[status] += 1
            else:
                counts['errors'] += 1
        
        logger.info(
            f"Queued {counts['queued']}/{len(business_ids)} businesses for generation "
            f"(already_queued: {counts['already_queued']}, "
            f"already_generated: {counts['already_generated']}, "
            f"errors: {counts['errors']})"
        )
        
        return {
            'total': len(business_ids),
            **counts,
            'results': results
        }
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status and statistics.
        
        Returns:
            Dict with:
                - queued: Count of businesses waiting in queue
                - in_progress: Count of businesses currently generating
                - completed_today: Count completed in last 24 hours
                - failed: Count of permanently failed generations
                - avg_queue_time_minutes: Average time in queue
        """
        now = datetime.utcnow()
        
        # Count queued (waiting to start)
        queued_result = await self.db.execute(
            select(func.count(Business.id)).where(
                and_(
                    Business.website_status == 'queued',
                    Business.generation_started_at.is_(None)
                )
            )
        )
        queued_count = queued_result.scalar()
        
        # Count in progress (actively generating)
        in_progress_result = await self.db.execute(
            select(func.count(Business.id)).where(
                and_(
                    Business.website_status == 'generating',
                    Business.generation_completed_at.is_(None)
                )
            )
        )
        in_progress_count = in_progress_result.scalar()
        
        # Count completed today
        from datetime import date, timedelta
        today_start = datetime.combine(date.today(), datetime.min.time())
        
        completed_today_result = await self.db.execute(
            select(func.count(Business.id)).where(
                Business.generation_completed_at >= today_start
            )
        )
        completed_today_count = completed_today_result.scalar()
        
        # Count failed (exceeded max attempts)
        failed_result = await self.db.execute(
            select(func.count(Business.id)).where(
                and_(
                    Business.generation_attempts >= self.MAX_GENERATION_ATTEMPTS,
                    Business.website_status.in_(['none', 'queued', 'generating']),
                    Business.generation_completed_at.is_(None)
                )
            )
        )
        failed_count = failed_result.scalar()
        
        # Calculate average queue time for in-progress items
        avg_queue_time_minutes = None
        if in_progress_count > 0:
            avg_result = await self.db.execute(
                select(
                    func.avg(
                        func.extract('epoch', Business.generation_started_at - Business.generation_queued_at) / 60
                    )
                ).where(
                    and_(
                        Business.website_status == 'generating',
                        Business.generation_queued_at.isnot(None),
                        Business.generation_started_at.isnot(None)
                    )
                )
            )
            avg_queue_time_minutes = avg_result.scalar()
            if avg_queue_time_minutes:
                avg_queue_time_minutes = round(float(avg_queue_time_minutes), 1)
        
        return {
            'queued': queued_count or 0,
            'in_progress': in_progress_count or 0,
            'completed_today': completed_today_count or 0,
            'failed': failed_count or 0,
            'avg_queue_time_minutes': avg_queue_time_minutes,
            'max_attempts': self.MAX_GENERATION_ATTEMPTS
        }
    
    async def mark_generation_started(self, business_id: UUID) -> bool:
        """
        Mark a business as generation started.
        
        Should be called by the generation task when it begins processing.
        
        Args:
            business_id: Business UUID
            
        Returns:
            True if successfully updated, False otherwise
        """
        try:
            await self.db.execute(
                update(Business)
                .where(Business.id == business_id)
                .values(
                    website_status='generating',
                    generation_started_at=datetime.utcnow()
                )
            )
            await self.db.commit()
            
            logger.info(f"Marked business {business_id} as generation started")
            return True
        
        except Exception as e:
            logger.error(f"Failed to mark generation started for {business_id}: {str(e)}")
            await self.db.rollback()
            return False
    
    async def mark_generation_completed(
        self,
        business_id: UUID,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Mark a business generation as completed (success or failure).
        
        Should be called by the generation task when it finishes.
        
        Args:
            business_id: Business UUID
            success: Whether generation succeeded
            error_message: Error message if failed
            
        Returns:
            True if successfully updated, False otherwise
        """
        try:
            updates = {
                'generation_completed_at': datetime.utcnow()
            }
            
            if success:
                updates['website_status'] = 'generated'
                logger.info(f"✅ Marked business {business_id} generation as completed (success)")
            else:
                # Check if we should retry
                result = await self.db.execute(
                    select(Business.generation_attempts).where(Business.id == business_id)
                )
                attempts = result.scalar()
                
                if attempts < self.MAX_GENERATION_ATTEMPTS:
                    updates['website_status'] = 'none'  # Allow retry
                    logger.warning(
                        f"⚠️ Generation failed for {business_id} "
                        f"(attempt {attempts}/{self.MAX_GENERATION_ATTEMPTS})"
                    )
                else:
                    updates['website_status'] = 'failed'
                    logger.error(
                        f"❌ Generation permanently failed for {business_id} "
                        f"(max attempts {self.MAX_GENERATION_ATTEMPTS} reached)"
                    )
            
            await self.db.execute(
                update(Business)
                .where(Business.id == business_id)
                .values(**updates)
            )
            await self.db.commit()
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to mark generation completed for {business_id}: {str(e)}")
            await self.db.rollback()
            return False
    
    async def get_businesses_needing_generation(
        self,
        limit: int = 100,
        min_qualification_score: int = 50
    ) -> List[Business]:
        """
        Get businesses that need website generation.
        
        Criteria:
        - No website URL or invalid website
        - Not already queued or generated
        - Qualification score above minimum
        - Haven't exceeded max attempts
        
        Args:
            limit: Maximum number to return
            min_qualification_score: Minimum qualification score (default: 50)
            
        Returns:
            List of Business records
        """
        result = await self.db.execute(
            select(Business)
            .where(
                and_(
                    # US only — SMS integration only works for US businesses
                    Business.country == 'US',
                    # No website or invalid
                    or_(
                        Business.website_url.is_(None),
                        Business.website_validation_status == 'invalid'
                    ),
                    # Eligible for outreach (exclude call_later)
                    or_(
                        Business.outreach_channel.is_(None),
                        Business.outreach_channel.in_([
                            OutreachChannel.SMS.value,
                            OutreachChannel.EMAIL.value,
                        ]),
                    ),
                    # Not already processed
                    Business.website_status.in_(['none', 'pending']),
                    # Not in queue
                    Business.generation_queued_at.is_(None),
                    # Qualified
                    Business.qualification_score >= min_qualification_score,
                    # Haven't exceeded attempts
                    Business.generation_attempts < self.MAX_GENERATION_ATTEMPTS
                )
            )
            .order_by(Business.qualification_score.desc())
            .limit(limit)
        )
        
        businesses = result.scalars().all()
        
        logger.info(
            f"Found {len(businesses)} US businesses needing generation "
            f"(min_score: {min_qualification_score})"
        )
        
        return list(businesses)

    async def get_triple_verified_businesses_needing_generation(
        self,
        limit: int = 100,
        min_qualification_score: int = 50
    ) -> List[Business]:
        """
        Get businesses TRIPLE-VERIFIED to have no website.
        Only these should be queued to avoid wasting credits.

        Criteria:
        - website_validation_status = 'missing' (confirmed no website)
        - website_validated_at IS NOT NULL (verification completed)
        - No website_url
        - Not already queued or generated
        - Qualification score above minimum
        """
        result = await self.db.execute(
            select(Business)
            .where(
                and_(
                    # US only — SMS integration only works for US businesses
                    Business.country == 'US',
                    Business.website_validation_status == 'missing',
                    Business.website_validated_at.isnot(None),
                    or_(
                        Business.website_url.is_(None),
                        Business.website_url == ""
                    ),
                    # Eligible for outreach (exclude call_later)
                    or_(
                        Business.outreach_channel.is_(None),
                        Business.outreach_channel.in_([
                            OutreachChannel.SMS.value,
                            OutreachChannel.EMAIL.value,
                        ]),
                    ),
                    Business.website_status.in_(['none', 'pending']),
                    Business.generation_queued_at.is_(None),
                    Business.qualification_score >= min_qualification_score,
                    Business.generation_attempts < self.MAX_GENERATION_ATTEMPTS
                )
            )
            .order_by(Business.qualification_score.desc())
            .limit(limit)
        )
        businesses = result.scalars().all()
        logger.info(
            f"Found {len(businesses)} TRIPLE-VERIFIED US businesses needing generation"
        )
        return list(businesses)
    
    async def auto_queue_eligible_businesses(
        self,
        max_to_queue: int = 50,
        priority: int = 5,
        min_qualification_score: int = 60
    ) -> Dict[str, Any]:
        """
        Automatically queue eligible businesses for generation.
        
        This can be called periodically (e.g., via cron) to keep the
        generation queue filled with high-quality businesses.
        
        Args:
            max_to_queue: Maximum number to queue
            priority: Task priority
            min_qualification_score: Minimum qualification score
            
        Returns:
            Dict with queuing results
        """
        businesses = await self.get_businesses_needing_generation(
            limit=max_to_queue,
            min_qualification_score=min_qualification_score
        )
        
        if not businesses:
            logger.info("No eligible businesses found for auto-queueing")
            return {
                'status': 'success',
                'queued': 0,
                'message': 'No eligible businesses found'
            }
        
        business_ids = [b.id for b in businesses]
        result = await self.queue_multiple(business_ids, priority=priority)
        
        logger.info(
            f"Auto-queued {result['queued']} businesses for generation "
            f"(priority: {priority}, min_score: {min_qualification_score})"
        )
        
        return {
            'status': 'success',
            **result
        }

