# Approach Integration Documentation

## Overview

The API has been updated to use **approaches as the primary processing method**, matching the original legacy code structure. Approaches are now the main way the system processes chat and ask requests, with simple responses only as fallbacks.

## Architecture

### Core Components

1. **Approach Classes** (`app/approaches/`)
   - `ChatReadRetrieveReadApproach` - For chat conversations
   - `RetrieveThenReadApproach` - For ask queries
   - `Approach` (base class) - Abstract base with required methods

2. **Approach Registry** (`app/approaches/approach_registry.py`)
   - Manages approach registration and retrieval
   - Provides dependency injection for approaches

3. **Service Layer** (`app/services/`)
   - `ChatService` - Uses ChatReadRetrieveReadApproach as primary
   - `AskService` - Uses RetrieveThenReadApproach as primary

4. **Configuration Setup** (`app/core/setup.py`)
   - Initializes approaches with Azure clients during startup
   - Ensures approaches are always available (even with mock clients)

## API Workflow

### Chat Endpoint (`POST /chat`)
1. **Primary**: Use `ChatReadRetrieveReadApproach`
   - Analyzes conversation context
   - Retrieves relevant documents
   - Generates contextual responses
2. **Fallback**: Simple response generation (only if approaches fail)

### Ask Endpoint (`POST /ask`) 
1. **Primary**: Use `RetrieveThenReadApproach`
   - Retrieves documents based on query
   - Generates response using retrieved context
   - Returns sources and data points
2. **Fallback**: Simple response generation (only if approaches fail)

## Configuration

### Approach Setup Process

1. **Client Initialization** (startup)
   ```python
   # Azure clients are set up first
   _search_client = await _setup_search_client()
   _openai_client = await _setup_openai_client()
   ```

2. **Approach Configuration**
   ```python
   # Approaches are configured with actual clients
   ask_approach = RetrieveThenReadApproach(
       search_client=_search_client,
       openai_client=_openai_client,
       chatgpt_model=settings.OPENAI_CHATGPT_MODEL,
       # ... other configuration parameters
   )
   ```

3. **Dependency Injection**
   ```python
   # Approaches are available via dependency injection
   current_app_config[CONFIG_ASK_APPROACH] = ask_approach
   current_app_config[CONFIG_CHAT_APPROACH] = chat_approach
   ```

### Environment Variables

The approaches use the following configuration from settings:

- `OPENAI_CHATGPT_MODEL` - GPT model for responses
- `AZURE_OPENAI_CHATGPT_DEPLOYMENT` - Azure deployment name
- `OPENAI_EMB_MODEL` - Embedding model
- `AZURE_OPENAI_EMB_DEPLOYMENT` - Embedding deployment
- `KB_FIELDS_SOURCEPAGE` - Source page field in search
- `KB_FIELDS_CONTENT` - Content field in search
- `AZURE_SEARCH_QUERY_LANGUAGE` - Search query language
- `AZURE_SEARCH_QUERY_SPELLER` - Search speller configuration

## Response Format

### Chat Response
```json
{
  "message": {
    "role": "assistant",
    "content": "Based on conversation context and retrieved documents...",
    "timestamp": "2025-06-03T17:17:41.508895"
  },
  "session_state": null,
  "context": {
    "approach_used": "chat_read_retrieve_read",
    "approach_type": "ChatReadRetrieveReadApproach",
    "streaming": false,
    "session_updated": false,
    "chat_processed_at": "2025-06-03T17:17:41.508900",
    "data_points": ["Conversation context...", "Retrieved documents..."],
    "thoughts": "Conversation: ... Answer: ...",
    "followup_questions": ["<<Question 1?>>", "<<Question 2?>>"]
  }
}
```

### Ask Response
```json
{
  "user_query": "What is the deductible?",
  "chatbot_response": "Based on retrieved documents...",
  "context": {
    "approach_used": "retrieve_then_read",
    "approach_type": "RetrieveThenReadApproach",
    "streaming": false,
    "query_processed_at": "2025-06-03T17:17:49.308731",
    "data_points": ["Document 1: Information...", "Document 2: Context..."],
    "thoughts": "Question: ... Answer: ..."
  },
  "sources": [
    {
      "title": "Retrieved Document 1",
      "url": "/content/doc1.pdf",
      "relevance_score": 0.9,
      "excerpt": "Document excerpt..."
    }
  ],
  "count": 0
}
```

## Error Handling

1. **Approach Failure**: If approaches fail, services fall back to simple responses
2. **Startup Failure**: If approaches cannot be initialized, the application will not start
3. **Mock Clients**: If Azure clients are unavailable, mock clients are used but approaches still function

## Integration Points

### Service Layer Changes
- Removed `use_approaches` parameter (approaches are now always primary)
- Updated methods to call `run_with_streaming()` or `run_without_streaming()`
- Enhanced error handling and logging

### API Layer Changes
- Added validation for requests
- Enhanced logging of approach usage
- Improved error responses

### Testing
- All integration tests pass (18 tests total)
- Tests validate that approaches are used as primary processing method
- Tests verify approach-specific response structures and metadata
- Tests confirm rich context data (data_points, thoughts, followup_questions) 
- Fallback mechanisms are verified but approaches are expected to work
- Streaming functionality is implemented (currently uses same logic as non-streaming)

## Benefits

1. **Consistency**: Matches original legacy code structure
2. **Reliability**: Approaches are always available with proper fallbacks
3. **Flexibility**: Easy to swap approach implementations
4. **Observability**: Clear logging of which approach is used
5. **Extensibility**: New approaches can be easily added via the registry

## Next Steps

You can now replace the placeholder approach implementations with your legacy approach code:

1. Update `app/approaches/chat_read_retrieve_read.py` with your legacy ChatReadRetrieveReadApproach
2. Update `app/approaches/retrieve_then_read.py` with your legacy RetrieveThenReadApproach
3. The existing infrastructure will automatically use your implementations

The approach system is now fully integrated and ready for your legacy code integration! 