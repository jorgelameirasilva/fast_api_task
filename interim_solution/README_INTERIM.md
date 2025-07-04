# Interim Solution - CosmosService Integration

This is an interim solution that integrates the new CosmosService with the existing old repo architecture. This provides session management and vote storage capabilities while maintaining the existing chat functionality.

## What's New

### Database Integration
- **Session Management**: Chat conversations are now stored in MongoDB
- **Vote Storage**: User votes and feedback are saved to the database
- **User Isolation**: Each user can only access their own sessions and messages

### New API Endpoints

#### Session Management
- `GET /sessions` - Get all sessions for the current user
- `GET /sessions/{session_id}/messages` - Get all messages in a session
- `DELETE /sessions/{session_id}` - Delete a session and all its messages

#### Enhanced Chat
- `POST /chat` - Enhanced to save messages to database
  - Include `session_id` in request to continue existing session
  - Omit `session_id` to create new session
  - Response includes `session_id` for future requests

#### Enhanced Voting
- `POST /vote` - Enhanced to save votes to database
  - Include `message_id` in request to save vote to database
  - Original logging functionality preserved

## Environment Variables

Add these environment variables to your `.env` file:

```env
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017/
COSMOS_DB_DATABASE_NAME=chatbot

# Existing variables (keep your current values)
AZURE_SEARCH_SERVICE=...
AZURE_OPENAI_SERVICE=...
# ... etc
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start MongoDB (if running locally):
```bash
# Using Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Or install MongoDB locally
# https://docs.mongodb.com/manual/installation/
```

3. Run the application:
```bash
python app.py
```

## Usage Examples

### Starting a New Chat Session
```javascript
// First message - no session_id
const response = await fetch('/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    messages: [{ role: 'user', content: 'Hello!' }],
    context: { knowledge_base: 'general' }
  })
});

const result = await response.json();
const sessionId = result.session_id; // Save this for subsequent messages
```

### Continuing a Chat Session
```javascript
// Subsequent messages - include session_id
const response = await fetch('/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    messages: [{ role: 'user', content: 'How are you?' }],
    session_id: sessionId,
    context: { knowledge_base: 'general' }
  })
});
```

### Voting on a Message
```javascript
// Vote on a specific message
const response = await fetch('/vote', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message_id: 'message_123',
    upvote: 1,
    downvote: 0,
    feedback: 'Very helpful!',
    count: 1
  })
});
```

### Getting User Sessions
```javascript
// Get all sessions for current user
const response = await fetch('/sessions');
const data = await response.json();
console.log(data.sessions); // Array of session objects
```

### Getting Session Messages
```javascript
// Get all messages in a session
const response = await fetch(`/sessions/${sessionId}/messages`);
const data = await response.json();
console.log(data.messages); // Array of message objects
```

## Database Schema

### Messages Collection
Each message is stored as a document with this structure:
```json
{
  "_id": "message_123",
  "session_id": "session_456", 
  "user_id": "user_789",
  "message": {
    "role": "user|assistant",
    "content": "Message content"
  },
  "knowledge_base": "general",
  "upvote": 0,
  "downvote": 0,
  "feedback": null,
  "created_at": "2023-...",
  "updated_at": "2023-...",
  "voted_at": null,
  "is_active": true
}
```

## Migration to Full New Architecture

This interim solution makes it easy to eventually migrate to the full new architecture:

1. **Session data is already in the new format** - no data migration needed
2. **Vote data is preserved** - all vote history is maintained
3. **API patterns are similar** - minimal frontend changes required
4. **User isolation is enforced** - security model is already in place

## Differences from Original

### What Changed
- Messages are now saved to MongoDB instead of being stateless
- Votes are saved to database instead of just logged
- New session management endpoints added
- Response includes `session_id` for client session tracking

### What Stayed the Same
- All existing authentication and authorization
- Same chat approach and AI processing
- Same Azure service integrations
- Same API request/response formats (with additions)
- All existing logging and monitoring

## Testing

Test the integration with the demo:
```bash
python demo_cosmos_service.py
```

This will test all database operations and confirm everything is working correctly.

## Production Considerations

1. **MongoDB Connection**: Update `MONGODB_URL` to point to your production MongoDB instance
2. **Database Name**: Set `COSMOS_DB_DATABASE_NAME` appropriately for your environment
3. **Indexing**: The service automatically creates indexes for optimal performance
4. **Backup**: Ensure your MongoDB instance has proper backup configured
5. **Monitoring**: Monitor MongoDB performance and connection health

This interim solution provides immediate session and vote persistence while maintaining full compatibility with the existing system! 