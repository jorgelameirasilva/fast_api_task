# Migration Guide: From Approaches Pattern to Clean Architecture V2

## Overview

This guide explains how to migrate from the old **Approaches Pattern** to the new **Clean Architecture with Dependency Injection**. The new architecture is more maintainable, testable, and production-ready.

## Quick Start (New Installation)

If you're starting fresh, simply use the new V2 implementation:

```bash
# 1. Install dependencies
pip install -r requirements_v2.txt

# 2. Set environment variables (optional - has smart defaults)
export OPENAI_API_KEY="your-api-key"
export AZURE_SEARCH_SERVICE="your-search-service"
export SEARCH_API_KEY="your-search-key"

# 3. Start the application
python run_v2.py
```

The application will automatically:
- ✅ Use real services if configured
- ⚠️ Fall back to mock implementations for development
- 🚀 Start with clean architecture benefits immediately

## Migration Steps for Existing Projects

### Phase 1: Parallel Implementation (Recommended)

Run both old and new systems side by side:

```bash
# Start V2 alongside existing system
python run_v2.py  # Runs on port 8000 with /v2/* endpoints
```

**Benefits:**
- ✅ No downtime
- ✅ Gradual migration
- ✅ Easy rollback

### Phase 2: Client Migration

Update your clients to use V2 endpoints:

```python
# OLD endpoints
POST /ask      → POST /v2/ask
POST /chat     → POST /v2/chat
GET  /health   → GET  /v2/health

# NEW endpoints (additional)
POST /v2/ask/stream      # Streaming ask
POST /v2/chat/stream     # Streaming chat  
GET  /v2/architecture/info  # Architecture details
GET  /v2/metrics         # Application metrics
```

### Phase 3: Complete Migration

Once all clients use V2, deprecate old endpoints.

## File Structure Comparison

### Old Structure (Approaches Pattern)
```
app/
├── approaches/
│   ├── base.py                 # Abstract approach
│   ├── retrieve_then_read.py   # Ask approach
│   ├── chat_read_retrieve_read.py  # Chat approach
│   └── approach_registry.py   # Registry pattern
├── core/
│   └── setup.py               # Global setup with config dict
├── services/
│   ├── ask_service.py         # Mixed responsibilities
│   └── chat_service.py        # Mixed responsibilities
└── api/endpoints/
    └── chat_endpoints.py      # Direct approach usage
```

### New Structure (Clean Architecture)
```
app/
├── repositories/              # 📦 Infrastructure Layer
│   ├── search_repository.py   # Search abstraction
│   └── llm_repository.py      # LLM abstraction
├── services/                  # 🧠 Domain + 🎼 Application Layers
│   ├── query_processing_service.py     # Domain service
│   ├── response_generation_service.py  # Domain service
│   ├── ask_orchestration_service.py    # Application service
│   └── chat_orchestration_service.py   # Application service
├── core/
│   └── container.py           # Dependency injection
├── api/endpoints/
│   └── chat_endpoints_v2.py   # Clean DI usage
├── main_v2.py                 # New main app
└── tests/
    └── test_clean_architecture_v2.py  # Comprehensive tests
```

## Code Migration Examples

### 1. Replace Direct Approach Usage

**OLD (Approaches Pattern):**
```python
# ❌ Tight coupling to global setup
from app.core.setup import get_ask_approach

class AskService:
    async def process_ask(self, request):
        ask_approach = get_ask_approach()  # Global dependency
        result = await ask_approach.run_without_streaming(...)
        # Mixed responsibilities: parsing, error handling, formatting
```

**NEW (Clean Architecture):**
```python
# ✅ Clean dependency injection
class AskOrchestrationService:
    def __init__(
        self, 
        query_processor: QueryProcessingService,    # Injected
        response_generator: ResponseGenerationService  # Injected
    ):
        self.query_processor = query_processor
        self.response_generator = response_generator
    
    async def process_ask_request(self, request: AskRequest) -> AskResponse:
        # Single responsibility: orchestration only
        processed_query = await self.query_processor.process_user_query(...)
        search_results = await self.query_processor.search_documents(...)
        response = await self.response_generator.generate_contextual_response(...)
        return AskResponse(...)
```

### 2. Replace Global Configuration

**OLD (Global State):**
```python
# ❌ Global configuration dictionary
current_app_config = {}
current_app_config[CONFIG_SEARCH_CLIENT] = search_client

def get_ask_approach():
    return current_app_config.get(CONFIG_ASK_APPROACH)
```

**NEW (Dependency Injection):**
```python
# ✅ Proper IoC container
class Container(containers.DeclarativeContainer):
    search_repository = providers.Singleton(create_search_repository)
    llm_repository = providers.Singleton(create_llm_repository)
    
    ask_orchestrator = providers.Factory(
        AskOrchestrationService,
        query_processor=query_processor,
        response_generator=response_generator,
    )

# FastAPI dependency
async def get_ask_orchestrator() -> AskOrchestrationService:
    return container.ask_orchestrator()
```

