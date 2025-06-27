# HR Chatbot API

A production-ready FastAPI application for HR chatbot functionality using Azure OpenAI and Azure Search with APIM (API Management) integration.

## Features

- **APIM Integration**: Production-ready Azure API Management with SecureGPT
- **OneAccount Authentication**: Custom authentication for APIM services
- **Azure Search**: ClientSecretCredential-based search integration
- **Comprehensive Testing**: Simple test setup with mocked external dependencies
- **Environment-based Configuration**: Separate settings for development, testing, and production

## Running the Application

### Development/Testing Mode

For development and testing, the app uses mock clients to avoid external dependencies:

```bash
# Set environment variables for testing
export REQUIRE_AUTHENTICATION=0
export USE_MOCK_CLIENTS=true

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

For production, the app connects to real Azure services with APIM integration:

```bash
# Set required Azure configuration
export REQUIRE_AUTHENTICATION=1
export USE_MOCK_CLIENTS=false

# APIM and SecureGPT Configuration
export APIM_BASE_URL="https://your-apim-instance.azure-api.net"
export APIM_KEY="your-apim-subscription-key"
export APIM_ONELOGIN_URL="https://your-apim-instance.azure-api.net/auth/login"
export SECURE_GPT_DEPLOYMENT_ID="your-securegpt-deployment"
export SECURE_GPT_EMB_DEPLOYMENT_ID="your-embeddings-deployment"
export SECURE_GPT_CLIENT_ID="your-securegpt-client-id"
export SECURE_GPT_CLIENT_SECRET="your-securegpt-client-secret"
export SECURE_GPT_API_VERSION="2024-02-01"

# Azure Search Configuration (with ClientSecretCredential)
export AZURE_SEARCH_SERVICE="your-search-service"
export AZURE_SEARCH_INDEX="your-search-index"
export AZURE_SEARCH_CLIENT_ID="your-search-client-id"
export AZURE_SEARCH_CLIENT_SECRET="your-search-client-secret"
export AZURE_SEARCH_TENANT_ID="your-tenant-id"

# Azure Storage Configuration
export AZURE_STORAGE_ACCOUNT="your-storage-account"
export AZURE_STORAGE_CONTAINER="your-container"
export AZURE_STORAGE_CLIENT_ID="your-storage-client-id"
export AZURE_STORAGE_CLIENT_SECRET="your-storage-client-secret"

# Authentication Configuration
export AZURE_CLIENT_APP_ID="your-client-app-id"
export AZURE_TENANT_ID="your-tenant-id"

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Authentication

### Development Mode
Set `REQUIRE_AUTHENTICATION=0` to disable authentication for testing.

### Production Mode
Set `REQUIRE_AUTHENTICATION=1` and configure Azure AD:
- Requires JWT tokens in Authorization header
- Validates tokens against Azure AD
- Uses OneAccount authentication for APIM services
- Uses ClientSecretCredential for Azure services

## Testing

Run the simple test suite:

```bash
# Run tests (automatically uses mock clients)
pytest tests/test_chat.py -v
```

The test:
- Disables authentication automatically
- Uses mocked Azure clients
- Tests the real chat pipeline end-to-end
- Validates request/response format

## API Endpoints

### POST /chat
Process a chat request with the HR chatbot.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "What are the company's vacation policies?"}
  ],
  "stream": false,
  "context": {}
}
```

**Response:**
```
data: {"message": {"role": "assistant", "content": "Our vacation policy..."}, "data_points": [...], "thoughts": "..."}
```

### GET /health
Health check endpoint.

**Response:**
```json
{"status": "healthy"}
```

## Architecture

- **FastAPI**: Modern async web framework
- **Azure API Management**: Secure gateway for OpenAI services
- **SecureGPT**: Enterprise-grade GPT deployment through APIM
- **OneAccount**: Custom authentication for APIM integration
- **Azure Search**: Document retrieval with ClientSecretCredential
- **Azure Storage**: Blob storage for documents
- **Pydantic**: Data validation and settings management

## Configuration

All configuration is handled through environment variables. See `app/core/config.py` for the complete list of available settings.

The production setup exactly matches the original implementation with:
- APIM-based OpenAI client with OneAccount authentication
- ClientSecretCredential for all Azure services
- SecureGPT deployment IDs for model selection
- Custom headers and SSL configuration

---

**Built with ❤️ using FastAPI, Azure Services, and Modern Python Practices**

## Features

- **Real Azure Integration**: Production-ready Azure OpenAI and Azure Search clients
- **Authentication**: Azure AD integration with JWT token validation
- **Comprehensive Testing**: Simple test setup with mocked external dependencies
- **Environment-based Configuration**: Separate settings for development, testing, and production

## Running the Application

### Development/Testing Mode

For development and testing, the app uses mock clients to avoid external dependencies:

```bash
# Set environment variables for testing
export REQUIRE_AUTHENTICATION=0
export USE_MOCK_CLIENTS=true

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

