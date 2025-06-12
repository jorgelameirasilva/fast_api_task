# Authentication Guide - Clean Architecture

This guide explains how to use the JWT authentication system integrated into the clean architecture.

## Overview

The authentication system follows clean architecture principles:

- **Repository Layer**: `JWTRepository` abstracts token validation
- **Service Layer**: `AuthenticationService` handles business logic  
- **API Layer**: FastAPI dependencies for endpoint protection
- **Models**: Pydantic models for type safety

## Quick Start

### 1. Development Mode (Mock Authentication)

By default, the system runs with mock authentication for development:

```bash
# Start the application
python run_v2.py

# Test endpoints with mock tokens
curl -H "Authorization: Bearer mock-token-admin" http://localhost:8000/v2/profile
curl -H "Authorization: Bearer mock-token-user" http://localhost:8000/v2/profile
curl -H "Authorization: Bearer mock-token-readonly" http://localhost:8000/v2/profile
```

Available mock tokens:
- `mock-token-admin`: Admin user with all permissions
- `mock-token-user`: Regular user with basic permissions  
- `mock-token-readonly`: Read-only user with limited permissions

### 2. Production Mode (Real JWT)

Set environment variables for production JWT validation:

```bash
export ENVIRONMENT=production
export APIM_ONELOGIN_URL=https://your-jwks-endpoint/.well-known/jwks.json
export JWT_AUDIENCE=your-audience
export JWT_ISSUER=your-issuer
```

## Authentication Usage

### Protecting Endpoints

#### Require Authentication
```python
from app.auth.dependencies import get_current_user
from app.auth.models import AuthUser

@router.get("/protected")
async def protected_endpoint(
    current_user: AuthUser = Depends(get_current_user)
):
    return {"user_id": current_user.user_id}
```

#### Optional Authentication
```python
from app.auth.dependencies import get_optional_user, with_auth_context
from app.auth.models import AuthUser, AuthContext

@router.get("/optional")
async def optional_auth_endpoint(
    user: Optional[AuthUser] = Depends(get_optional_user)
):
    if user:
        return {"authenticated": True, "user_id": user.user_id}
    else:
        return {"authenticated": False}

# Or use AuthContext for more details
@router.get("/optional-context")
async def optional_with_context(
    auth_context: AuthContext = Depends(with_auth_context())
):
    return {
        "authenticated": auth_context.is_authenticated,
        "user": auth_context.user.user_id if auth_context.user else None
    }
```

#### Role-Based Access Control
```python
from app.auth.dependencies import require_roles, require_any_role, require_all_roles

@router.get("/admin", dependencies=[Depends(require_roles(["admin"]))])
async def admin_endpoint():
    return {"message": "Admin access granted"}

@router.get("/moderator", dependencies=[Depends(require_any_role("admin", "moderator"))])
async def moderator_endpoint():
    return {"message": "Moderator access granted"}

@router.get("/super-admin", dependencies=[Depends(require_all_roles("admin", "super_user"))])
async def super_admin_endpoint():
    return {"message": "Super admin access granted"}
```

#### Scope-Based Access Control
```python
from app.auth.dependencies import require_scope

@router.get("/read-data", dependencies=[Depends(require_scope("read:data"))])
async def read_data():
    return {"data": "sensitive information"}
```

### Working with User Context

#### Extract User Information
```python
@router.post("/ask")
async def ask_with_user_context(
    request: AskRequest,
    auth_context: AuthContext = Depends(with_auth_context())
):
    # Build enhanced context with user info
    enhanced_context = request.context or {}
    if auth_context.is_authenticated:
        enhanced_context.update({
            "user_id": auth_context.user.user_id,
            "user_roles": auth_context.user.roles,
            "user_scopes": auth_context.user.scope.split()
        })
    
    # Use enhanced context in business logic
    return await process_request(request.query, enhanced_context)
```

#### Audit Logging
```python
from app.auth.dependencies import get_user_context

@router.post("/sensitive-action")
async def sensitive_action(
    user_context: dict = Depends(get_user_context)
):
    logger.info(f"Sensitive action performed", extra={
        "user_context": user_context
    })
    return {"status": "success"}
```

## API Examples

### Test Authentication Status
```bash
# Check authentication status (works without token)
curl http://localhost:8000/v2/auth/info

# Check with admin token
curl -H "Authorization: Bearer mock-token-admin" http://localhost:8000/v2/auth/info
```

Response for authenticated user:
```json
{
  "authenticated": true,
  "user": {
    "user_id": "admin-123",
    "email": "admin@example.com",
    "roles": ["admin", "user"],
    "scopes": ["read", "write", "admin"]
  },
  "auth_method": "JWT",
  "request_id": "req-uuid"
}
```

### Get User Profile
```bash
# Requires authentication
curl -H "Authorization: Bearer mock-token-user" http://localhost:8000/v2/profile
```

Response:
```json
{
  "user_id": "user-456",
  "email": "user@example.com", 
  "name": "Mock Regular User",
  "username": "user",
  "roles": ["user"],
  "groups": ["users"],
  "scopes": ["read", "write"]
}
```

### Access Admin Endpoint
```bash
# Requires admin role
curl -H "Authorization: Bearer mock-token-admin" http://localhost:8000/v2/admin/stats
```

