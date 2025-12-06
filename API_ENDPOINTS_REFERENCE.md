# API Endpoints Reference

All endpoints are available in FastAPI interactive docs at: **http://localhost:8000/docs**

## Chat Endpoints

### 1. POST /chat
**Start a new chat or continue existing conversation**

**Location in docs:** `chat` section → `POST /chat`

**Request Body:**
```json
{
  "message": "What is this document about?",
  "file_id": "your-file-id-here",  // Optional
  "conversation_id": "conversation-id-here"  // Optional (creates new if not provided)
}
```

**Example 1: New chat with PDF**
```json
{
  "message": "What is this document about?",
  "file_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Example 2: Continue existing conversation**
```json
{
  "message": "Tell me more about section 2",
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Example 3: Continue conversation with new file**
```json
{
  "message": "What about this other document?",
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "file_id": "another-file-id-here"
}
```

**Response:**
```json
{
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "response": "The document discusses...",
  "retrieval_mode": "inline",
  "retrieved_chunks": []
}
```

---

### 2. GET /chats
**List all conversations**

**Location in docs:** `chat` section → `GET /chats`

**Query Parameters:**
- `limit` (optional, default: 20, max: 100): Number of conversations to return
- `offset` (optional, default: 0): Pagination offset

**Example URL:**
```
http://localhost:8000/chats?limit=20&offset=0
```

**Response:**
```json
{
  "chats": [
    {
      "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
      "created_at": "2024-01-01T00:00:00Z",
      "message_count": 5
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

---

### 3. GET /chats/{conversation_id}
**Get conversation details with all messages**

**Location in docs:** `chat` section → `GET /chats/{conversation_id}`

**Path Parameter:**
- `conversation_id`: UUID of the conversation

**Example URL:**
```
http://localhost:8000/chats/123e4567-e89b-12d3-a456-426614174000
```

**Response:**
```json
{
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "created_at": "2024-01-01T00:00:00Z",
  "messages": [
    {
      "role": "user",
      "content": "What is this document about?",
      "file_id": "123e4567-e89b-12d3-a456-426614174000",
      "retrieval_mode": null,
      "retrieved_chunks": null,
      "created_at": "2024-01-01T00:00:00Z"
    },
    {
      "role": "assistant",
      "content": "The document discusses...",
      "file_id": null,
      "retrieval_mode": "inline",
      "retrieved_chunks": [],
      "created_at": "2024-01-01T00:00:01Z"
    }
  ]
}
```

---

## File Endpoints (from Milestone 1)

### 4. POST /files/presign
**Get presigned URL for uploading PDF**

**Location in docs:** `files` section → `POST /files/presign`

### 5. GET /files
**List all files**

**Location in docs:** `files` section → `GET /files`

### 6. GET /files/{file_id}
**Get file details with download URL**

**Location in docs:** `files` section → `GET /files/{file_id}`

### 7. POST /webhook/ingest
**Webhook for S3 upload events**

**Location in docs:** `webhook` section → `POST /webhook/ingest`

---

## Testing in FastAPI Docs

1. **Start the server:**
   ```bash
   uvicorn main:app --reload
   ```

2. **Open the docs:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

3. **Test endpoints:**
   - Click on any endpoint to expand it
   - Click "Try it out"
   - Fill in the request body (JSON)
   - Click "Execute"
   - See the response below

---

## Complete Testing Flow

### Step 1: Upload a PDF (if not already done)
1. POST `/files/presign` → Get `file_id` and `presigned_url`
2. Upload PDF to S3 using the presigned URL (PUT request)
3. POST `/webhook/ingest` → Create file record

### Step 2: Start a chat with PDF
1. POST `/chat` with:
   ```json
   {
     "message": "What is this document about?",
     "file_id": "your-file-id-from-step-1"
   }
   ```
2. Save the `conversation_id` from the response

### Step 3: Continue the conversation
1. POST `/chat` with:
   ```json
   {
     "message": "Tell me more about section 2",
     "conversation_id": "conversation-id-from-step-2"
   }
   ```

### Step 4: View conversation history
1. GET `/chats` → List all conversations
2. GET `/chats/{conversation_id}` → View full conversation with all messages

---

## Tips for Testing in FastAPI Docs

1. **Copy-paste JSON:** You can copy the example JSON from this guide and paste it into the request body in the docs

2. **View schemas:** Click "Schema" next to any endpoint to see the exact request/response format

3. **Try different scenarios:**
   - Chat without file_id
   - Chat with file_id (file status = "uploaded")
   - Continue conversation
   - Add new file to existing conversation

4. **Check responses:** The response will show:
   - `conversation_id`: Use this for continuing conversations
   - `retrieval_mode`: Should be "inline" for Milestone 2
   - `retrieved_chunks`: Empty array for inline mode

---

## Common Issues

1. **"File not found" error:**
   - Make sure you uploaded the file to S3 first
   - Make sure you called `/webhook/ingest` to create the file record
   - Verify the file_id is correct

2. **"OpenAI API error":**
   - Check your `OPENAI_API_KEY` in `.env`
   - Make sure the model supports PDFs (gpt-4o-mini may have limitations)

3. **"Database connection error":**
   - Verify `DATABASE_URL` in `.env`
   - Make sure migrations are run: `alembic upgrade head`

