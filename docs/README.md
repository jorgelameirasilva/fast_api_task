# Chat Service Flow Documentation

This directory contains visual documentation of the chat service architecture with session management.

## Diagrams

### 1. Detailed Flow (`chat-flow-detailed.png`)
Shows the complete end-to-end flow including:
- HTTP request handling
- Authentication flow
- Session management logic
- Database operations
- LLM processing
- Response formatting
- All service interactions

### 2. Simplified Flow (`chat-flow-simple.png`)
Shows the high-level flow focusing on:
- Main components
- Session decision logic
- Database interactions
- Core processing steps

## Architecture Overview

The chat service uses a clean, scalable architecture:

- **Single Endpoint**: Only `/chat` route needed
- **Session Management**: Transparent conversation history via session_id
- **Database**: One document per message in MongoDB/Cosmos DB
- **Scalability**: No document size limits, efficient queries

## Database Structure

Each conversation message is stored as an individual document:

```javascript
{
  "_id": "message-uuid",
  "user_id": "user123",
  "session_id": "session-uuid",
  "message": {
    "role": "user|assistant",
    "content": "message content"
  },
  "created_at": "2024-01-01T10:00:00Z"
}
```

## Key Benefits

- ✅ **Simple API**: Single `/chat` endpoint handles everything
- ✅ **Scalable Storage**: No MongoDB 16MB document limits
- ✅ **User Isolation**: All messages scoped to specific users
- ✅ **Efficient Queries**: `find({session_id, user_id}).sort({created_at: 1})`
- ✅ **Clean Architecture**: Focused services with clear responsibilities

## Files

- `chat-flow-detailed.mmd` - Detailed mermaid diagram source
- `chat-flow-simple.mmd` - Simplified mermaid diagram source
- `chat-flow-detailed.png` - Detailed flow image (PNG)
- `chat-flow-simple.png` - Simplified flow image (PNG)
- `chat-flow-detailed.svg` - Detailed flow image (SVG, scalable)
- `chat-flow-simple.svg` - Simplified flow image (SVG, scalable) 