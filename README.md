# Chat Application

A FastAPI-based chat application converted from Quart, designed to handle chat interactions, document serving, and user feedback.

## Features

- **Chat Interface**: Handle chat requests with message history and session state
- **Ask Endpoint**: Process user queries and return responses
- **Document Serving**: Serve static assets and content files
- **Vote/Feedback System**: Collect user feedback on responses
- **Authentication Setup**: Configurable authentication system
- **Static File Serving**: Serve static assets and content files

## API Endpoints

### Core Endpoints

- `GET /` - Main index page
- `GET /redirect` - Redirect endpoint
- `GET /favicon.ico` - Favicon serving
- `GET /assets/{file_path:path}` - Static asset serving
- `GET /content/{file_path:path}` - Content file serving

### Chat Endpoints

- `POST /ask` - Handle user queries
- `POST /chat` - Handle chat conversations
- `POST /vote` - Handle user feedback/voting

### Configuration Endpoints

- `GET /auth_setup` - Authentication configuration

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create environment file:
   ```bash
   cp .env.example .env
   ```

4. Configure your environment variables in `.env`

## Running the Application

### Development
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Using Docker
```bash
docker-compose up
```

## Project Structure

```
app/
├── main.py              # Main FastAPI application
├── core/
│   └── config.py        # Application configuration
├── api/                 # API endpoints (legacy from task app)
├── services/            # Business logic services
├── db/                  # Database models and repositories
├── exceptions/          # Custom exceptions
└── schemas/             # Pydantic schemas

static/                  # Static files (CSS, JS, images)
├── assets/              # Static assets
└── favicon.ico          # Favicon

content/                 # Content files to be served
logs/                    # Application logs
tests/                   # Test files
```

## Configuration

The application uses environment variables for configuration. Key settings include:

- `DEBUG`: Enable debug mode
- `ENVIRONMENT`: Application environment (development/production)
- `AZURE_OPENAI_*`: Azure OpenAI configuration
- `AZURE_SEARCH_*`: Azure Search configuration
- `AZURE_STORAGE_*`: Azure Storage configuration
- `AUTH_ENABLED`: Enable authentication

## API Documentation

Once the application is running, you can access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Request/Response Models

### ChatRequest
```json
{
  "messages": [],
  "context": {},
  "session_state": "string"
}
```

### AskRequest
```json
{
  "user_query": "string",
  "user_query_vector": [],
  "chatbot_response": "string",
  "count": 0,
  "upvote": true
}
```

### VoteRequest
```json
{
  "user_query": "string",
  "chatbot_response": "string",
  "count": 0,
  "upvote": true
}
```

## Development

This application is currently set up with placeholder implementations for all endpoints. To implement the full functionality, you'll need to:

1. Integrate with Azure OpenAI for chat responses
2. Implement Azure Search for document retrieval
3. Set up Azure Blob Storage for content serving
4. Implement authentication if required
5. Add proper error handling and validation
6. Implement logging and monitoring

## Testing

Run tests with:
```bash
pytest
```

## License

[Add your license information here]