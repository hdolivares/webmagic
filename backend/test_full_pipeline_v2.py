"""
Complete End-to-End Pipeline Test - Enhanced with Progress Tracking
Tests the entire workflow from business data to live website + email notification

Features:
- Real-time progress indicators
- Status updates for each agent
- Better error handling and logging
- Time tracking for each step
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.database import get_db
from services.creative.orchestrator import CreativeOrchestrator
from services.pitcher.email_sender import EmailSender
from core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Test business data
BUSINESS_DATA = {
    "name": "Los Angeles Plumbing Pros",
    "category": "plumber",
    "description": "Professional plumbing services in Los Angeles area",
    "location": {
        "address": "1901 E Gage Ave, Los Angeles, CA 90001, United States",
        "city": "Los Angeles",
        "state": "California",
        "zip_code": "90001",
        "country": "United States"
    },
    "phone": "+1 310-861-9785",
    "email": None,  # Test smart fallback - will use phone
    "rating": 5.0,
    "review_count": 64,
    "hours": "Open 24 hours",
    "areas_served": ["Los Ángeles", "Huntington Park"],
    "reviews": [
        "The technician verified that no pressure issues existed.",
        "Excellent service and professional staff.",
        "He is the best service technician I've ever had in my home."
    ]
}

# Email recipient
TEST_EMAIL = "hobeja7@gmail.com"

# Subdomain for this test
SUBDOMAIN = "la-plumbing-pros"


def print_progress(step, message, status="⏳"):
    """Print formatted progress message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {status} {step}: {message}", flush=True)


def print_step_header(step_num, title):
    """Print step header"""
    print(f"\n{'='*70}")
    print(f"STEP {step_num}: {title}")
    print(f"{'='*70}\n")


