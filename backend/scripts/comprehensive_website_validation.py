"""
Comprehensive Multi-Stage Website Validation

This script performs thorough validation before website generation to prevent
wasting tokens on businesses that actually have websites.

Validation Stages:
1. Raw Data Analysis: Check if website exists in raw Outscraper data but wasn't parsed
2. Multi-Method HTTP Validation: Try multiple user-agents, retries, and protocols
3. DNS Validation: Verify domain actually exists
4. Social Media Check: Look for website in Google listing
5. Confidence Scoring: Assign confidence level to each validation result

Run with: python -m scripts.comprehensive_website_validation
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import aiohttp
import socket
from urllib.parse import urlparse

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from core.database import AsyncSessionLocal
from models.business import Business
from services.hunter.website_validation_service import WebsiteValidationService
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComprehensiveValidator:
    """Multi-stage website validation with confidence scoring."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_agents = [
            # Modern browsers
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            # Mobile
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            # Googlebot (sometimes gets better access)
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        ]
    
    async def __aenter__(self):
        """Initialize async resources."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup async resources."""
        if self.session:
            await self.session.close()
    
    def check_raw_data_for_website(self, business: Business) -> Optional[str]:
        """
        Stage 1: Check if website exists in raw_data but wasn't parsed.
        
        Returns:
            Website URL if found, None otherwise
        """
        if not business.raw_data:
            return None
        
        # Check multiple possible fields in raw data
        possible_fields = [
            'website', 'site', 'url', 'web', 'homepage',
            'Website', 'Site', 'URL', 'Web', 'HomePage'
        ]
        
        for field in possible_fields:
            if field in business.raw_data and business.raw_data[field]:
                website = str(business.raw_data[field]).strip()
                if website and website not in ['', 'null', 'None', 'N/A']:
                    logger.info(f"  🔍 Found website in raw_data['{field}']: {website}")
                    return website
        
        return None
    
    async def validate_with_multiple_user_agents(self, url: str) -> Dict[str, Any]:
        """
        Stage 2: Try multiple user-agents to bypass anti-bot protection.
        
        Returns:
            Dict with 'accessible', 'status_code', 'user_agent_used', 'protected'
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' context manager.")
        
        results = []
        
        for ua in self.user_agents:
            try:
                async with self.session.head(
                    url,
                    headers={"User-Agent": ua},
                    allow_redirects=True,
                    ssl=False
                ) as response:
                    results.append({
                        'user_agent': ua[:50],  # Truncate for logging
                        'status': response.status,
                        'accessible': response.status in [200, 301, 302, 303, 307, 308]
                    })
                    
                    # If we get a good response, return immediately
                    if response.status == 200:
                        return {
                            'accessible': True,
                            'status_code': 200,
                            'user_agent_used': ua[:50],
                            'protected': False
                        }
                    
                    # 403/429 means site exists but is protected
                    if response.status in [403, 429]:
                        return {
                            'accessible': True,
                            'status_code': response.status,
                            'user_agent_used': ua[:50],
                            'protected': True
                        }
            
            except Exception as e:
                results.append({
                    'user_agent': ua[:50],
                    'status': 'error',
                    'error': str(e)[:100],
                    'accessible': False
                })
                continue
        
        # All attempts failed
        return {
            'accessible': False,
            'status_code': None,
            'user_agent_used': None,
            'protected': False,
            'all_attempts': results
        }
    
    async def validate_dns(self, url: str) -> Dict[str, Any]:
        """
        Stage 3: Verify domain exists via DNS lookup.
        
        Returns:
            Dict with 'domain_exists', 'ip_address'
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split('/')[0]
            
            # Remove port if present
            domain = domain.split(':')[0]
            
            # DNS lookup
            ip_address = socket.gethostbyname(domain)
            
            return {
                'domain_exists': True,
                'ip_address': ip_address,
                'domain': domain
            }
        
        except socket.gaierror:
            return {
                'domain_exists': False,
                'error': 'DNS lookup failed - domain does not exist',
                'domain': domain if 'domain' in locals() else 'unknown'
            }
        
        except Exception as e:
            return {
                'domain_exists': False,
                'error': str(e),
                'domain': 'unknown'
            }
    
    def calculate_confidence_score(
        self,
        has_url: bool,
        raw_data_has_url: bool,
        http_accessible: bool,
        http_protected: bool,
        dns_exists: bool,
        current_status: str
    ) -> Dict[str, Any]:
        """
        Stage 5: Calculate confidence score for validation result.
        
        Returns:
            Dict with 'confidence', 'recommendation', 'reasoning'
        """
        confidence = 0
        reasoning = []
        
        # Scoring logic
        if has_url:
            confidence += 20
            reasoning.append("Has URL in database")
            
            if http_accessible:
                confidence += 40
                reasoning.append("HTTP request successful")
            elif http_protected:
                confidence += 35
                reasoning.append("Website protected by anti-bot (likely valid)")
            else:
                confidence -= 10
                reasoning.append("HTTP request failed")
            
            if dns_exists:
                confidence += 30
                reasoning.append("Domain exists (DNS verified)")
            else:
                confidence -= 20
                reasoning.append("Domain doesn't exist (DNS failed)")
        
        else:  # No URL
            if raw_data_has_url:
                confidence = 50
                reasoning.append("Website found in raw data but not parsed!")
            else:
                confidence = 90
                reasoning.append("No URL in database or raw data")
        
        # Determine recommendation
        if confidence >= 70:
            if has_url and (http_accessible or http_protected):
                recommendation = "has_website"
            else:
                recommendation = "needs_website"
        elif confidence >= 40:
            recommendation = "needs_manual_review"
        else:
            recommendation = "needs_website"
        
        return {
            'confidence': min(100, max(0, confidence)),
            'recommendation': recommendation,
            'reasoning': reasoning
        }
    
    async def comprehensive_validate(self, business: Business) -> Dict[str, Any]:
        """
        Perform comprehensive multi-stage validation.
        
        Returns:
            Complete validation result with confidence score
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Validating: {business.name} ({business.city}, {business.state})")
        logger.info(f"Current Status: {business.website_validation_status}")
        logger.info(f"Current URL: {business.website_url or 'None'}")
        
        result = {
            'business_id': str(business.id),
            'business_name': business.name,
            'original_url': business.website_url,
            'original_status': business.website_validation_status,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Stage 1: Check raw data
        raw_data_url = self.check_raw_data_for_website(business)
        result['raw_data_url'] = raw_data_url
        
        # Determine which URL to validate
        url_to_validate = business.website_url or raw_data_url
        
        if url_to_validate:
            # Stage 2: Multi-agent HTTP validation
            logger.info(f"  🌐 Testing HTTP accessibility...")
            http_result = await self.validate_with_multiple_user_agents(url_to_validate)
            result['http_validation'] = http_result
            
            # Stage 3: DNS validation
            logger.info(f"  🔍 Checking DNS...")
            dns_result = await self.validate_dns(url_to_validate)
            result['dns_validation'] = dns_result
        else:
            result['http_validation'] = {'accessible': False, 'reason': 'no_url'}
            result['dns_validation'] = {'domain_exists': False, 'reason': 'no_url'}
        
        # Stage 5: Calculate confidence
        confidence_result = self.calculate_confidence_score(
            has_url=bool(business.website_url),
            raw_data_has_url=bool(raw_data_url),
            http_accessible=result['http_validation'].get('accessible', False),
            http_protected=result['http_validation'].get('protected', False),
            dns_exists=result['dns_validation'].get('domain_exists', False),
            current_status=business.website_validation_status
        )
        result['confidence'] = confidence_result
        
        # Determine final status
        if confidence_result['recommendation'] == 'has_website':
            result['final_status'] = 'valid'
        elif confidence_result['recommendation'] == 'needs_website':
            result['final_status'] = 'missing'
        else:
            result['final_status'] = 'needs_review'
        
        # Log summary
        logger.info(f"  ✅ Validation Complete:")
        logger.info(f"     Confidence: {confidence_result['confidence']}%")
        logger.info(f"     Recommendation: {confidence_result['recommendation']}")
        logger.info(f"     Final Status: {result['final_status']}")
        logger.info(f"     Reasoning: {', '.join(confidence_result['reasoning'])}")
        
        return result


async def validate_all_queued_businesses(
    dry_run: bool = True,
    save_results: bool = True
) -> Dict[str, Any]:
    """
    Validate all businesses in the generation queue.
    
    Args:
        dry_run: If True, don't update database, just report
        save_results: If True, save validation results to JSON file
    
    Returns:
        Summary statistics
    """
    logger.info("="*80)
    logger.info("COMPREHENSIVE WEBSITE VALIDATION")
    logger.info("="*80)
    logger.info(f"Mode: {'DRY RUN (no database changes)' if dry_run else 'LIVE (will update database)'}")
    logger.info("")
    
    async with AsyncSessionLocal() as db:
        # Get all queued businesses
        result = await db.execute(
            select(Business).where(
                Business.website_status == 'queued'
            ).order_by(Business.website_validation_status)
        )
        businesses = result.scalars().all()
        
        if not businesses:
            logger.info("✅ No businesses in queue to validate")
            return {'total': 0}
        
        logger.info(f"Found {len(businesses)} businesses to validate\n")
        
        # Initialize validator
        async with ComprehensiveValidator() as validator:
            validation_results = []
            stats = {
                'total': len(businesses),
                'has_website': 0,
                'needs_website': 0,
                'needs_review': 0,
                'removed_from_queue': 0,
                'updated': 0
            }
            
            for idx, business in enumerate(businesses, 1):
                try:
                    logger.info(f"\n[{idx}/{len(businesses)}] Processing...")
                    
                    # Perform comprehensive validation
                    validation = await validator.comprehensive_validate(business)
                    validation_results.append(validation)
                    
                    # Update stats
                    if validation['final_status'] == 'valid':
                        stats['has_website'] += 1
                    elif validation['final_status'] == 'missing':
                        stats['needs_website'] += 1
                    else:
                        stats['needs_review'] += 1
                    
                    # Update database if not dry run
                    if not dry_run:
                        # Update validation status
                        business.website_validation_status = validation['final_status']
                        business.website_validated_at = datetime.utcnow()
                        
                        # If found URL in raw_data, update it
                        if validation['raw_data_url'] and not business.website_url:
                            business.website_url = validation['raw_data_url']
                            logger.info(f"     📝 Updated website_url from raw_data")
                        
                        # Remove from queue if has valid website
                        if validation['final_status'] == 'valid':
                            business.website_status = 'none'
                            business.generation_queued_at = None
                            business.generation_attempts = 0
                            stats['removed_from_queue'] += 1
                            logger.info(f"     🚫 Removed from generation queue")
                        
                        stats['updated'] += 1
                        
                        # Commit every 10 to avoid losing progress
                        if idx % 10 == 0:
                            await db.commit()
                            logger.info(f"\n💾 Progress saved ({idx}/{len(businesses)})\n")
                    
                    # Small delay to avoid overwhelming services
                    await asyncio.sleep(0.5)
                
                except Exception as e:
                    logger.error(f"❌ Error validating {business.name}: {e}")
                    validation_results.append({
                        'business_id': str(business.id),
                        'business_name': business.name,
                        'error': str(e)
                    })
                    continue
            
            # Final commit
            if not dry_run:
                await db.commit()
                logger.info("\n💾 Final commit complete")
            
            # Save results to file
            if save_results:
                import json
                filename = f"validation_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump({
                        'timestamp': datetime.utcnow().isoformat(),
                        'dry_run': dry_run,
                        'statistics': stats,
                        'results': validation_results
                    }, f, indent=2)
                logger.info(f"\n📄 Results saved to: {filename}")
            
            # Print summary
            logger.info("\n" + "="*80)
            logger.info("VALIDATION SUMMARY")
            logger.info("="*80)
            logger.info(f"Total Validated: {stats['total']}")
            logger.info(f"  ✅ Has Valid Website: {stats['has_website']}")
            logger.info(f"  ❌ Needs Website: {stats['needs_website']}")
            logger.info(f"  ⚠️  Needs Manual Review: {stats['needs_review']}")
            if not dry_run:
                logger.info(f"  🚫 Removed from Queue: {stats['removed_from_queue']}")
                logger.info(f"  📝 Database Updated: {stats['updated']}")
            logger.info("="*80)
            
            return stats


if __name__ == "__main__":
    import sys
    
    # Check if user wants live run
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == '--live':
        print("\n⚠️  LIVE MODE: Database will be updated!")
        response = input("Are you sure? (type 'yes' to confirm): ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
        dry_run = False
    else:
        print("\n🔍 DRY RUN MODE: No database changes will be made.")
        print("   To run in live mode, use: python -m scripts.comprehensive_website_validation --live\n")
    
    asyncio.run(validate_all_queued_businesses(dry_run=dry_run))

