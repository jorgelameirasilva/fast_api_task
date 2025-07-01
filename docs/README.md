# Architecture Documentation

This folder contains essential architectural diagrams for the FastAPI-based chat application. Each diagram illustrates key aspects of the system's architecture and data flows in a simplified, easy-to-understand format.

## 📋 Diagram Overview

### 3. Simplified Sessions Flow in /chat
**File:** `3-simplified-sessions-flow-in-chat.png`

This flowchart focuses specifically on how sessions are handled within the chat endpoint:
- **Decision Logic**: Determines whether to use existing session or create new one
- **History Management**: Loading conversation history from MongoDB for context
- **Message Persistence**: Adding user messages to the session
- **Context Preservation**: Processing chat with full conversation context
- **Response Storage**: Saving assistant responses back to the session
- **Session Context**: Returning responses with session information

**Purpose:** Shows how chat maintains conversational context through session management, ensuring continuity across multiple interactions.

### 4. Simplified /chat Flow
**File:** `4-simplified-chat-flow.png`

This high-level flowchart shows the main chat processing steps:
- **HTTP Handling**: Request reception and initial processing
- **Authentication**: JWT validation and user verification
- **Request Orchestration**: Context preparation and request coordination
- **Service Processing**: Business logic execution through chat service
- **Approach Execution**: RAG (Retrieval-Augmented Generation) processing
- **Response Formatting**: Support for both streaming and non-streaming responses
- **HTTP Response**: Final response delivery to client

**Purpose:** Provides a clear overview of the main chat processing pipeline without implementation complexity, ideal for understanding the high-level flow.

### 5. Architecture Overview
**File:** `5-architecture-overview.png`

This comprehensive system architecture diagram shows:
- **Client Layer**: Frontend application interface
- **API Layer**: FastAPI routes and authentication middleware
- **Business Logic Layer**: Orchestrators and services for chat and voting
- **Processing Layer**: Chat approaches and configuration management
- **External Services**: Azure services (AD, Search, OpenAI, Storage) and MongoDB
- **Infrastructure**: Configuration management and logging systems

**Key Components:**
- **Chat Route & Vote Route**: Main API endpoints for user interactions
- **Chat & Vote Orchestrators**: Coordinate complex business workflows
- **Chat & Vote Services**: Handle specific business logic
- **Session Service & Session Manager**: **Integral to chat flow** - manage conversation persistence and history
- **RAG Approach**: Retrieval-Augmented Generation for enhanced responses

**Critical Architecture Note:**
Sessions are **not separate from chat** - they are **integral to the chat processing flow**:
- **Chat Orchestrator** uses **Session Manager** for session coordination
- **Chat Service** uses **Session Service** for message persistence and history retrieval
- Every chat request involves session management for conversation continuity

**Architectural Patterns:**
- Layered architecture with clear separation of concerns
- Orchestrator pattern for complex workflow coordination
- Service layer for business logic encapsulation
- External service integration through dedicated clients
- Centralized configuration management

## 🏗️ Architecture Principles

### SOLID Principles
- **Single Responsibility**: Each component has a focused, well-defined purpose
- **Open/Closed**: System is extensible through interfaces and dependency injection
- **Liskov Substitution**: Services can be replaced through clean interfaces
- **Interface Segregation**: Clean API boundaries between different layers
- **Dependency Inversion**: High-level modules don't depend on low-level implementation details

### Key Design Patterns
- **Orchestrator Pattern**: Coordinates complex workflows across multiple services
- **Service Layer Pattern**: Encapsulates business logic in dedicated, testable services
- **Repository Pattern**: Abstracts data access through service interfaces
- **Dependency Injection**: Centralized configuration and service management

### Technology Stack
- **API Framework**: FastAPI with async/await support for high performance
- **Authentication**: Azure AD with JWT validation for enterprise security
- **Database**: MongoDB/CosmosDB for flexible session and vote storage
- **AI Services**: Azure OpenAI for chat completion and text embeddings
- **Search**: Azure Search for document retrieval and semantic search
- **Streaming**: NDJSON streaming responses for real-time chat experience

## 📊 Core Data Models

### Primary Entities
- **ChatRequest**: Incoming chat request with messages, session info, and options
- **ChatResponse**: Structured response with AI-generated content and metadata
- **VoteRequest**: User feedback on chat responses for quality improvement
- **Session**: Chat session with user context and conversation history
- **ChatMessage**: Individual message with role (user/assistant) and content

### External Integrations
- **Azure Search**: Document indexing and semantic search capabilities
- **Azure OpenAI**: Chat completion and text embeddings generation
- **Azure Storage**: Centralized logging and diagnostics storage
- **MongoDB/CosmosDB**: Persistent storage for sessions and user interactions

## 🔄 Key Processing Flows

### Chat Processing (with Integrated Session Management)
1. **Authentication**: JWT validation and user claim extraction
2. **Session Management**: Load existing session or create new one for conversation context
3. **Message Persistence**: Save user message to session before processing
4. **RAG Processing**: Document retrieval and context augmentation using conversation history
5. **AI Generation**: Response generation using Azure OpenAI with full conversation context
6. **Response Storage**: Save assistant response to session for future context
7. **Response Formatting**: NDJSON streaming for real-time delivery with session_id

### Vote Processing
1. **Authentication**: User verification for vote submission
2. **Validation**: Vote data validation and sanitization
3. **Processing**: Business logic execution through vote orchestrator
4. **Storage**: Persistent storage of user feedback
5. **Response**: Confirmation and feedback to user

### Session Management (Embedded in Chat Flow)
1. **Session Lookup**: Check for existing conversation by session ID
2. **History Loading**: Retrieve previous messages for conversation context
3. **Message Addition**: Add new user messages to conversation
4. **Context Maintenance**: Preserve conversation state across interactions
5. **Response Storage**: Save AI responses for future context

This architecture correctly shows that **session management is embedded within the chat processing flow**, not a separate concern. Every chat interaction involves session operations for maintaining conversation continuity and context. 