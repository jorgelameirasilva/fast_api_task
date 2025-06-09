# End-to-End Workflow Diagram: Clean Architecture V2

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        🌐 PRESENTATION LAYER                                │
│                         (FastAPI Endpoints)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      🎼 APPLICATION LAYER                                   │
│                    (Orchestration Services)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        🧠 DOMAIN LAYER                                      │
│                      (Domain Services)                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     📦 INFRASTRUCTURE LAYER                                │
│                        (Repositories)                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Complete Ask Workflow

```mermaid
graph TB
    %% Client and Entry Point
    Client[👤 Client Application]
    
    %% Presentation Layer
    subgraph "🌐 Presentation Layer"
        API["🚀 FastAPI App<br/>main_v2.py"]
        AskEndpoint["📝 POST /v2/ask<br/>chat_endpoints_v2.py"]
        HealthEndpoint["🩺 GET /v2/health"]
        DI["🔧 Dependency Injection<br/>get_ask_orchestrator()"]
    end
    
    %% Application Layer
    subgraph "🎼 Application Layer"
        AskOrch["🎭 AskOrchestrationService<br/>• Coordinate workflow<br/>• Handle errors<br/>• Format response"]
    end
    
    %% Domain Layer
    subgraph "🧠 Domain Layer"
        QueryProc["🔍 QueryProcessingService<br/>• Process user query<br/>• Enhance if needed<br/>• Execute search"]
        ResponseGen["📝 ResponseGenerationService<br/>• Generate LLM response<br/>• Manage prompts<br/>• Format output"]
    end
    
    %% Infrastructure Layer
    subgraph "📦 Infrastructure Layer"
        SearchRepo["🔎 SearchRepository<br/>Interface"]
        LLMRepo["🤖 LLMRepository<br/>Interface"]
        
        subgraph "Search Implementations"
            AzureSearch["☁️ AzureSearchRepository"]
            MockSearch["🎭 MockSearchRepository"]
        end
        
        subgraph "LLM Implementations"
            OpenAI["🤖 OpenAIRepository"]
            MockLLM["🎭 MockLLMRepository"]
        end
    end
    
    %% External Services
    subgraph "🌍 External Services"
        AzureSearchService["☁️ Azure Search"]
        OpenAIService["🤖 OpenAI API"]
    end
    
    %% Data Objects
    subgraph "📊 Data Flow"
        AskReq["📥 AskRequest<br/>• user_query<br/>• count<br/>• context"]
        SearchQuery["🔎 SearchQuery<br/>• query<br/>• top_k<br/>• filters"]
        SearchResults["📋 SearchResult[]<br/>• content<br/>• source<br/>• relevance_score"]
        LLMReq["🤖 LLMRequest<br/>• messages<br/>• temperature<br/>• model"]
        LLMResp["💬 LLMResponse<br/>• content<br/>• usage_tokens"]
        AskResp["📤 AskResponse<br/>• chatbot_response<br/>• sources<br/>• context"]
    end
    
    %% Container
    Container["🏗️ IoC Container<br/>container.py<br/>• Factory functions<br/>• Fallback logic<br/>• Health checks"]
    
    %% Flow
    Client -->|"1. HTTP POST"| AskEndpoint
    AskEndpoint -->|"2. Inject"| DI
    DI -.->|"3. Resolve"| Container
    Container -->|"4. Create"| AskOrch
    AskEndpoint -->|"5. Call"| AskOrch
    
    AskOrch -->|"6. Process Query"| QueryProc
    QueryProc -->|"7. Search"| SearchRepo
    SearchRepo -.->|"Implementation"| AzureSearch
    SearchRepo -.->|"Fallback"| MockSearch
    AzureSearch -.->|"External Call"| AzureSearchService
    
    QueryProc -->|"8. Generate"| ResponseGen
    ResponseGen -->|"9. LLM Call"| LLMRepo
    LLMRepo -.->|"Implementation"| OpenAI
    LLMRepo -.->|"Fallback"| MockLLM
    OpenAI -.->|"External Call"| OpenAIService
    
    %% Data flow
    AskEndpoint -.->|"Data"| AskReq
    QueryProc -.->|"Creates"| SearchQuery
    SearchRepo -.->|"Returns"| SearchResults
    ResponseGen -.->|"Creates"| LLMReq
    LLMRepo -.->|"Returns"| LLMResp
    AskOrch -.->|"Creates"| AskResp
    AskEndpoint -->|"10. Return"| Client
    
    %% Health check flow
    Client -->|"Health Check"| HealthEndpoint
    HealthEndpoint -->|"Check"| Container
    
    classDef presentation fill:#e1f5fe
    classDef application fill:#f3e5f5
    classDef domain fill:#e8f5e8
    classDef infrastructure fill:#fff3e0
    classDef external fill:#ffebee
    classDef data fill:#f1f8e9
    
    class API,AskEndpoint,HealthEndpoint,DI presentation
    class AskOrch application
    class QueryProc,ResponseGen domain
    class SearchRepo,LLMRepo,AzureSearch,MockSearch,OpenAI,MockLLM infrastructure
    class AzureSearchService,OpenAIService external
    class AskReq,SearchQuery,SearchResults,LLMReq,LLMResp,AskResp data
```

