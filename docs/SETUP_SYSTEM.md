# Setup System Documentation

## Overview

The FastAPI chat application now includes a comprehensive setup system that initializes Azure services, OpenAI clients, and approach configurations during application startup. This follows FastAPI best practices for dependency injection and application lifecycle management.

## Features

- **Azure Service Integration**: Automatic setup of Azure Search, Storage, and OpenAI services
- **Dependency Injection**: Pre-configured clients are injected into approach instances
- **Graceful Fallbacks**: Mock clients when services are unavailable or not configured
- **Environment-based Configuration**: All settings configurable via environment variables
- **Dual Authentication Support**: Azure AD and standard authentication modes
- **Approach Pre-configuration**: Approaches are initialized with proper clients during startup

## Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```bash
# Application settings
DEBUG=0
ENVIRONMENT=development

# Azure Storage
AZURE_STORAGE_ACCOUNT=your_storage_account_name
AZURE_STORAGE_CONTAINER=your_container_name
STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...

# Azure Search
AZURE_SEARCH_SERVICE=your_search_service_name
AZURE_SEARCH_INDEX=your_search_index_name
SEARCH_API_KEY=your_search_api_key
AZURE_SEARCH_QUERY_LANGUAGE=en-us
AZURE_SEARCH_QUERY_SPELLER=lexicon

# Knowledge Base Fields
KB_FIELDS_CONTENT=content
KB_FIELDS_SOURCEPAGE=sourcepage

# OpenAI Configuration
OPENAI_HOST=azure  # or "openai" for standard OpenAI

# Azure OpenAI (when OPENAI_HOST=azure)
AZURE_OPENAI_SERVICE=your_openai_service_name
AZURE_OPENAI_CHATGPT_MODEL=gpt-4o
AZURE_OPENAI_CHATGPT_DEPLOYMENT=your_gpt_deployment_name
AZURE_OPENAI_EMB_MODEL=text-embedding-ada-002
AZURE_OPENAI_EMB_DEPLOYMENT=your_embedding_deployment_name

# Standard OpenAI (when OPENAI_HOST!=azure)
OPENAI_API_KEY=your_openai_api_key
OPENAI_ORGANIZATION=your_openai_organization_id

# Authentication
AZURE_USE_AUTHENTICATION=false
AZURE_SERVER_APP_ID=your_server_app_id
AZURE_SERVER_APP_SECRET=your_server_app_secret
AZURE_CLIENT_APP_ID=your_client_app_id
AZURE_TENANT_ID=your_tenant_id
TOKEN_CACHE_PATH=.token_cache
```

## Architecture

### Setup Flow

1. **Application Startup**: FastAPI calls `setup_clients()` during startup event
2. **Client Initialization**: Azure Search, Storage, and OpenAI clients are created
3. **Authentication Setup**: Azure AD authentication helper is configured
4. **Approach Configuration**: Approach instances are created with injected clients
5. **Registry Update**: Pre-configured approaches are registered globally

### Components

#### 1. Setup Module (`app/core/setup.py`)
- **`setup_clients()`**: Main setup function called during startup
- **`cleanup_clients()`**: Cleanup function called during shutdown
- **Client factories**: Individual setup functions for each service
- **Dependency injection functions**: `get_search_client()`, `get_openai_client()`, etc.

#### 2. Configuration (`app/core/config.py`)
- **Settings class**: Pydantic-based configuration with environment variable binding
- **URL construction**: Dynamic endpoint URL generation
- **Validation**: Automatic configuration validation

#### 3. Approach Registry (`app/approaches/approach_registry.py`)
- **Dual Registration**: Supports both class-based and instance-based approaches
- **Priority System**: Pre-configured instances take priority over class-based ones
- **Automatic Aliases**: Registers multiple names for the same approach

#### 4. Authentication (`app/core/auth.py`)
- **Azure AD Integration**: Basic authentication helper for Azure AD
- **Extensible Design**: Can be enhanced with full OAuth/OIDC support

## Usage

### Development Mode

For development, the system automatically uses mock clients when Azure services aren't configured:

```bash
# Run without any Azure configuration
python -m uvicorn app.main:app --reload
```

The application will start with mock clients and log warnings about missing configuration.

### Production Mode

For production, configure all required environment variables:

```bash
# Set environment variables
export AZURE_SEARCH_SERVICE=your-search-service
export AZURE_OPENAI_SERVICE=your-openai-service
# ... other variables

# Run the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Dependency Injection

Access configured clients in your code:

```python
from app.core.setup import get_search_client, get_openai_client

# Get the configured clients
search_client = get_search_client()
openai_client = get_openai_client()
```

### Approach Usage

The setup system automatically configures approaches with the proper clients:

```python
from app.approaches import get_approach, get_best_approach

# Get a specific approach (pre-configured with clients)
approach = get_approach("retrieve_then_read")

# Get the best approach for a query (auto-selection)
approach = get_best_approach("What is AI?", message_count=1)
```

## Mock Clients

When Azure services are not available, the setup system provides mock clients:

- **MockSearchClient**: Returns empty search results
- **MockBlobClient**: Returns empty blob listings  
- **MockOpenAIClient**: Returns placeholder responses

This allows development and testing without requiring Azure services.

## Error Handling

The setup system includes comprehensive error handling:

- **Graceful Degradation**: Falls back to mock clients on errors
- **Detailed Logging**: Logs configuration status and errors
- **Non-blocking Startup**: Application starts even if some services fail

## Extending the System

### Adding New Clients

1. Create a setup function in `app/core/setup.py`:
```python
async def _setup_your_service():
    # Client setup logic
    return your_client
```

2. Add configuration in `app/core/config.py`:
```python
YOUR_SERVICE_ENDPOINT: str = os.getenv("YOUR_SERVICE_ENDPOINT", "")
```

3. Register in `setup_clients()`:
```python
your_client = await _setup_your_service()
current_app_config["your_service"] = your_client
```

### Adding New Approaches

1. Create your approach class inheriting from `BaseApproach`
2. Add client parameters to the constructor
3. Register in `_setup_approaches()`:
```python
your_approach = YourApproach(
    search_client=_search_client,
    openai_client=_openai_client,
    # ... other parameters
)
register_approach_instance("your_approach", your_approach)
```

## Best Practices

1. **Environment Variables**: Use environment variables for all configuration
2. **Graceful Fallbacks**: Always provide mock/fallback implementations
3. **Dependency Injection**: Use the setup system's dependency injection
4. **Error Handling**: Handle client initialization errors gracefully
5. **Resource Cleanup**: Implement proper cleanup in shutdown handlers

## Troubleshooting

### Common Issues

1. **Missing Azure SDKs**: Install required packages:
   ```bash
   pip install azure-search-documents azure-storage-blob azure-identity openai
   ```

2. **Configuration Errors**: Check environment variables and Azure service endpoints

3. **Authentication Issues**: Verify Azure AD configuration and managed identity setup

4. **Startup Failures**: Check logs for specific error messages and ensure all required services are available

### Debugging

Enable debug logging to see detailed setup information:

```python
import logging
logging.getLogger("app.core.setup").setLevel(logging.DEBUG)
```

This will show client creation, registration, and configuration details. 