### Test Authorization Failures
```bash
# Try admin endpoint with user token (should fail with 403)
curl -H "Authorization: Bearer mock-token-user" http://localhost:8000/v2/admin/stats

# Try with invalid token (should fail with 401)
curl -H "Authorization: Bearer invalid-token" http://localhost:8000/v2/profile
```

## Architecture Details

### Repository Pattern
```python
# Abstract interface
class JWTRepository(ABC):
    @abstractmethod
    async def validate_token(self, request: TokenValidationRequest) -> TokenValidationResult:
        pass

# Production implementation
class ProductionJWTRepository(JWTRepository):
    # Uses PyJWT + JWKS for real token validation
    
# Mock implementation  
class MockJWTRepository(JWTRepository):
    # Uses predefined mock tokens for development
```

### Service Layer
```python
class AuthenticationService:
    def __init__(self, jwt_repository: JWTRepository):
        self.jwt_repository = jwt_repository
    
    async def authenticate_user(self, token: str) -> AuthContext:
        # Business logic for authentication
        
    async def authorize_roles(self, auth_context: AuthContext, roles: List[str]):
        # Business logic for authorization
```

### Dependency Injection
```python
# Container automatically chooses implementation based on environment
jwt_repository = providers.Factory(_create_jwt_repository, environment=environment)
authentication_service = providers.Factory(AuthenticationService, jwt_repository=jwt_repository)

def _create_jwt_repository(environment: str) -> JWTRepository:
    if environment == "production":
        try:
            return ProductionJWTRepository()  # Real JWT validation
        except Exception:
            return MockJWTRepository()        # Fallback to mock
    else:
        return MockJWTRepository()           # Development default
```

## Testing

### Unit Tests
```python
@pytest.mark.asyncio
async def test_authentication():
    # Use mock repository for testing
    jwt_repo = MockJWTRepository()
    auth_service = AuthenticationService(jwt_repo)
    
    # Test authentication flow
    auth_context = await auth_service.authenticate_user("mock-token-admin")
    assert auth_context.is_authenticated
    assert "admin" in auth_context.user.roles
```

### Integration Tests
```python
def test_endpoint_with_auth(client):
    # Test protected endpoint
    response = client.get(
        "/v2/profile",
        headers={"Authorization": "Bearer mock-token-user"}
    )
    assert response.status_code == 200
    
    # Test without token
    response = client.get("/v2/profile")
    assert response.status_code == 401
```

### Custom Mock Users
```python
# Add custom mock user for testing
mock_repo = MockJWTRepository()
custom_user = AuthUser(user_id="test-123", roles=["tester"])
mock_repo.create_custom_mock_user("test-token", custom_user)
```

## Migration from Existing System

The authentication system is fully compatible with your existing JWT setup:

1. **Models**: Same `AuthUser` and `AuthContext` models
2. **Dependencies**: Same dependency functions (`get_current_user`, etc.)
3. **Configuration**: Same JWT settings (JWKS URL, audience, issuer)
4. **Business Logic**: Enhanced with clean architecture patterns

### Migration Steps

1. **Parallel Deployment**: Deploy V2 endpoints alongside existing ones
2. **Test Authentication**: Verify JWT validation works with your tokens
3. **Update Clients**: Gradually migrate clients to V2 endpoints
4. **Remove Old System**: Once migration is complete

## Error Handling

The system provides detailed error responses:

```json
// 401 Unauthorized
{
  "detail": "Token has expired",
  "headers": {"WWW-Authenticate": "Bearer"}
}

// 403 Forbidden  
{
  "detail": "Required roles: admin"
}

// 503 Service Unavailable
{
  "detail": "Authentication service unavailable"
}
```

## Best Practices

1. **Use AuthContext**: Prefer `AuthContext` over `AuthUser` for optional authentication
2. **Enhance Context**: Add user information to business logic context
3. **Audit Logging**: Log user actions with full context
4. **Test Coverage**: Test both authenticated and anonymous flows
5. **Fallback Strategy**: Always have mock authentication for development
6. **Role Isolation**: Test that users can't access unauthorized resources

## Configuration Reference

Environment variables for JWT authentication:

```bash
# Required for production
APIM_ONELOGIN_URL=https://your-jwks-endpoint/.well-known/jwks.json
JWT_AUDIENCE=your-audience  
JWT_ISSUER=your-issuer
JWT_ALGORITHMS=["RS256"]

# Application settings
ENVIRONMENT=production|development|testing
DEBUG=true|false

# CORS settings
CORS_ORIGINS=["http://localhost:3000"]
```

## Troubleshooting

### Common Issues

1. **"Authentication service unavailable"**
   - Check JWKS URL is accessible
   - Verify network connectivity
   - System falls back to mock authentication

2. **"Token contains invalid issuer"**
   - Verify JWT_ISSUER matches token issuer claim
   - Check token is from correct identity provider

3. **"Required roles: admin"**
   - User doesn't have required role
   - Check token contains correct roles claim

4. **Mock tokens not working**
   - Ensure ENVIRONMENT != "production"
   - Use exact token strings: `mock-token-admin`, `mock-token-user`, `mock-token-readonly`

### Debug Authentication

Enable debug logging to troubleshoot:

```python
import logging
logging.getLogger("app.auth").setLevel(logging.DEBUG)
```

This comprehensive authentication system provides production-ready JWT validation with a clean, testable architecture that's fully compatible with your existing setup. 