## 🔄 Complete Chat Workflow

```mermaid
graph TB
    %% Client and Entry Point
    Client[👤 Client Application]
    
    %% Presentation Layer
    subgraph "🌐 Presentation Layer"
        ChatEndpoint["💬 POST /v2/chat<br/>chat_endpoints_v2.py"]
        StreamEndpoint["🌊 POST /v2/chat/stream"]
        DI2["🔧 get_chat_orchestrator()"]
    end
    
    %% Application Layer
    subgraph "🎼 Application Layer"
        ChatOrch["🎭 ChatOrchestrationService<br/>• Extract latest message<br/>• Build conversation context<br/>• Coordinate workflow<br/>• Format chat response"]
    end
    
    %% Domain Layer (Same as Ask)
    subgraph "🧠 Domain Layer"
        QueryProc2["🔍 QueryProcessingService<br/>• Process with context<br/>• Conversation enhancement<br/>• Execute search"]
        ResponseGen2["📝 ResponseGenerationService<br/>• Conversation-aware prompts<br/>• History management<br/>• Contextual response"]
    end
    
    %% Data Objects for Chat
    subgraph "📊 Chat Data Flow"
        ChatReq["📥 ChatRequest<br/>• messages[]<br/>• session_state<br/>• context"]
        ChatMsg["💬 ChatMessage<br/>• role<br/>• content<br/>• timestamp"]
        ConvContext["🧵 Conversation Context<br/>• Previous messages<br/>• Session history<br/>• User intent"]
        ChatResp["📤 ChatResponse<br/>• message<br/>• session_state<br/>• context"]
    end
    
    %% Flow
    Client -->|"1. HTTP POST"| ChatEndpoint
    ChatEndpoint -->|"2. Inject"| DI2
    DI2 -->|"3. Create"| ChatOrch
    ChatEndpoint -->|"4. Call"| ChatOrch
    
    ChatOrch -->|"5. Extract & Analyze"| ConvContext
    ChatOrch -->|"6. Process with Context"| QueryProc2
    ChatOrch -->|"7. Generate with History"| ResponseGen2
    
    %% Streaming
    Client -->|"Streaming Request"| StreamEndpoint
    StreamEndpoint -->|"Server-Sent Events"| Client
    
    %% Data flow
    ChatEndpoint -.->|"Input"| ChatReq
    ChatReq -.->|"Contains"| ChatMsg
    ChatOrch -.->|"Builds"| ConvContext
    ChatOrch -.->|"Creates"| ChatResp
    ChatEndpoint -->|"8. Return"| Client
    
    classDef presentation fill:#e1f5fe
    classDef application fill:#f3e5f5
    classDef domain fill:#e8f5e8
    classDef data fill:#f1f8e9
    
    class ChatEndpoint,StreamEndpoint,DI2 presentation
    class ChatOrch application
    class QueryProc2,ResponseGen2 domain
    class ChatReq,ChatMsg,ConvContext,ChatResp data
```

## 🏗️ Dependency Injection Container Flow

