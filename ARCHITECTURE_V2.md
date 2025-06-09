# Architecture V2: Clean Architecture with DDD

## Why Replace the Approaches Pattern?

### Problems with Current Approaches Pattern

1. **Tight Coupling**: Services directly import global setup functions
   ```python
   # 🚫 BEFORE: Tight coupling
   from app.core.setup import get_ask_approach
   ask_approach = get_ask_approach()
   ```

2. **Global State Management**: Configuration stored in global dictionaries
   ```python
   # 🚫 BEFORE: Global state
   current_app_config = {}  # Global variable
   ```

3. **Mixed Responsibilities**: Single classes handling multiple concerns
   ```python
   # 🚫 BEFORE: Mixed responsibilities
   class AskService:
       async def _process_with_approaches(self):  # Business logic
       async def _process_simple(self):           # Fallback logic
   ```

4. **Incomplete Abstractions**: Approaches have placeholder implementations
   ```python
   # 🚫 BEFORE: Placeholder code
   async def _search_documents(self): 
       return ["Document 1: Information about {query}"]  # Not real
   ```

5. **Testing Difficulties**: Hard to mock dependencies and test in isolation

## New Architecture: Clean Architecture + DDD

### 1. Repository Pattern (Infrastructure Layer)

**Abstracts external dependencies with clean interfaces:**

```python
# ✅ AFTER: Clean abstraction
class SearchRepository(ABC):
    @abstractmethod
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        pass

class AzureSearchRepository(SearchRepository):
    # Real implementation
    
class MockSearchRepository(SearchRepository):
    # Test implementation
```

### 2. Dependency Injection Container

**Manages dependencies without global state:**

```python
# ✅ AFTER: Proper IoC container
class Container(containers.DeclarativeContainer):
    search_client = providers.Factory(AzureSearchRepository, ...)
    llm_client = providers.Factory(OpenAIRepository, ...)
    
    ask_orchestrator = providers.Factory(
        AskOrchestrationService,
        query_processor=query_processor,
        response_generator=response_generator,
    )
```

### 3. Service Layer (Domain Layer)

**Single Responsibility Principle:**

```python
# ✅ AFTER: Single responsibility
class QueryProcessingService:
    """Only handles query processing and search"""
    
class ResponseGenerationService:
    """Only handles LLM response generation"""
    
class AskOrchestrationService:
    """Only orchestrates the ask workflow"""
```

### 4. Clean API Layer

**FastAPI endpoints with proper dependency injection:**

```python
# ✅ AFTER: Clean API with DI
@router.post("/ask")
async def ask_question(
    request: AskRequest,
    orchestrator: AskOrchestrationService = Depends(get_ask_orchestrator)
) -> AskResponse:
    return await orchestrator.process_ask_request(request)
```

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐  │
│  │  FastAPI        │ │  WebSocket      │ │  Streaming    │  │
│  │  Routers        │ │  Handlers       │ │  Responses    │  │
│  └─────────────────┘ └─────────────────┘ └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
│  ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐  │
│  │  Ask            │ │  Chat           │ │  Session      │  │
│  │  Orchestration  │ │  Orchestration  │ │  Management   │  │
│  │  Service        │ │  Service        │ │  Service      │  │
│  └─────────────────┘ └─────────────────┘ └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     Domain Layer                            │
│  ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐  │
│  │  Query          │ │  Response       │ │  Domain       │  │
│  │  Processing     │ │  Generation     │ │  Models       │  │
│  │  Service        │ │  Service        │ │  & Logic      │  │
│  └─────────────────┘ └─────────────────┘ └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                       │
│  ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐  │
│  │  Search         │ │  LLM            │ │  Storage      │  │
│  │  Repository     │ │  Repository     │ │  Repository   │  │
│  │  (Azure/Mock)   │ │  (OpenAI/Mock)  │ │  (Blob/Mock)  │  │
│  └─────────────────┘ └─────────────────┘ └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Benefits Over Approaches Pattern

| Aspect | Approaches Pattern | Clean Architecture |
|--------|-------------------|-------------------|
| **Testability** | Hard to mock global dependencies | Easy dependency injection mocking |
| **Maintainability** | Mixed responsibilities | Clear separation of concerns |
| **Extensibility** | Registry pattern, but tightly coupled | Repository pattern, loosely coupled |
| **Production Ready** | Global state, error prone | Proper error handling, no global state |
| **Performance** | Import-time initialization | Lazy loading, optimized |
| **Development** | Mock clients as fallbacks | Proper mock implementations |

## Migration Strategy

### Phase 1: Parallel Implementation
- Keep existing approaches for compatibility
- Add new V2 endpoints (`/v2/ask`, `/v2/chat`)
- Gradually migrate clients to V2

### Phase 2: Full Migration
- Update all endpoints to use new architecture
- Remove approaches pattern
- Clean up global setup code

## Example Usage

### Testing with Dependency Injection
```python
# Easy to test with mocks
async def test_ask_orchestration():
    mock_search = MockSearchRepository()
    mock_llm = MockLLMRepository()
    
    query_processor = QueryProcessingService(mock_search, mock_llm)
    response_generator = ResponseGenerationService(mock_llm)
    orchestrator = AskOrchestrationService(query_processor, response_generator)
    
    response = await orchestrator.process_ask_request(request)
    assert response.chatbot_response == "Expected response"
```

### Production Configuration
```python
# Easy to configure for production
container.config.from_dict({
    "AZURE_SEARCH_SERVICE": "prod-search",
    "OPENAI_API_KEY": "prod-key",
    # ... other config
})
```

## Key Design Patterns Used

1. **Repository Pattern**: Abstraction over data access
2. **Dependency Injection**: Inversion of Control
3. **Service Layer**: Business logic separation
4. **Factory Pattern**: Object creation
5. **Strategy Pattern**: Algorithm selection (but properly implemented)
6. **Domain Driven Design**: Rich domain models

This architecture is production-ready, testable, maintainable, and follows FastAPI best practices while being highly extensible for future requirements. 