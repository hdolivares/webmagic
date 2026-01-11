"""
Test script for Phase 4 - Pitcher (Email Outreach).
Tests email generation, sending, and campaign management.
"""
import httpx
import asyncio


async def test_phase4():
    """Test Phase 4 Pitcher module."""
    base_url = "http://localhost:8000"
    token = None
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("🧪 Testing WebMagic Phase 4 - Pitcher (Email Outreach)\n")
        print("=" * 60)
        
        # 1. Login
        print("\n1️⃣  Logging in...")
        response = await client.post(
            f"{base_url}/api/v1/auth/login",
            json={"email": "admin@webmagic.com", "password": "admin123"}
        )
        
        if response.status_code != 200:
            print(f"❌ Login failed: {response.json()}")
            return
        
        data = response.json()
        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"✅ Logged in as {data['user']['email']}")
        
        # 2. Check for businesses with emails
        print("\n2️⃣  Looking for businesses with emails...")
        response = await client.get(
            f"{base_url}/api/v1/businesses/?has_email=true&page_size=1",
            headers=headers
        )
        
        if response.status_code == 200:
            businesses = response.json()
            if businesses['total'] == 0:
                print("⚠️  No businesses with emails found.")
                print("   Run Phase 2 scraping first to get businesses.")
                return
            
            business = businesses['businesses'][0]
            business_id = business['id']
            print(f"✅ Found business: {business['name']}")
            print(f"   Email: {business['email']}")
            print(f"   Category: {business['category']}")
        else:
            print(f"❌ Failed: {response.json()}")
            return
        
        # 3. Get campaign stats (before)
        print("\n3️⃣  Getting campaign statistics (before)...")
        response = await client.get(
            f"{base_url}/api/v1/campaigns/stats",
            headers=headers
        )
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Campaign stats:")
            print(f"   - Total campaigns: {stats['total_campaigns']}")
            print(f"   - Total sent: {stats['total_sent']}")
            print(f"   - Open rate: {stats['open_rate']}%")
            print(f"   - Click rate: {stats['click_rate']}%")
        
        # 4. Test email configuration
        print("\n4️⃣  Testing email configuration...")
        user_test_email = input("\n   Enter your email to receive test (or press Enter to skip): ")
        
        if user_test_email.strip():
            print(f"\n   Sending test email to {user_test_email}...")
            response = await client.post(
                f"{base_url}/api/v1/campaigns/test-email",
                headers=headers,
                json={
                    "to_email": user_test_email,
                    "subject": "WebMagic Email Test"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Test email sent!")
                print(f"   Provider: {result.get('provider')}")
                print(f"   Message ID: {result.get('message_id')}")
                print(f"\n   Check your inbox for the test email.")
            else:
                print(f"❌ Test failed: {response.json()}")
                print("\n   Make sure your .env has email credentials:")
                print("   - For SES: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
                print("   - For SendGrid: SENDGRID_API_KEY")
        else:
            print("   ⏭️  Skipped email test")
        
        # 5. Create campaign
        print("\n5️⃣  Creating email campaign...")
        response = await client.post(
            f"{base_url}/api/v1/campaigns/",
            headers=headers,
            json={
                "business_id": business_id,
                "variant": "default"
            }
        )
        
        if response.status_code == 201:
            campaign = response.json()
            campaign_id = campaign['id']
            print(f"✅ Campaign created!")
            print(f"   Campaign ID: {campaign_id}")
            print(f"   Subject: {campaign['subject_line']}")
            print(f"   Recipient: {campaign['recipient_email']}")
            print(f"   Status: {campaign['status']}")
            
            # Show email preview
            print(f"\n   📧 Email Preview:")
            response = await client.get(
                f"{base_url}/api/v1/campaigns/{campaign_id}",
                headers=headers
            )
            if response.status_code == 200:
                detail = response.json()
                print(f"   Subject: {detail['subject_line']}")
                print(f"   Preview: {detail.get('preview_text', 'N/A')}")
                print(f"\n   Body (first 200 chars):")
                print(f"   {detail['email_body'][:200]}...")
            
            # 6. Send campaign (optional)
            print("\n6️⃣  Ready to send campaign...")
            print("⚠️  This will send an actual email!")
            user_send = input("\n   Send campaign? (y/n): ")
            
            if user_send.lower() == 'y':
                print("\n   Sending campaign...")
                response = await client.post(
                    f"{base_url}/api/v1/campaigns/{campaign_id}/send",
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Campaign sent!")
                    print(f"   Status: {result['status']}")
                    
                    # Get updated campaign
                    response = await client.get(
                        f"{base_url}/api/v1/campaigns/{campaign_id}",
                        headers=headers
                    )
                    if response.status_code == 200:
                        updated = response.json()
                        print(f"   Sent at: {updated.get('sent_at', 'N/A')}")
                        print(f"   Provider: {updated.get('email_provider', 'N/A')}")
                else:
                    print(f"❌ Send failed: {response.json()}")
            else:
                print("   ⏭️  Skipped sending")
        else:
            print(f"❌ Campaign creation failed: {response.json()}")
            return
        
        # 7. List campaigns
        print("\n7️⃣  Listing campaigns...")
        response = await client.get(
            f"{base_url}/api/v1/campaigns/?page_size=5",
            headers=headers
        )
        if response.status_code == 200:
            campaigns_data = response.json()
            print(f"✅ Found {campaigns_data['total']} total campaigns")
            print(f"\n   Recent campaigns:")
            for camp in campaigns_data['campaigns'][:5]:
                print(f"   - {camp['business_name']} ({camp['status']})")
                print(f"     Subject: {camp['subject_line']}")
                if camp.get('opened_at'):
                    print(f"     ✅ Opened at: {camp['opened_at']}")
                if camp.get('clicked_at'):
                    print(f"     🖱️  Clicked at: {camp['clicked_at']}")
        
        # 8. Updated stats
        print("\n8️⃣  Getting updated campaign statistics...")
        response = await client.get(
            f"{base_url}/api/v1/campaigns/stats",
            headers=headers
        )
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Updated stats:")
            print(f"   - Total campaigns: {stats['total_campaigns']}")
            print(f"   - Total sent: {stats['total_sent']}")
            print(f"   - Sent (24h): {stats['sent_24h']}")
            print(f"   - Open rate: {stats['open_rate']}%")
            print(f"   - Click rate: {stats['click_rate']}%")
            print(f"   - Reply rate: {stats['reply_rate']}%")
        
        print("\n" + "=" * 60)
        print("✨ Phase 4 testing completed!")
        print("\n📚 API Documentation: http://localhost:8000/docs")
        print("\n📝 Key Endpoints:")
        print("   - POST /api/v1/campaigns/ - Create campaign")
        print("   - POST /api/v1/campaigns/{id}/send - Send campaign")
        print("   - GET  /api/v1/campaigns/ - List campaigns")
        print("   - GET  /api/v1/campaigns/stats - Statistics")
        print("   - POST /api/v1/campaigns/test-email - Test email config")


if __name__ == "__main__":
    print("=" * 60)
    print("WebMagic Phase 4 Test - Pitcher (Email Outreach)")
    print("=" * 60)
    print("\nPrerequisites:")
    print("1. API server running on http://localhost:8000")
    print("2. .env file configured with email provider:")
    print("   - For AWS SES:")
    print("     EMAIL_PROVIDER=ses")
    print("     AWS_ACCESS_KEY_ID=your-key")
    print("     AWS_SECRET_ACCESS_KEY=your-secret")
    print("     AWS_REGION=us-east-1")
    print("     EMAIL_FROM=your-verified-email@domain.com")
    print("\n   - For SendGrid:")
    print("     EMAIL_PROVIDER=sendgrid")
    print("     SENDGRID_API_KEY=your-api-key")
    print("     EMAIL_FROM=your-verified-email@domain.com")
    print("\n3. At least one business with email (Phase 2)")
    print("\n")
    
    try:
        asyncio.run(test_phase4())
    except httpx.ConnectError:
        print("❌ Error: Could not connect to API")
        print("   Make sure the server is running: python start.py")
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
