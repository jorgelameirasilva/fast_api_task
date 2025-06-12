# Clean Architecture FastAPI Implementation

This is a complete mockup implementation of Clean Architecture principles applied to a FastAPI application, replacing the problematic "approaches pattern" with a solid, maintainable, and testable architecture.

## 🏗️ Architecture Overview

This implementation follows **Clean Architecture** with **Dependency Injection**, organized into four distinct layers:

### 1. **Presentation Layer** (`app/api/`)
- FastAPI routers and endpoints
- Request/response models (DTOs)
- HTTP-specific concerns

### 2. **Application Layer** (`app/services/orchestration/`)
- Orchestration services that coordinate workflows
- Business use cases and application logic
- Cross-cutting concerns

### 3. **Domain Layer** (`app/services/domain/`)
- Core business logic
- Domain services
- Business rules and validations

### 4. **Infrastructure Layer** (`app/repositories/`)
- External service abstractions
- Repository implementations
- Data access and external API integrations

## 🔧 Key Components

### Dependency Injection Container (`app/core/container.py`)
- **Smart Fallback Strategy**: Production services with fallback to mock implementations
- **Environment Detection**: Automatically chooses appropriate implementations
- **Easy Testing**: Simple dependency replacement for unit tests

### Repository Pattern
- **SearchRepository**: Abstracts search functionality (Azure Search + Mock)
- **LLMRepository**: Abstracts LLM services (OpenAI + Mock)
- **Clean Interfaces**: Easy to add new implementations

### Service Layer
- **Domain Services**: `QueryProcessingService`, `ResponseGenerationService`
- **Orchestration Services**: `AskOrchestrationService`, `ChatOrchestrationService`
- **Clear Separation**: Each service has a single responsibility

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements_v2.txt
```

### 2. Run the Application
```bash
# Development (uses mock services)
python main_v2.py

# Production (uses real services with fallback)
ENVIRONMENT=production python main_v2.py
```

### 3. Access the API
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/v2/health
- **API Info**: http://localhost:8000/v2/info

## 📝 API Endpoints

### Ask Endpoint
```bash
POST /v2/ask
{
  "query": "What is FastAPI?",
  "context": {"user_role": "developer"},
  "max_results": 5
}
```

### Chat Endpoint
```bash
POST /v2/chat
{
  "message": "Hello, how can you help me?",
  "conversation_id": "optional-uuid",
  "history": []
}
```

### Chat History Management
```bash
GET /v2/chat/{conversation_id}/history
DELETE /v2/chat/{conversation_id}
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test category
pytest tests/test_clean_architecture.py::TestSearchRepository -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Testing Benefits Demonstrated

1. **Easy Mocking**: All dependencies are injected, making unit tests simple
2. **Isolated Testing**: Services can be tested independently
3. **Fast Tests**: Mock repositories provide instant responses
4. **Comprehensive Coverage**: Each layer can be tested thoroughly

### Example Test
```python
@pytest.mark.asyncio
async def test_ask_orchestration():
    # Easy dependency injection for testing
    mock_query_service = AsyncMock()
    mock_response_service = AsyncMock()
    
    ask_service = AskOrchestrationService(
        mock_query_service, 
        mock_response_service
    )
    
    result = await ask_service.process_ask("test query")
    
    # Easy verification of service interactions
    mock_query_service.process_query.assert_called_once()
    mock_response_service.generate_response.assert_called_once()
```

## 🔄 Migration from Approaches Pattern

### Before (Approaches Pattern Problems)
- ❌ Tight coupling with global imports
- ❌ Hard-to-test global state
- ❌ Mixed responsibilities
- ❌ Difficult to mock dependencies
- ❌ Incomplete abstractions

### After (Clean Architecture Benefits)
- ✅ Dependency injection with clear interfaces
- ✅ Easy unit testing with mock services
- ✅ Separated concerns and responsibilities
- ✅ Production-ready with smart fallbacks
- ✅ Extensible repository patterns

### Migration Steps
1. **Parallel Implementation**: Deploy V2 endpoints alongside existing ones
2. **Gradual Client Migration**: Move clients to V2 endpoints incrementally
3. **Feature Parity**: Ensure all existing functionality is available
4. **Complete Transition**: Remove old approaches pattern implementation

## 🏭 Smart Fallback Strategy

The dependency injection container implements a smart fallback strategy:

```python
def _create_search_repository(environment: str) -> SearchRepository:
    if environment == "production":
        try:
            return AzureSearchRepository()  # Try real service
        except Exception as e:
            print(f"Warning: Falling back to MockSearchRepository")
            return MockSearchRepository()  # Fallback to mock
    else:
        return MockSearchRepository()  # Development default
```

This ensures:
- **Production Resilience**: Application works even if external services fail
- **Development Ease**: Developers can work without external service setup
- **Testing Reliability**: Tests always use predictable mock services

## 📊 Health Monitoring

Comprehensive health checks at every level:

```bash
GET /v2/health
```

Response includes:
- Overall application status
- Individual service health
- Dependency status
- Environment information

## 🔧 Configuration

### Environment Variables
```bash
# Environment detection
ENVIRONMENT=development|production

# Azure Search (production)
AZURE_SEARCH_ENDPOINT=https://your-service.search.windows.net
AZURE_SEARCH_API_KEY=your-api-key
AZURE_SEARCH_INDEX=your-index

# OpenAI (production)
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4
```

### Development vs Production
- **Development**: Uses mock services by default
- **Production**: Uses real services with mock fallback

## 📁 Project Structure

```
clean_architecture_mockup/
├── app/
│   ├── __init__.py
│   ├── core/
│   │   └── container.py          # Dependency injection
│   ├── models/
│   │   └── dto.py                # Request/response models
│   ├── repositories/
│   │   ├── search_repository.py  # Search abstraction
│   │   └── llm_repository.py     # LLM abstraction
│   ├── services/
│   │   ├── domain/
│   │   │   ├── query_processing_service.py
│   │   │   └── response_generation_service.py
│   │   └── orchestration/
│   │       ├── ask_orchestration_service.py
│   │       └── chat_orchestration_service.py
│   └── api/
│       └── endpoints/
│           └── v2_endpoints.py   # FastAPI routes
├── tests/
│   └── test_clean_architecture.py
├── docs/
│   └── README.md
├── main_v2.py                    # Application entry point
└── requirements_v2.txt           # Dependencies
```

## 🌟 Key Advantages

1. **Testability**: Easy dependency injection and mocking
2. **Maintainability**: Clear separation of concerns
3. **Extensibility**: New implementations through repository pattern
4. **Production Ready**: Smart fallback strategy and comprehensive monitoring
5. **Developer Experience**: Works out-of-the-box with mock services

## 🔮 Future Enhancements

This architecture easily supports adding:

- **Persistent Storage**: Database repositories for conversation history
- **Caching Layer**: Redis repositories for performance optimization
- **Event Sourcing**: Event repositories for audit trails
- **Multiple LLM Providers**: Additional LLM repository implementations
- **Advanced Search**: Vector database repositories

## 📚 Further Reading

- [Clean Architecture Principles](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Dependency Injection in Python](https://python-dependency-injector.ets-labs.org/)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)

---

This implementation demonstrates how Clean Architecture principles can transform a tightly coupled, hard-to-test codebase into a maintainable, extensible, and production-ready application. 