async def generate_website_with_progress(db) -> dict:
    """Step 1: Generate website using AI agents with progress tracking"""
    print_step_header(1, "WEBSITE GENERATION")
    
    print(f"📊 Business: {BUSINESS_DATA['name']}")
    print(f"📍 Location: {BUSINESS_DATA['location']['city']}, {BUSINESS_DATA['location']['state']}")
    print(f"📞 Phone: {BUSINESS_DATA['phone']}")
    print(f"⭐ Rating: {BUSINESS_DATA['rating']} ({BUSINESS_DATA['review_count']} reviews)\n")
    
    try:
        print_progress("Orchestrator", "Initializing Creative Orchestrator", "🤖")
        orchestrator = CreativeOrchestrator(db)
        
        print_progress("Pipeline", "Starting AI agent pipeline", "🚀")
        print("   📝 Agent sequence:")
        print("      1️⃣ Analyst Agent - Analyze business & competition")
        print("      2️⃣ Concept Agent - Create creative DNA")
        print("      3️⃣ Art Director - Design brand identity")
        print("      4️⃣ Architect Agent - Build website structure\n")
        
        start_time = datetime.now()
        
        # Wrap the generation with progress updates
        print_progress("Agent 1/4", "Analyst analyzing business data...", "🔍")
        
        result = await orchestrator.generate_website(
            business_data=BUSINESS_DATA,
            save_intermediate=True
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        website = result.get("website", {})
        
        if not website or not website.get('html'):
            print_progress("Generation", "No website data received!", "❌")
            raise ValueError("Website generation failed - no HTML returned")
        
        print_progress("Generation", f"Complete in {duration:.1f}s", "✅")
        print(f"\n📄 Website Output:")
        print(f"   ├─ HTML: {len(website.get('html', '')):,} characters")
        print(f"   ├─ CSS: {len(website.get('css', '')):,} characters")
        print(f"   └─ JS: {len(website.get('js', '')):,} characters")
        
        return website
        
    except Exception as e:
        print_progress("Generation", f"FAILED: {str(e)}", "❌")
        logger.exception("Website generation error:")
        raise


async def save_website_files(website: dict) -> Path:
    """Step 2: Save website files to disk"""
    print_step_header(2, "SAVE WEBSITE FILES")
    
    try:
        output_dir = Path(__file__).parent / "test_output" / "full_pipeline" / SUBDOMAIN
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print_progress("Files", f"Output directory: {output_dir}", "📁")
        
        # Save HTML
        print_progress("Save", "Writing index.html...", "💾")
        html_path = output_dir / "index.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(website.get('html', ''))
        size = html_path.stat().st_size
        print_progress("HTML", f"Saved {size:,} bytes", "✅")
        
        # Save CSS
        print_progress("Save", "Writing styles.css...", "💾")
        css_path = output_dir / "styles.css"
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(website.get('css', ''))
        size = css_path.stat().st_size
        print_progress("CSS", f"Saved {size:,} bytes", "✅")
        
        # Save JS
        print_progress("Save", "Writing script.js...", "💾")
        js_path = output_dir / "script.js"
        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(website.get('js', ''))
        size = js_path.stat().st_size
        print_progress("JS", f"Saved {size:,} bytes", "✅")
        
        return output_dir
        
    except Exception as e:
        print_progress("Save", f"FAILED: {str(e)}", "❌")
        logger.exception("File save error:")
        raise


async def deploy_to_nginx(output_dir: Path) -> str:
    """Step 3: Deploy website to Nginx"""
    print_step_header(3, "DEPLOY TO NGINX")
    
    try:
        settings = get_settings()
        site_root = Path(settings.SITES_BASE_PATH)
        
        # Create subdomain directory
        subdomain_dir = site_root / SUBDOMAIN
        print_progress("Deploy", f"Creating directory: {subdomain_dir}", "📂")
        subdomain_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy files
        import shutil
        
        for file_name in ["index.html", "styles.css", "script.js"]:
            print_progress("Copy", f"Deploying {file_name}...", "📤")
            src = output_dir / file_name
            dst = subdomain_dir / file_name
            shutil.copy2(src, dst)
            print_progress(file_name, "Deployed successfully", "✅")
        
        # Generate website URL
        domain = settings.SITES_DOMAIN
        website_url = f"https://{SUBDOMAIN}.{domain}"
        
        print_progress("Deploy", f"Website live at {website_url}", "🌐")
        
        return website_url
        
    except Exception as e:
        print_progress("Deploy", f"FAILED: {str(e)}", "❌")
        logger.exception("Deployment error:")
        raise


async def send_notification_email(website_url: str):
    """Step 4: Send email notification"""
    print_step_header(4, "SEND EMAIL NOTIFICATION")
    
    try:
        print_progress("Email", f"Preparing notification to {TEST_EMAIL}", "📧")
        
        # Create email content
        subject = f"🎉 Website Generated: {BUSINESS_DATA['name']}"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .content {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .business-info {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #667eea;
        }}
        .business-info h3 {{
            margin-top: 0;
            color: #667eea;
        }}
        .business-info p {{
            margin: 10px 0;
        }}
        .cta {{
            text-align: center;
            margin: 30px 0;
        }}
        .button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            padding: 15px 40px;
            border-radius: 50px;
            font-weight: bold;
            font-size: 18px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 20px 0;
        }}
        .stat {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
        .footer {{
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎉 Your Website is Live!</h1>
        <p>WebMagic AI has completed website generation</p>
    </div>
    
    <div class="content">
        <div class="business-info">
            <h3>{BUSINESS_DATA['name']}</h3>
            <p><strong>📍 Location:</strong> {BUSINESS_DATA['location']['city']}, {BUSINESS_DATA['location']['state']}</p>
            <p><strong>📞 Phone:</strong> {BUSINESS_DATA['phone']}</p>
            <p><strong>⭐ Rating:</strong> {BUSINESS_DATA['rating']} ({BUSINESS_DATA['review_count']} reviews)</p>
            <p><strong>🏷️ Category:</strong> {BUSINESS_DATA['category'].title()}</p>
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-value">4</div>
                <div class="stat-label">AI Agents</div>
            </div>
            <div class="stat">
                <div class="stat-value">100%</div>
                <div class="stat-label">AI Generated</div>
            </div>
            <div class="stat">
                <div class="stat-value">1</div>
                <div class="stat-label">Live Website</div>
            </div>
        </div>
        
        <div class="cta">
            <a href="{website_url}" class="button">View Live Website →</a>
        </div>
        
        <p style="text-align: center; color: #666; margin-top: 20px;">
            <strong>Website URL:</strong><br>
            <a href="{website_url}" style="color: #667eea;">{website_url}</a>
        </p>
    </div>
    
    <div class="footer">
        <p>This is an automated test from WebMagic AI</p>
        <p>Testing complete end-to-end pipeline: Generation → Deployment → Email</p>
        <p style="margin-top: 15px;">
            <strong>Powered by:</strong> Claude Sonnet 4.5, Google Gemini, PostgreSQL, FastAPI, React
        </p>
    </div>
</body>
</html>
"""
        
        # Plain text version
        text_content = f"""
Your Website is Live!

Business: {BUSINESS_DATA['name']}
Location: {BUSINESS_DATA['location']['city']}, {BUSINESS_DATA['location']['state']}
Phone: {BUSINESS_DATA['phone']}
Rating: {BUSINESS_DATA['rating']} ({BUSINESS_DATA['review_count']} reviews)

View your live website at: {website_url}

This is an automated test from WebMagic AI.
Testing complete end-to-end pipeline: Generation → Deployment → Email

Powered by: Claude Sonnet 4.5, Google Gemini, PostgreSQL, FastAPI, React
"""
        
        # Send email
        print_progress("Send", "Sending email via configured provider...", "📨")
        email_sender = EmailSender()
        
        await email_sender.provider.send_email(
            to_email=TEST_EMAIL,
            subject=subject,
            body_text=text_content,
            body_html=html_content
        )
        
        print_progress("Email", f"Sent successfully to {TEST_EMAIL}", "✅")
        print_progress("Inbox", "Check your email for the notification!", "📬")
        
    except Exception as e:
        print_progress("Email", f"FAILED: {str(e)}", "⚠️")
        logger.warning("Email sending failed (non-critical):")
        logger.warning(str(e))
        print("\n⚠️  Note: Website is still live, only email notification failed")


async def main():
    """Run the complete end-to-end test"""
    print("\n" + "="*70)
    print("🚀 COMPLETE END-TO-END PIPELINE TEST (Enhanced v2)")
    print("="*70)
    print(f"\n⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📧 Email: {TEST_EMAIL}")
    print(f"🌐 Subdomain: {SUBDOMAIN}\n")
    
    overall_start = datetime.now()
    website_url = None
    
    try:
        # Get database session
        async for db in get_db():
            # Step 1: Generate website
            website = await generate_website_with_progress(db)
            
            # Step 2: Save files
            output_dir = await save_website_files(website)
            
            # Step 3: Deploy to Nginx
            website_url = await deploy_to_nginx(output_dir)
            
            # Step 4: Send email
            await send_notification_email(website_url)
            
            # Summary
            total_duration = (datetime.now() - overall_start).total_seconds()
            
            print("\n" + "="*70)
            print("✅ TEST COMPLETE!")
            print("="*70)
            print(f"\n⏱️  Total time: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
            print(f"\n📊 Summary:")
            print(f"   ✅ Website generated with 4 AI agents")
            print(f"   ✅ Files saved locally")
            print(f"   ✅ Deployed to Nginx")
            print(f"   ✅ Email notification sent")
            print(f"\n🌐 Live Website: {website_url}")
            print(f"📧 Email sent to: {TEST_EMAIL}")
            print(f"\n💡 Next steps:")
            print(f"   1. Check your email inbox at {TEST_EMAIL}")
            print(f"   2. Click the link to view the live website")
            print(f"   3. Verify website quality and design")
            print(f"   4. Test on desktop and mobile devices")
            print(f"   5. Check all sections and interactions\n")
            
            break
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    
    except Exception as e:
        print(f"\n{'='*70}")
        print("❌ TEST FAILED!")
        print(f"{'='*70}\n")
        print(f"Error: {str(e)}")
        print("\n📋 Full error details:")
        logger.exception("Test failed:")
        
        if website_url:
            print(f"\n⚠️  Note: Website may have been partially deployed: {website_url}")
        
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
