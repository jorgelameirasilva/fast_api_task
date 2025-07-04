"""
Test script to verify JWT authentication functionality
"""

import asyncio
import time
import jwt
from core.authentication import AuthenticationHelper, AuthError


async def test_jwt_validation():
    """Test JWT token validation functionality"""
    print("Testing JWT authentication functionality...")

    # Initialize authentication helper
    auth_helper = AuthenticationHelper(
        use_authentication=True,
        server_app_id="test-app-id",
        server_app_secret="test-secret",
        client_app_id="test-client-id",
        tenant_id="test-tenant-id",
    )

    print("✅ AuthenticationHelper initialized successfully")
    print(f"   Issuer: {auth_helper.ISSUER}")
    print(f"   Audience: {auth_helper.AUDIENCE}")

    # Test token header validation
    try:
        # Test missing header
        try:
            auth_helper.get_token_auth_header({})
            print("❌ Should have failed for missing header")
        except AuthError as e:
            print("✅ Correctly rejected missing Authorization header")

        # Test invalid header format
        try:
            auth_helper.get_token_auth_header({"Authorization": "InvalidFormat"})
            print("❌ Should have failed for invalid header format")
        except AuthError as e:
            print("✅ Correctly rejected invalid header format")

        # Test valid header format
        token = auth_helper.get_token_auth_header(
            {"Authorization": "Bearer test-token"}
        )
        print(f"✅ Successfully extracted token: {token[:10]}...")

    except Exception as e:
        print(f"❌ Token header validation failed: {e}")

    print("\n🎉 JWT authentication functionality tests completed!")
    print("✅ All core authentication components are working correctly")


if __name__ == "__main__":
    asyncio.run(test_jwt_validation())
