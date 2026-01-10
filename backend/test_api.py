"""
Quick test script to verify the API is working.
"""
import httpx
import asyncio


async def test_api():
    """Test basic API endpoints."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        print("🧪 Testing WebMagic API...\n")
        
        # Test health check
        print("1️⃣  Testing health check endpoint...")
        response = await client.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
        
        # Test root endpoint
        print("2️⃣  Testing root endpoint...")
        response = await client.get(f"{base_url}/")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
        
        # Test login
        print("3️⃣  Testing login endpoint...")
        login_data = {
            "email": "admin@webmagic.com",
            "password": "admin123"
        }
        response = await client.post(
            f"{base_url}/api/v1/auth/login",
            json=login_data
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Login successful!")
            print(f"   User: {data['user']['email']}")
            print(f"   Role: {data['user']['role']}")
            token = data["access_token"]
            
            # Test protected endpoint
            print("\n4️⃣  Testing protected endpoint (/auth/me)...")
            response = await client.get(
                f"{base_url}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ Token verified!")
                print(f"   User info: {response.json()}")
            else:
                print(f"   ❌ Failed: {response.json()}")
        else:
            print(f"   ❌ Login failed: {response.json()}")
        
        print("\n✨ API tests completed!")


if __name__ == "__main__":
    print("=" * 60)
    print("WebMagic API Test")
    print("=" * 60 + "\n")
    print("Make sure the API is running on http://localhost:8000")
    print("Run: uvicorn api.main:app --reload\n")
    
    try:
        asyncio.run(test_api())
    except httpx.ConnectError:
        print("❌ Error: Could not connect to API.")
        print("   Make sure the server is running on http://localhost:8000")
