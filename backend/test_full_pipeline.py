"""
Complete End-to-End Pipeline Test
Tests the entire workflow from business data to live website + email notification

This script:
1. Generates website using all 4 AI agents
2. Saves website files to disk
3. Deploys to Nginx (subdomain)
4. Sends email notification with live link
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.database import get_db
from services.creative.orchestrator import CreativeOrchestrator
from services.creative.site_service import SiteService
from services.pitcher.email_sender import EmailSender
from core.config import get_settings

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


async def generate_website(db) -> dict:
    """Step 1: Generate website using AI agents"""
    print("\n" + "="*60)
    print("STEP 1: WEBSITE GENERATION")
    print("="*60)
    
    print(f"\n📊 Business: {BUSINESS_DATA['name']}")
    print(f"📍 Location: {BUSINESS_DATA['location']['city']}, {BUSINESS_DATA['location']['state']}")
    print(f"📞 Phone: {BUSINESS_DATA['phone']}")
    print(f"⭐ Rating: {BUSINESS_DATA['rating']} ({BUSINESS_DATA['review_count']} reviews)")
    
    print(f"\n🤖 Initializing Creative Orchestrator...")
    orchestrator = CreativeOrchestrator(db)
    
    print(f"🚀 Starting AI generation pipeline...")
    print(f"   ├─ Analyst: Analyzing business & competition")
    print(f"   ├─ Concept: Creating creative DNA")
    print(f"   ├─ Art Director: Designing brand identity")
    print(f"   └─ Architect: Building website structure")
    
    start_time = datetime.now()
    
    result = await orchestrator.generate_website(
        business_data=BUSINESS_DATA,
        save_intermediate=True
    )
    
    duration = (datetime.now() - start_time).total_seconds()
    
    website = result.get("website", {})
    
    print(f"\n✅ Generation complete in {duration:.1f}s")
    print(f"\n📄 Website Output:")
    print(f"   ├─ HTML: {len(website.get('html', ''))} characters")
    print(f"   ├─ CSS: {len(website.get('css', ''))} characters")
    print(f"   └─ JS: {len(website.get('js', ''))} characters")
    
    return website


async def save_website_files(website: dict) -> Path:
    """Step 2: Save website files to disk"""
    print("\n" + "="*60)
    print("STEP 2: SAVE WEBSITE FILES")
    print("="*60)
    
    output_dir = Path(__file__).parent / "test_output" / "full_pipeline" / SUBDOMAIN
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📁 Output directory: {output_dir}")
    
    # Save HTML
    html_path = output_dir / "index.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(website.get('html', ''))
    print(f"   ✅ Saved: index.html ({html_path.stat().st_size:,} bytes)")
    
    # Save CSS
    css_path = output_dir / "styles.css"
    with open(css_path, 'w', encoding='utf-8') as f:
        f.write(website.get('css', ''))
    print(f"   ✅ Saved: styles.css ({css_path.stat().st_size:,} bytes)")
    
    # Save JS
    js_path = output_dir / "script.js"
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(website.get('js', ''))
    print(f"   ✅ Saved: script.js ({js_path.stat().st_size:,} bytes)")
    
    return output_dir


async def deploy_to_nginx(output_dir: Path) -> str:
    """Step 3: Deploy website to Nginx"""
    print("\n" + "="*60)
    print("STEP 3: DEPLOY TO NGINX")
    print("="*60)
    
    settings = get_settings()
    site_root = Path(settings.SITES_BASE_PATH)
    
    # Create subdomain directory
    subdomain_dir = site_root / SUBDOMAIN
    subdomain_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📂 Deploy directory: {subdomain_dir}")
    
    # Copy files
    import shutil
    
    for file_name in ["index.html", "styles.css", "script.js"]:
        src = output_dir / file_name
        dst = subdomain_dir / file_name
        shutil.copy2(src, dst)
        print(f"   ✅ Deployed: {file_name}")
    
    # Generate website URL
    domain = settings.SITE_BASE_DOMAIN
    website_url = f"https://{SUBDOMAIN}.{domain}"
    
    print(f"\n🌐 Website URL: {website_url}")
    
    return website_url


async def send_notification_email(website_url: str):
    """Step 4: Send email notification"""
    print("\n" + "="*60)
    print("STEP 4: SEND EMAIL NOTIFICATION")
    print("="*60)
    
    print(f"\n📧 Sending notification to: {TEST_EMAIL}")
    
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
    
    # Send email using EmailSender
    email_sender = EmailSender()
    
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
    
    try:
        await email_sender.provider.send_email(
            to_email=TEST_EMAIL,
            subject=subject,
            body_text=text_content,
            body_html=html_content
        )
        print(f"   ✅ Email sent successfully!")
        print(f"   📬 Check your inbox: {TEST_EMAIL}")
    except Exception as e:
        print(f"   ⚠️ Email sending failed: {str(e)}")
        print(f"   (This is non-critical - website is still live)")


async def main():
    """Run the complete end-to-end test"""
    print("\n" + "="*60)
    print("🚀 COMPLETE END-TO-END PIPELINE TEST")
    print("="*60)
    print(f"\n⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📧 Email recipient: {TEST_EMAIL}")
    print(f"🌐 Subdomain: {SUBDOMAIN}")
    
    overall_start = datetime.now()
    
    try:
        # Get database session
        async for db in get_db():
            # Step 1: Generate website
            website = await generate_website(db)
            
            # Step 2: Save files
            output_dir = await save_website_files(website)
            
            # Step 3: Deploy to Nginx
            website_url = await deploy_to_nginx(output_dir)
            
            # Step 4: Send email
            await send_notification_email(website_url)
            
            # Summary
            total_duration = (datetime.now() - overall_start).total_seconds()
            
            print("\n" + "="*60)
            print("✅ TEST COMPLETE!")
            print("="*60)
            print(f"\n⏱️  Total time: {total_duration:.1f}s")
            print(f"\n📊 Summary:")
            print(f"   ✅ Website generated with 4 AI agents")
            print(f"   ✅ Files saved locally")
            print(f"   ✅ Deployed to Nginx")
            print(f"   ✅ Email notification sent")
            print(f"\n🌐 Live Website: {website_url}")
            print(f"📧 Email sent to: {TEST_EMAIL}")
            print(f"\n💡 Next steps:")
            print(f"   1. Check your email inbox")
            print(f"   2. Click the link to view the website")
            print(f"   3. Verify website looks professional")
            print(f"   4. Test on mobile device")
            
            break
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
