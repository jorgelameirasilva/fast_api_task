# HR Chatbot API - FastAPI Migration

A production-ready FastAPI application that migrates the original Quart-based HR Chatbot with enhanced architecture, authentication, and mock clients for development.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                           │
│  ┌─────────────────┐              ┌─────────────────────┐  │
│  │ Static endpoint │              │ Chat Endpoints      │  │
│  │      (/)        │              │   (/chat)           │  │
│  └─────────────────┘              │   (/vote)           │  │
│                                   └─────────────────────┘  │
└─────────────────────┬───────────────────────────────────────┘
                      │
            ┌─────────▼──────────┐
            │   Auth Gateway     │
            │  (Bearer Token)    │
            └─────────┬──────────┘
                      │
            ┌─────────▼──────────┐
            │   Service Layer    │
            │  ┌──────────────┐  │
            │  │ Chat Service │  │  ┌──────────────┐
            │  └──────────────┘  │  │ Vote Service │
            │                    │  └──────────────┘
            └─────────┬──────────┘
                      │
            ┌─────────▼──────────┐
            │ Approaches Layer   │
            │ ┌─────────────────┐│
            │ │Chat Read-Retrieve│││ ┌─────────────────┐
            │ │Read Approach    │││ │Retrieve then read│
            │ └─────────────────┘││ └─────────────────┘
            └────────────────────┘
```

## 🚀 Features

### Core Features
- **FastAPI Framework**: Modern, high-performance async web framework
- **Bearer Token Authentication**: Azure AD integration with JWT validation
- **Mock Clients**: Development-friendly mock implementations for Azure services
- **SOLID Architecture**: Clean separation of concerns with dependency injection
- **Production Ready**: Health checks, proper logging, error handling

### API Endpoints
- `POST /chat` - Chat with AI assistant using RAG approach
- `POST /vote` - Submit feedback votes with validation
- `GET /auth_setup` - Authentication configuration for frontend
- `GET /health` - Health check endpoint
- `GET /` - API information and available endpoints

### Mock Clients
- **MockOpenAIClient**: Realistic chat completions and embeddings
- **MockSearchClient**: Azure Search simulation with sample HR documents
- **MockBlobContainerClient**: Azure Blob Storage simulation

## 📋 Prerequisites

- Python 3.9+
- pip or poetry
- Access to Azure services (for production) or use mock clients

## ⚡ Quick Start

### 1. Clone and Setup
```bash
cd new_repo
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Run Development Server
```bash
# Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python
python -m app.main
```

### 4. Access the API
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_MOCK_CLIENTS` | Use mock clients instead of real Azure services | `true` |
| `DEBUG` | Enable debug mode | `false` |
| `AZURE_USE_AUTHENTICATION` | Enable Azure AD authentication | `true` |
| `AZURE_CLIENT_APP_ID` | Azure AD client application ID | - |
| `AZURE_TENANT_ID` | Azure AD tenant ID | - |
| `SECURE_GPT_DEPLOYMENT_ID` | Azure OpenAI deployment ID | - |
| `APIM_KEY` | API Management subscription key | - |

See `.env.example` for complete configuration options.

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_chat.py

# Run with verbose output
pytest -v
```

### Test Coverage
The test suite covers:
- ✅ Chat endpoint functionality
- ✅ Vote endpoint with validation
- ✅ Authentication flows
- ✅ Error handling
- ✅ Mock client behavior

## 🏭 Production Deployment

### Using Gunicorn
```bash
gunicorn -c gunicorn.conf.py app.main:app
```

### Using Docker
```bash
docker build -t hr-chatbot-api .
docker run -p 8000:8000 hr-chatbot-api
```

### Environment Setup for Production
1. Set `USE_MOCK_CLIENTS=false`
2. Configure all Azure service credentials
3. Set appropriate logging levels
4. Configure CORS for your domain

## 📊 API Usage Examples

### Chat Request
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "How do I report an illness?"}
    ],
    "stream": false
  }'
```

### Vote Request
```bash
curl -X POST "http://localhost:8000/vote" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "How do I report an illness?",
    "chatbot_response": "Follow these steps...",
    "upvote": 1,
    "downvote": 0,
    "count": 1
  }'
```

### Health Check
```bash
curl "http://localhost:8000/health"
```

## 🔍 Monitoring & Observability

### Logging
- Structured JSON logging for production
- Request correlation IDs
- Performance metrics
- Error tracking with stack traces

### Health Checks
- `/health` endpoint for container orchestration
- Dependency health validation
- Graceful shutdown handling

### Metrics
- Request/response metrics
- Authentication success/failure rates
- Mock vs real client usage tracking

## 🛡️ Security

### Authentication
- Bearer token validation using Azure AD
- JWT claim extraction and validation
- Request-level authentication enforcement

### Input Validation
- Comprehensive Pydantic model validation
- SQL injection prevention
- XSS protection through proper encoding

### Error Handling
- Consistent error response format
- No sensitive information in error messages
- Proper HTTP status codes

## 🔄 Migration from Original Quart App

### Key Changes
- **Framework**: Quart → FastAPI
- **Architecture**: Monolithic → Layered (API/Service/Approaches)
- **Validation**: Manual → Pydantic models
- **Testing**: Limited → Comprehensive test suite
- **Documentation**: None → Auto-generated OpenAPI docs

### Preserved Functionality
- ✅ Exact same `/chat` and `/vote` endpoints
- ✅ Same authentication mechanism
- ✅ Identical approaches (copied as-is)
- ✅ Same response formats
- ✅ Compatible with existing frontend

## 🚨 Troubleshooting

### Common Issues

**Mock clients not working?**
- Ensure `USE_MOCK_CLIENTS=true` in your environment
- Check that approaches can import mock clients

**Authentication failing?**
- Verify `AZURE_USE_AUTHENTICATION` setting
- Check Bearer token format
- Validate Azure AD configuration

**Tests failing?**
- Ensure test environment has `USE_MOCK_CLIENTS=true`
- Check that all dependencies are installed
- Verify test database is accessible

### Debug Mode
Enable debug mode for detailed logging:
```bash
export DEBUG=true
export USE_MOCK_CLIENTS=true
uvicorn app.main:app --reload --log-level debug
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built with ❤️ using FastAPI, Azure Services, and Modern Python Practices**