### 3. Replace Mock Fallbacks

**OLD (Mock as Last Resort):**
```python
# ❌ Mock clients only when everything fails
try:
    _search_client = setup_real_client()
except:
    _search_client = MockSearchClient()  # Fallback
```

**NEW (Proper Fallback Strategy):**
```python
# ✅ Smart factory with graceful fallbacks
def create_search_repository() -> SearchRepository:
    try:
        if all([settings.AZURE_SEARCH_SERVICE, settings.SEARCH_API_KEY]):
            return AzureSearchRepository(...)  # Production
        else:
            logger.warning("Azure Search not configured, using mock")
            return MockSearchRepository()      # Development
    except Exception:
        logger.error("Azure Search failed, falling back to mock")
        return MockSearchRepository()          # Error recovery
```

## Testing Migration

### Old Testing (Difficult)
```python
# ❌ Hard to test - global dependencies
def test_ask_service():
    # Can't easily mock global setup
    # Need to patch global state
    # Tightly coupled to approaches
```

### New Testing (Easy)
```python
# ✅ Easy to test - inject mocks
async def test_ask_orchestration():
    mock_search = MockSearchRepository()
    mock_llm = MockLLMRepository(["Test response"])
    
    query_processor = QueryProcessingService(mock_search, mock_llm)
    response_generator = ResponseGenerationService(mock_llm)
    orchestrator = AskOrchestrationService(query_processor, response_generator)
    
    request = AskRequest(user_query="Test question")
    response = await orchestrator.process_ask_request(request)
    
    assert response.chatbot_response == "Test response"
```

## Environment Configuration

The new architecture supports flexible environment configuration:

```bash
# Production with real services
export OPENAI_API_KEY="sk-..."
export AZURE_SEARCH_SERVICE="your-search-service"
export SEARCH_API_KEY="your-search-key"
export AZURE_SEARCH_INDEX="your-index"

# Development with mocks (no config needed)
# Will automatically use mock implementations

# Hybrid (real LLM, mock search)
export OPENAI_API_KEY="sk-..."
# No search config = uses mock search
```

## Deployment Options

### Option 1: Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements_v2.txt .
RUN pip install -r requirements_v2.txt

COPY . .
EXPOSE 8000

CMD ["python", "run_v2.py"]
```

### Option 2: Traditional Deployment
```bash
# Install dependencies
pip install -r requirements_v2.txt

# Set production environment variables
export ENVIRONMENT=production
export OPENAI_API_KEY=$PROD_OPENAI_KEY
export AZURE_SEARCH_SERVICE=$PROD_SEARCH_SERVICE

# Start with gunicorn for production
gunicorn app.main_v2:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Option 3: Development
```bash
# Simple development start
python run_v2.py

# Or with uvicorn directly
uvicorn app.main_v2:app --reload
```

## Benefits After Migration

| Aspect | Before (Approaches) | After (Clean Architecture) |
|--------|-------------------|---------------------------|
| **Testing** | Hard to mock global deps | Easy dependency injection |
| **Configuration** | Global state dictionary | Proper IoC container |
| **Error Handling** | Mixed in with business logic | Centralized and clean |
| **Extensibility** | Registry pattern coupling | Repository pattern abstraction |
| **Production Ready** | Mock fallbacks only | Smart fallback strategy |
| **Performance** | Import-time initialization | Lazy loading with singletons |
| **Maintainability** | Mixed responsibilities | Clear separation of concerns |

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Solution: Install new dependencies
   pip install -r requirements_v2.txt
   ```

2. **Service Not Starting**
   ```bash
   # Solution: Check startup script output
   python run_v2.py
   # Will show detailed health check information
   ```

3. **Mock Services in Production**
   ```bash
   # Solution: Check environment variables
   export OPENAI_API_KEY="your-key"
   export AZURE_SEARCH_SERVICE="your-service"
   ```

4. **Dependency Injection Errors**
   ```python
   # Solution: Check container initialization
   from app.core.container import initialize_container
   initialize_container()
   ```

### Health Checks

The new architecture includes comprehensive health monitoring:

```bash
# Check overall health
curl http://localhost:8000/v2/health

# Check architecture info
curl http://localhost:8000/v2/architecture/info

# Check metrics
curl http://localhost:8000/v2/metrics
```

## Rollback Plan

If you need to rollback:

1. **Keep old code**: Don't delete the old approaches until V2 is stable
2. **Switch endpoints**: Change clients back to old endpoints
3. **Environment isolation**: Use different ports/domains for V1 vs V2

## Support

For issues with migration:

1. Check the comprehensive tests in `tests/test_clean_architecture_v2.py`
2. Review the architectural documentation in `ARCHITECTURE_V2.md`
3. Use the health check endpoints to diagnose issues
4. Start with mock implementations and gradually add real services

The new clean architecture provides a solid foundation for long-term maintenance and growth! 