```mermaid
graph LR
    subgraph "🏗️ IoC Container (container.py)"
        Config["⚙️ Configuration<br/>• Environment variables<br/>• Settings<br/>• Feature flags"]
        
        subgraph "🏭 Factory Functions"
            SearchFactory["🔍 create_search_repository()<br/>• Check Azure config<br/>• Fallback to Mock<br/>• Error handling"]
            LLMFactory["🤖 create_llm_repository()<br/>• Check OpenAI config<br/>• Fallback to Mock<br/>• Error handling"]
        end
        
        subgraph "🎯 Providers"
            SearchProvider["🔍 search_repository<br/>Singleton"]
            LLMProvider["🤖 llm_repository<br/>Singleton"]
            QueryProvider["🔎 query_processor<br/>Factory"]
            ResponseProvider["📝 response_generator<br/>Factory"]
            AskProvider["🎭 ask_orchestrator<br/>Factory"]
            ChatProvider["💬 chat_orchestrator<br/>Factory"]
        end
    end
    
    subgraph "🌍 Environment Detection"
        ProdEnv["🏢 Production<br/>• Real API keys<br/>• Azure services<br/>• Full features"]
        DevEnv["💻 Development<br/>• No API keys<br/>• Mock services<br/>• Local testing"]
        HybridEnv["🔄 Hybrid<br/>• Partial config<br/>• Mixed services<br/>• Flexible setup"]
    end
    
    Config --> SearchFactory
    Config --> LLMFactory
    
    SearchFactory -->|"Creates"| SearchProvider
    LLMFactory -->|"Creates"| LLMProvider
    
    SearchProvider -->|"Injects into"| QueryProvider
    LLMProvider -->|"Injects into"| QueryProvider
    LLMProvider -->|"Injects into"| ResponseProvider
    
    QueryProvider -->|"Injects into"| AskProvider
    ResponseProvider -->|"Injects into"| AskProvider
    QueryProvider -->|"Injects into"| ChatProvider
    ResponseProvider -->|"Injects into"| ChatProvider
    
    Config -.->|"Detects"| ProdEnv
    Config -.->|"Detects"| DevEnv
    Config -.->|"Detects"| HybridEnv
    
    classDef container fill:#fff9c4
    classDef factory fill:#e8f5e8
    classDef provider fill:#f3e5f5
    classDef env fill:#e1f5fe
    
    class Config container
    class SearchFactory,LLMFactory factory
    class SearchProvider,LLMProvider,QueryProvider,ResponseProvider,AskProvider,ChatProvider provider
    class ProdEnv,DevEnv,HybridEnv env
```

## 🔧 Component Interaction Matrix

| Component | Layer | Depends On | Provides To | Responsibility |
|-----------|-------|------------|-------------|----------------|
| **FastAPI Endpoints** | 🌐 Presentation | Orchestration Services | HTTP Clients | HTTP handling, validation |
| **AskOrchestrationService** | 🎼 Application | Domain Services | Ask Endpoint | Ask workflow coordination |
| **ChatOrchestrationService** | 🎼 Application | Domain Services | Chat Endpoint | Chat workflow coordination |
| **QueryProcessingService** | 🧠 Domain | Repositories | Orchestration Services | Query analysis & search |
| **ResponseGenerationService** | 🧠 Domain | LLM Repository | Orchestration Services | Response generation |
| **SearchRepository** | 📦 Infrastructure | External APIs | Domain Services | Search abstraction |
| **LLMRepository** | 📦 Infrastructure | External APIs | Domain Services | LLM abstraction |
| **IoC Container** | 🏗️ Core | Configuration | All Services | Dependency management |

## 🚀 Request Flow Sequence

### Ask Request Flow:
```
1. Client → POST /v2/ask
2. FastAPI → get_ask_orchestrator() [DI]
3. Container → Creates AskOrchestrationService
4. AskOrchestrationService → process_ask_request()
5. QueryProcessingService → process_user_query()
6. SearchRepository → search(query)
7. External Service → Azure Search / Mock
8. ResponseGenerationService → generate_contextual_response()
9. LLMRepository → generate_response()
10. External Service → OpenAI / Mock
11. AskOrchestrationService → Build AskResponse
12. FastAPI → Return JSON response
13. Client → Receive response
```

### Chat Request Flow:
```
1. Client → POST /v2/chat
2. FastAPI → get_chat_orchestrator() [DI]
3. Container → Creates ChatOrchestrationService
4. ChatOrchestrationService → process_chat_request()
5. Extract latest message + build conversation context
6. QueryProcessingService → process_user_query(with_context)
7. SearchRepository → search(enhanced_query)
8. ResponseGenerationService → generate_contextual_response(with_history)
9. LLMRepository → generate_response(with_conversation)
10. ChatOrchestrationService → Build ChatResponse
11. FastAPI → Return JSON response
12. Client → Receive response
```

## 🎯 Key Benefits of This Architecture

### 🧪 **Testability**
- **Easy Mocking**: Each layer can be tested independently
- **Dependency Injection**: No global state to manage
- **Clear Contracts**: Interfaces define exact behavior

### 🔧 **Maintainability**
- **Single Responsibility**: Each component has one clear purpose
- **Loose Coupling**: Components depend on abstractions, not implementations
- **Clear Boundaries**: Layers have well-defined responsibilities

### 🚀 **Production Readiness**
- **Smart Fallbacks**: Graceful degradation with mock services
- **Health Monitoring**: Built-in health checks at every layer
- **Error Handling**: Centralized error management

### 📈 **Scalability**
- **Repository Pattern**: Easy to swap implementations
- **Service Layer**: Business logic isolated from infrastructure
- **Dependency Injection**: Runtime composition of services

This architecture completely replaces the old approaches pattern with a much more robust, testable, and maintainable solution! 