For production, the app connects to real Azure services:

```bash
# Set required Azure configuration
export REQUIRE_AUTHENTICATION=1
export USE_MOCK_CLIENTS=false

# Azure OpenAI Configuration
export AZURE_OPENAI_SERVICE="your-openai-service"
export AZURE_OPENAI_CHATGPT_DEPLOYMENT="gpt-4o-chatbot-poc"
export AZURE_OPENAI_CHATGPT_MODEL="gpt-4o"
export AZURE_OPENAI_EMB_DEPLOYMENT="embeddings"
export AZURE_OPENAI_EMB_MODEL_NAME="text-embedding-ada-002"

# Azure Search Configuration  
export AZURE_SEARCH_SERVICE="your-search-service"
export AZURE_SEARCH_INDEX="your-search-index"

# Authentication Configuration
export AZURE_CLIENT_APP_ID="your-client-app-id"
export AZURE_TENANT_ID="your-tenant-id"

# Optional: API Keys (if not using managed identity)
export OPENAI_API_KEY="your-openai-api-key"
export SEARCH_API_KEY="your-search-api-key"

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Authentication

### Development Mode
Set `REQUIRE_AUTHENTICATION=0` to disable authentication for testing.

### Production Mode
Set `REQUIRE_AUTHENTICATION=1` and configure Azure AD:
- Requires JWT tokens in Authorization header
- Validates tokens against Azure AD
- Supports both API keys and managed identity for Azure services

## Testing

Run the simple test suite:

```bash
# Run tests (automatically uses mock clients)
pytest tests/test_chat.py -v
```

The test:
- Disables authentication automatically
- Uses mocked Azure clients
- Tests the real chat pipeline end-to-end
- Validates request/response format

## API Endpoints

### POST /chat
Process a chat request with the HR chatbot.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "What are the company's vacation policies?"}
  ],
  "stream": false,
  "context": {}
}
```

**Response:**
```
data: {"message": {"role": "assistant", "content": "Our vacation policy..."}, "data_points": [...], "thoughts": "..."}
```

### GET /health
Health check endpoint.

**Response:**
```json
{"status": "healthy"}
```

## Architecture

- **FastAPI**: Modern async web framework
- **Azure OpenAI**: GPT-4 powered chat responses  
- **Azure Search**: Document retrieval and search
- **Pydantic**: Data validation and settings management
- **Azure Identity**: Managed identity and authentication support

## Configuration

All configuration is handled through environment variables. See `app/core/config.py` for the complete list of available settings.

graph TD
    A["Client Request<br/>POST /chat<br/>{messages, session_id}"] --> B["Chat Route<br/>api/routes/chat.py"]
    B --> C["Chat Orchestrator<br/>orchestrators/chat_orchestrator.py"]
    C --> D["Chat Service<br/>services/chat_service.py"]
    
    D --> E{"session_id<br/>provided?"}
    E -->|Yes| F["Load Session<br/>session_service.get_session()"]
    E -->|No| G["Create Session<br/>session_service.create_session()"]
    
    F --> H["Get Conversation History"]
    G --> I["Empty History"]
    
    H --> J["Add User Message<br/>session_service.add_message_to_session()"]
    I --> J
    
    J --> K["Process Chat<br/>approach.run()"]
    
    K --> L["Add Assistant Response<br/>session_service.add_message_to_session()"]
    
    L --> M["Return Response<br/>with session_id"]
    
    N["Session Service<br/>services/session_service.py"] --> O["Cosmos DB<br/>MongoDB Collection"]
    
    F -.-> N
    G -.-> N
    J -.-> N
    L -.-> N
    
    P["Database Schema<br/>{_id, user_id, created_at,<br/>updated_at, messages[]}"] --> O
    
    style A fill:#e1f5fe
    style M fill:#c8e6c9
    style O fill:#fff3e0
    style P fill:#f3e5f5