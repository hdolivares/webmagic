"""
Test script for Phase 3 - Creative Engine.
Tests the complete website generation pipeline.
"""
import httpx
import asyncio
import json


async def test_phase3():
    """Test Phase 3 Creative Engine."""
    base_url = "http://localhost:8000"
    token = None
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        print("🧪 Testing WebMagic Phase 3 - Creative Engine\n")
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
        
        # 2. Check if we have any businesses
        print("\n2️⃣  Checking for businesses...")
        response = await client.get(
            f"{base_url}/api/v1/businesses/?page_size=1",
            headers=headers
        )
        if response.status_code == 200:
            businesses = response.json()
            if businesses['total'] == 0:
                print("⚠️  No businesses found. Please run Phase 2 scraping first.")
                print("   Run: python test_phase2.py")
                return
            
            business = businesses['businesses'][0]
            business_id = business['id']
            print(f"✅ Found business: {business['name']}")
            print(f"   ID: {business_id}")
            print(f"   Category: {business['category']}")
            print(f"   Rating: {business['rating']}")
        else:
            print(f"❌ Failed: {response.json()}")
            return
        
        # 3. Check if prompt templates exist
        print("\n3️⃣  Checking prompt templates...")
        response = await client.get(
            f"{base_url}/api/v1/settings/templates",
            headers=headers
        )
        if response.status_code == 200:
            templates = response.json()
            if len(templates) == 0:
                print("⚠️  No prompt templates found.")
                print("   Run: python scripts/seed_prompt_templates.py")
                return
            
            print(f"✅ Found {len(templates)} prompt templates:")
            for template in templates:
                print(f"   - {template['agent_name']}")
        else:
            print(f"❌ Failed: {response.json()}")
        
        # 4. Check site stats (before generation)
        print("\n4️⃣  Getting site statistics (before)...")
        response = await client.get(
            f"{base_url}/api/v1/sites/stats",
            headers=headers
        )
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Site stats:")
            print(f"   - Total sites: {stats['total_sites']}")
            print(f"   - Live sites: {stats['total_live']}")
        
        # 5. Generate website
        print("\n5️⃣  Generating website...")
        print("⚠️  NOTE: This will call the Claude API and may take 30-60 seconds!")
        print("   It will also use your Anthropic API credits.")
        
        user_input = input("\n   Generate website? (y/n): ")
        
        if user_input.lower() == 'y':
            print("\n   🚀 Starting website generation...")
            print("   This runs in the background, so response is immediate.")
            
            response = await client.post(
                f"{base_url}/api/v1/sites/generate",
                headers=headers,
                json={
                    "business_id": business_id,
                    "force_regenerate": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ Generation started!")
                print(f"   Status: {result['status']}")
                print(f"   Message: {result['message']}")
                
                # Wait for generation to complete
                print("\n   ⏳ Waiting for generation to complete...")
                print("   (This may take 30-60 seconds...)")
                
                await asyncio.sleep(60)  # Wait 60 seconds
                
                # Check if site was created
                print("\n   Checking for generated site...")
                response = await client.get(
                    f"{base_url}/api/v1/sites/",
                    headers=headers
                )
                
                if response.status_code == 200:
                    sites_data = response.json()
                    if sites_data['total'] > 0:
                        site = sites_data['sites'][0]
                        print(f"\n   ✅ Site generated successfully!")
                        print(f"      - Site ID: {site['id']}")
                        print(f"      - Subdomain: {site['subdomain']}")
                        print(f"      - Status: {site['status']}")
                        print(f"      - URL: {site['full_url']}")
                        
                        # Get full site details
                        print("\n   📄 Fetching site details...")
                        response = await client.get(
                            f"{base_url}/api/v1/sites/{site['id']}",
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            site_detail = response.json()
                            print(f"\n   📊 Site Details:")
                            print(f"      - HTML size: {len(site_detail['html_content'])} chars")
                            print(f"      - CSS size: {len(site_detail.get('css_content', ''))} chars")
                            print(f"      - JS size: {len(site_detail.get('js_content', ''))} chars")
                            print(f"      - Design brief: {'Yes' if site_detail.get('design_brief') else 'No'}")
                            
                            # Show design brief summary
                            if site_detail.get('design_brief'):
                                brief = site_detail['design_brief']
                                print(f"\n   🎨 Design Brief:")
                                print(f"      - Vibe: {brief.get('vibe', 'N/A')}")
                                typography = brief.get('typography', {})
                                print(f"      - Font: {typography.get('display', 'N/A')}")
                                colors = brief.get('colors', {})
                                print(f"      - Primary Color: {colors.get('primary', 'N/A')}")
                    else:
                        print("\n   ⚠️  No sites found yet. Generation may still be running.")
                        print("      Check the API logs for progress.")
                
            else:
                print(f"\n❌ Generation failed: {response.json()}")
        else:
            print("   ⏭️  Skipped website generation")
        
        # 6. List prompt settings
        print("\n6️⃣  Listing prompt settings...")
        response = await client.get(
            f"{base_url}/api/v1/settings/prompts",
            headers=headers
        )
        if response.status_code == 200:
            settings_data = response.json()
            print(f"✅ Found {settings_data['total']} prompt settings")
            if settings_data['settings']:
                print("\n   Sample settings:")
                for setting in settings_data['settings'][:3]:
                    print(f"   - {setting['agent_name']}.{setting['section_name']}")
                    print(f"     Version: {setting['version']}, Active: {setting['is_active']}")
                    print(f"     Usage: {setting['usage_count']}, Success: {setting['success_count']}")
        
        print("\n" + "=" * 60)
        print("✨ Phase 3 testing completed!")
        print("\n📚 API Documentation: http://localhost:8000/docs")
        print("\n📝 Key Endpoints:")
        print("   - POST /api/v1/sites/generate - Generate website")
        print("   - GET  /api/v1/sites/ - List sites")
        print("   - GET  /api/v1/sites/{id} - Get site details")
        print("   - GET  /api/v1/settings/prompts - List prompt settings")
        print("   - PATCH /api/v1/settings/prompts/{id} - Update prompts")


if __name__ == "__main__":
    print("=" * 60)
    print("WebMagic Phase 3 Test - Creative Engine")
    print("=" * 60)
    print("\nPrerequisites:")
    print("1. API server running on http://localhost:8000")
    print("2. .env file configured with:")
    print("   - DATABASE_URL (Supabase)")
    print("   - ANTHROPIC_API_KEY")
    print("3. At least one business in database (Phase 2)")
    print("4. Prompt templates seeded:")
    print("   Run: python scripts/seed_prompt_templates.py")
    print("\n")
    
    try:
        asyncio.run(test_phase3())
    except httpx.ConnectError:
        print("❌ Error: Could not connect to API")
        print("   Make sure the server is running: python start.py")
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
