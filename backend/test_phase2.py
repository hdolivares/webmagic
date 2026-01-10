"""
Test script for Phase 2 - Hunter Module.
Tests the entire scraping workflow.
"""
import httpx
import asyncio
import json


async def test_phase2():
    """Test Phase 2 Hunter module endpoints."""
    base_url = "http://localhost:8000"
    token = None
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🧪 Testing WebMagic Phase 2 - Hunter Module\n")
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
        
        # 2. Get business stats (should be empty)
        print("\n2️⃣  Getting business statistics...")
        response = await client.get(
            f"{base_url}/api/v1/businesses/stats",
            headers=headers
        )
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Business stats:")
            print(f"   - Total leads: {stats['total_leads']}")
            print(f"   - Qualified leads: {stats['qualified_leads']}")
            print(f"   - With email: {stats['with_email']}")
            print(f"   - Without website: {stats['without_website']}")
        else:
            print(f"❌ Failed: {response.json()}")
        
        # 3. Get coverage stats (should be empty)
        print("\n3️⃣  Getting coverage statistics...")
        response = await client.get(
            f"{base_url}/api/v1/coverage/stats",
            headers=headers
        )
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Coverage stats:")
            print(f"   - Total territories: {stats['total_territories']}")
            print(f"   - Pending: {stats['pending']}")
            print(f"   - Total leads scraped: {stats['total_leads']}")
            print(f"   - Avg qualification rate: {stats['avg_qualification_rate']:.2f}%")
        else:
            print(f"❌ Failed: {response.json()}")
        
        # 4. Create a coverage entry
        print("\n4️⃣  Creating coverage entry...")
        response = await client.post(
            f"{base_url}/api/v1/coverage/",
            headers=headers,
            json={
                "state": "TX",
                "city": "Austin",
                "country": "US",
                "industry": "Coffee Shop",
                "priority": 80
            }
        )
        if response.status_code == 201:
            coverage = response.json()
            coverage_id = coverage['id']
            print(f"✅ Created coverage entry: {coverage_id}")
            print(f"   Location: {coverage['city']}, {coverage['state']}")
            print(f"   Industry: {coverage['industry']}")
            print(f"   Status: {coverage['status']}")
        else:
            print(f"❌ Failed: {response.json()}")
            return
        
        # 5. Trigger scraping (this will actually call Outscraper API)
        print("\n5️⃣  Testing scraping endpoint...")
        print("⚠️  NOTE: This will use your Outscraper API credits!")
        print("   To test without API calls, skip this step.")
        
        user_input = input("\n   Run actual scrape? (y/n): ")
        
        if user_input.lower() == 'y':
            print("\n   Starting scrape...")
            response = await client.post(
                f"{base_url}/api/v1/coverage/scrape",
                headers=headers,
                json={
                    "city": "Austin",
                    "state": "TX",
                    "industry": "Coffee Shop",
                    "limit": 10,  # Small limit for testing
                    "country": "US"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ Scraping initiated!")
                print(f"   Status: {result['status']}")
                print(f"   Message: {result['message']}")
                
                # Wait a bit for background task
                print("\n   Waiting for scraping to complete...")
                await asyncio.sleep(15)
                
                # Check updated stats
                print("\n   Checking updated stats...")
                response = await client.get(
                    f"{base_url}/api/v1/businesses/stats",
                    headers=headers
                )
                if response.status_code == 200:
                    stats = response.json()
                    print(f"\n   📊 Updated Business Stats:")
                    print(f"      - Total leads: {stats['total_leads']}")
                    print(f"      - Qualified: {stats['qualified_leads']}")
                    print(f"      - With email: {stats['with_email']}")
                    print(f"      - Without website: {stats['without_website']}")
                
                # List businesses
                print("\n   📋 Listing businesses...")
                response = await client.get(
                    f"{base_url}/api/v1/businesses/?page_size=5",
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f"\n   Found {data['total']} total businesses")
                    print(f"   Showing first {len(data['businesses'])}:\n")
                    
                    for biz in data['businesses']:
                        print(f"      • {biz['name']}")
                        print(f"        Email: {biz['email'] or 'N/A'}")
                        print(f"        Rating: {biz['rating'] or 'N/A'}")
                        print(f"        Score: {biz['qualification_score']}")
                        print()
            else:
                print(f"❌ Scraping failed: {response.json()}")
        else:
            print("   ⏭️  Skipped actual scraping")
        
        # 6. Get scraping report
        print("\n6️⃣  Getting scraping report...")
        response = await client.get(
            f"{base_url}/api/v1/coverage/report/scraping",
            headers=headers
        )
        if response.status_code == 200:
            report = response.json()
            print(f"✅ Scraping report:")
            print(f"\n   Summary:")
            print(f"   - Territories tracked: {report['summary']['territories_tracked']}")
            print(f"   - Territories pending: {report['summary']['territories_pending']}")
            print(f"   - Total leads in DB: {report['summary']['total_businesses_in_db']}")
            print(f"   - Without website: {report['summary']['businesses_without_website']}")
        else:
            print(f"❌ Failed: {response.json()}")
        
        print("\n" + "=" * 60)
        print("✨ Phase 2 testing completed!")
        print("\n📚 API Documentation: http://localhost:8000/docs")


if __name__ == "__main__":
    print("=" * 60)
    print("WebMagic Phase 2 Test - Hunter Module")
    print("=" * 60)
    print("\nPrerequisites:")
    print("1. API server running on http://localhost:8000")
    print("2. .env file configured with:")
    print("   - DATABASE_URL (Supabase)")
    print("   - OUTSCRAPER_API_KEY")
    print("   - Other required keys")
    print("\n")
    
    try:
        asyncio.run(test_phase2())
    except httpx.ConnectError:
        print("❌ Error: Could not connect to API")
        print("   Make sure the server is running: python start.py")
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
