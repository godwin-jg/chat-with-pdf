# Testing Multi-File RAG in Swagger UI

## Access Swagger UI

1. **Start your server** (if not running):
   ```bash
   uvicorn main:app --reload
   ```

2. **Open Swagger UI**:
   - URL: http://localhost:8000/docs
   - Or ReDoc: http://localhost:8000/redoc

## Test Multi-File RAG Mode

### Prerequisites
- Two files with `ingestion_status="completed"`:
  - `minecraft.pdf`: `9f2d89bf-18b4-4bf4-a55c-3475db992210`
  - `SamplePDF.pdf`: `fc952142-4b8a-401f-80f1-ddf5c11e90af`

### Step-by-Step in Swagger UI

#### Step 1: Start Conversation with First File

1. **Navigate to**: `POST /chat` endpoint
2. **Click**: "Try it out"
3. **Request Body**:
   ```json
   {
     "message": "What does this document say about Minecraft?",
     "file_id": "9f2d89bf-18b4-4bf4-a55c-3475db992210"
   }
   ```
4. **Click**: "Execute"
5. **Copy the `conversation_id`** from the response

**Expected Response**:
```json
{
  "conversation_id": "36769911-528c-43d6-8536-ecb36157556c",
  "response": "...",
  "retrieval_mode": "rag",
  "retrieved_chunks": [...]
}
```

#### Step 2: Add Second File to Same Conversation

1. **Stay in**: `POST /chat` endpoint
2. **Click**: "Try it out" again
3. **Request Body** (use the `conversation_id` from Step 1):
   ```json
   {
     "message": "Now compare this with the other document about MCPACK files",
     "conversation_id": "36769911-528c-43d6-8536-ecb36157556c",
     "file_id": "fc952142-4b8a-401f-80f1-ddf5c11e90af"
   }
   ```
4. **Click**: "Execute"

**Expected Response**:
```json
{
  "conversation_id": "36769911-528c-43d6-8536-ecb36157556c",
  "response": "... (synthesizes info from both documents)",
  "retrieval_mode": "rag",
  "retrieved_chunks": [
    {
      "chunk_text": "... (from minecraft.pdf)",
      "similarity_score": 0.78
    },
    {
      "chunk_text": "... (from SamplePDF.pdf)",
      "similarity_score": 0.77
    }
  ]
}
```

**What to Verify**:
- ✅ `retrieval_mode: "rag"`
- ✅ `retrieved_chunks` contains chunks from BOTH files
- ✅ Response references content from both documents
- ✅ Same `conversation_id` as Step 1

#### Step 3: Test Direct Multi-File Retrieval

1. **Navigate to**: `POST /retrieve` endpoint
2. **Click**: "Try it out"
3. **Request Body**:
   ```json
   {
     "query": "What is Minecraft?",
     "file_ids": [
       "9f2d89bf-18b4-4bf4-a55c-3475db992210",
       "fc952142-4b8a-401f-80f1-ddf5c11e90af"
     ],
     "top_k": 5
   }
   ```
4. **Click**: "Execute"

**Expected Response**:
```json
{
  "results": [
    {
      "chunk_id": "...",
      "file_id": "9f2d89bf-18b4-4bf4-a55c-3475db992210",
      "chunk_text": "...",
      "similarity_score": 0.80
    },
    {
      "chunk_id": "...",
      "file_id": "fc952142-4b8a-401f-80f1-ddf5c11e90af",
      "chunk_text": "...",
      "similarity_score": 0.79
    }
  ]
}
```

**What to Verify**:
- ✅ Results from both `file_ids`
- ✅ Each result shows which `file_id` it came from
- ✅ Results sorted by similarity score

#### Step 4: View Conversation History

1. **Navigate to**: `GET /chats/{conversation_id}` endpoint
2. **Click**: "Try it out"
3. **Path Parameter**: Enter the `conversation_id` from Step 1
4. **Click**: "Execute"

**Expected Response**:
```json
{
  "conversation_id": "...",
  "created_at": "...",
  "messages": [
    {
      "role": "user",
      "content": "...",
      "file_id": "9f2d89bf-18b4-4bf4-a55c-3475db992210",
      "retrieval_mode": null,
      "retrieved_chunks": null
    },
    {
      "role": "assistant",
      "content": "...",
      "retrieval_mode": "rag",
      "retrieved_chunks": [...]
    },
    {
      "role": "user",
      "content": "...",
      "file_id": "fc952142-4b8a-401f-80f1-ddf5c11e90af",
      "retrieval_mode": null,
      "retrieved_chunks": null
    },
    {
      "role": "assistant",
      "content": "...",
      "retrieval_mode": "rag",
      "retrieved_chunks": [
        // Chunks from BOTH files
      ]
    }
  ]
}
```

**What to Verify**:
- ✅ All messages stored correctly
- ✅ Assistant messages have `retrieval_mode: "rag"`
- ✅ Last message has `retrieved_chunks` from both files

## Quick Test Checklist

### Single File RAG
- [ ] `POST /chat` with one `file_id`
- [ ] Verify `retrieval_mode: "rag"`
- [ ] Verify `retrieved_chunks` present

### Multi-File RAG
- [ ] `POST /chat` with first `file_id` → get `conversation_id`
- [ ] `POST /chat` with same `conversation_id` + second `file_id`
- [ ] Verify `retrieved_chunks` from both files
- [ ] Verify response synthesizes both documents

### Direct Retrieval
- [ ] `POST /retrieve` with multiple `file_ids`
- [ ] Verify results from all specified files
- [ ] Verify each result shows correct `file_id`

### Conversation History
- [ ] `GET /chats/{conversation_id}`
- [ ] Verify all messages stored
- [ ] Verify `retrieval_mode` and `retrieved_chunks` persisted

## Tips for Swagger UI

1. **Copy Response Values**: Click the response to expand it, then copy values like `conversation_id`
2. **Save Requests**: Use the "Try it out" feature to test different scenarios
3. **Check Response Schema**: Expand the response model to see all fields
4. **View Examples**: Each endpoint has example request/response in the schema

## Troubleshooting

### Issue: `retrieval_mode: "inline"` instead of `"rag"`
- **Check**: File status is `"completed"` (use `GET /files/{file_id}`)
- **Check**: Server logs for `"RAG mode enabled"`

### Issue: No chunks from second file
- **Check**: Both files have `ingestion_status="completed"`
- **Check**: Both `file_ids` are in the conversation history
- **Check**: Server logs for `"Collected X file_id(s), has_completed=True"`

### Issue: Error 400 or 500
- **Check**: File IDs are valid UUIDs
- **Check**: Files exist in database (use `GET /files`)
- **Check**: Server logs for detailed error messages

