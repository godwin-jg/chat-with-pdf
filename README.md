# Chat with PDF - Hybrid-Inline PDF + RAG Chat System

A FastAPI-based backend system that enables chat interactions with PDF documents using a hybrid approach: **Inline mode** (Base64 PDF via Vision API) for immediate access and **RAG mode** (Vector Search) for optimized retrieval after ingestion.

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Setup Instructions](#setup-instructions)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Project Structure](#project-structure)

## Features

- **Hybrid PDF Processing**: Automatically switches between inline (Base64) and RAG modes based on file ingestion status
- **Manual Chunking**: Custom chunking implementation with configurable token windows and overlap
- **Vector Search**: Semantic search using Upstash Vector with metadata filtering
- **OpenAI Tool Calling**: Dynamic retrieval using OpenAI function calling
- **State Management**: Tracks file ingestion status (`uploaded` → `completed` or `failed`)
- **Multi-file Conversations**: Support for referencing multiple PDFs in a single conversation
- **Conversation History**: Maintains full conversation context with message-level file associations

## Architecture Overview

### System Flow

```
┌─────────┐
│ Client  │
└────┬────┘
     │
     │ 1. POST /files/presign
     │    → Get file_id + presigned URL
     │
     ▼
┌─────────┐
│   S3    │ ← 2. PUT PDF to presigned URL
└────┬────┘
     │
     │ 3. S3 Event Trigger
     │
     ▼
┌─────────┐
│ Lambda  │ → 4. POST /webhook/ingest
└────┬────┘    → Create file record (status: "uploaded")
     │
     │ 5. Background Task
     │    → Download PDF
     │    → Extract text
     │    → Chunk text
     │    → Generate embeddings
     │    → Upsert to Upstash Vector
     │    → Update status: "completed"
     │
     ▼
┌─────────┐
│   DB    │ ← Store file metadata, conversations, messages
└────┬────┘
     │
     │ 6. POST /chat
     │    → Check ingestion_status
     │    → If "uploaded": Inline mode (Base64 PDF)
     │    → If "completed": RAG mode (Vector Search)
     │
     ▼
┌─────────┐
│ OpenAI  │ ← LLM with context (PDF or retrieved chunks)
└─────────┘
```

### Architecture Diagram Description

The system follows a **Client → S3 → Webhook → DB** flow:

1. **Client Request**: User requests a presigned URL via `POST /files/presign`
2. **S3 Upload**: Client uploads PDF directly to S3 using the presigned URL
3. **S3 Event**: AWS Lambda is triggered by the S3 upload event
4. **Webhook Processing**: Lambda calls `POST /webhook/ingest` with S3 event payload
5. **Database Record**: Backend creates a file record with `ingestion_status = "uploaded"`
6. **Background Ingestion**: System processes the file asynchronously:
   - Downloads PDF from S3
   - Extracts text using PyMuPDF
   - Chunks text manually (512 tokens, 102 token overlap)
   - Generates embeddings using OpenAI `text-embedding-3-small`
   - Stores vectors in Upstash Vector with metadata
   - Updates status to `"completed"`
7. **Chat Interaction**: User chats via `POST /chat`:
   - System checks file ingestion status
   - **If "uploaded"**: Downloads PDF, converts to images, sends via Vision API (Inline mode)
   - **If "completed"**: Uses OpenAI tool calling to retrieve relevant chunks from vector DB (RAG mode)
8. **Response**: LLM generates response with appropriate context

### Key Design Decisions

- **Manual Chunking**: Implemented custom chunking logic for precise control over token windows and overlap
- **Hybrid Logic**: State machine that switches between Base64 and RAG based on ingestion status
- **Message-level File Association**: Files are associated with individual messages, not conversations, enabling multi-file support
- **Metadata Filtering**: Vector search uses metadata filtering to only retrieve chunks from files referenced in the conversation

## Setup Instructions

### Prerequisites

- Python 3.10+
- Poetry (for dependency management)
- PostgreSQL database (Neon recommended)
- AWS S3 bucket (with prefix: `swe-test-godwin-j`)
- Upstash Vector namespace (with prefix: `swe-test-godwin-j`)
- OpenAI API key

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini  # or gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Upstash Vector
UPSTASH_VECTOR_REST_URL=https://...
UPSTASH_VECTOR_REST_TOKEN=...
UPSTASH_VECTOR_NAMESPACE=swe-test-godwin-j

# AWS S3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
AWS_S3_BUCKET=swe-test-godwin-j

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Poetry Installation

1. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install Dependencies**:
   ```bash
   poetry install
   ```

3. **Activate Virtual Environment**:
   ```bash
   poetry shell
   ```

   Or run commands with `poetry run`:
   ```bash
   poetry run uvicorn main:app --reload
   ```

### Database Setup

1. **Run Migrations**:
   ```bash
   alembic upgrade head
   ```

2. **Verify Schema**:
   - `files` table: Stores PDF metadata and ingestion status
   - `conversations` table: Stores conversation records
   - `messages` table: Stores individual messages with file associations

### Running the Application

```bash
# Development server with auto-reload
poetry run uvicorn main:app --reload

# Production server
poetry run uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/

## API Documentation

### File Management Endpoints

#### POST /files/presign

Generate a presigned URL for uploading a PDF file to S3.

**Request:**
```json
{
  "filename": "document.pdf"
}
```

**Response:**
```json
{
  "file_id": "123e4567-e89b-12d3-a456-426614174000",
  "presigned_url": "https://s3.amazonaws.com/bucket/uploads/...",
  "expires_in_seconds": 3600
}
```

**Usage:**
1. Call this endpoint to get a `file_id` and `presigned_url`
2. Upload the PDF to S3 using a PUT request to the `presigned_url`
3. The file record will be created automatically when the webhook is triggered

---

#### GET /files

List all files with pagination.

**Query Parameters:**
- `limit` (optional, default: 20, max: 100): Number of files to return
- `offset` (optional, default: 0): Pagination offset

**Response:**
```json
{
  "files": [
    {
      "file_id": "123e4567-e89b-12d3-a456-426614174000",
      "s3_key": "uploads/123e4567-e89b-12d3-a456-426614174000.pdf",
      "ingestion_status": "completed",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0
}
```

**Ingestion Status Values:**
- `uploaded`: File is uploaded but not yet processed
- `completed`: File has been chunked, embedded, and indexed
- `failed`: Ingestion failed (check logs for details)

---

#### GET /files/{file_id}

Get file details with presigned download URL.

**Path Parameter:**
- `file_id`: UUID of the file

**Response:**
```json
{
  "file_id": "123e4567-e89b-12d3-a456-426614174000",
  "s3_key": "uploads/123e4567-e89b-12d3-a456-426614174000.pdf",
  "ingestion_status": "completed",
  "presigned_download_url": "https://s3.amazonaws.com/...",
  "download_url_expires_in_seconds": 3600,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

### Webhook Endpoints

#### POST /webhook/ingest

Webhook endpoint for S3 upload events (called by AWS Lambda).

**Request:**
```json
{
  "s3_bucket": "swe-test-godwin-j",
  "s3_key": "uploads/123e4567-e89b-12d3-a456-426614174000.pdf"
}
```

**Response:**
```json
{
  "file_id": "123e4567-e89b-12d3-a456-426614174000",
  "s3_key": "uploads/123e4567-e89b-12d3-a456-426614174000.pdf",
  "ingestion_status": "uploaded",
  "message": "File record created successfully. Ingestion started in background."
}
```

**Behavior:**
1. Extracts `file_id` from S3 key path
2. Creates file record with status `"uploaded"`
3. Starts background task for full ingestion pipeline
4. Returns immediately (ingestion runs asynchronously)

---

### Chat Endpoints

#### POST /chat

Start a new chat or continue an existing conversation.

**Request:**
```json
{
  "message": "What is this document about?",
  "file_id": "123e4567-e89b-12d3-a456-426614174000",  // Optional
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000"  // Optional
}
```

**Response:**
```json
{
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "response": "The document discusses...",
  "retrieval_mode": "rag",
  "retrieved_chunks": [
    {
      "chunk_text": "This is a relevant chunk...",
      "similarity_score": 0.92
    }
  ]
}
```

**Retrieval Modes:**
- `inline`: PDF sent as Base64 images via Vision API (when `ingestion_status = "uploaded"`)
- `rag`: Semantic search with retrieved chunks (when `ingestion_status = "completed"`)

**Behavior:**
1. Creates or retrieves conversation
2. Stores user message with optional `file_id`
3. Checks ingestion status for all files in conversation
4. **If "uploaded"**: Downloads PDF, converts to images, sends via Vision API
5. **If "completed"**: Uses OpenAI tool calling to retrieve relevant chunks
6. Sends context to LLM and stores assistant response

**Example Usage:**

**New chat with PDF:**
```json
{
  "message": "What is this document about?",
  "file_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Continue conversation:**
```json
{
  "message": "Tell me more about section 2",
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Add new file to existing conversation:**
```json
{
  "message": "What about this other document?",
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "file_id": "another-file-id-here"
}
```

---

#### GET /chats

List all conversations with pagination.

**Query Parameters:**
- `limit` (optional, default: 20, max: 100): Number of conversations to return
- `offset` (optional, default: 0): Pagination offset

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

#### GET /chats/{conversation_id}

Get conversation details with all messages.

**Path Parameter:**
- `conversation_id`: UUID of the conversation

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
      "retrieval_mode": "rag",
      "retrieved_chunks": [
        {
          "chunk_text": "This is a relevant chunk...",
          "similarity_score": 0.92
        }
      ],
      "created_at": "2024-01-01T00:00:01Z"
    }
  ]
}
```

---

### Retrieval Endpoints

#### POST /retrieve

Retrieve relevant chunks from vector database (for testing/debugging).

**Request:**
```json
{
  "file_ids": ["123e4567-e89b-12d3-a456-426614174000"],
  "query": "What is the main topic?",
  "top_k": 5
}
```

**Response:**
```json
{
  "results": [
    {
      "chunk_id": "123e4567-e89b-12d3-a456-426614174000-chunk-0",
      "file_id": "123e4567-e89b-12d3-a456-426614174000",
      "chunk_text": "This is a relevant chunk...",
      "similarity_score": 0.92
    }
  ]
}
```

**Note:** This endpoint is for testing retrieval independently. In production, the `/chat` endpoint uses this logic internally with file_ids collected from conversation history.

---

## Testing

### Complete Testing Flow

1. **Upload a PDF:**
   ```bash
   # Get presigned URL
   curl -X POST http://localhost:8000/files/presign \
     -H "Content-Type: application/json" \
     -d '{"filename": "document.pdf"}'
   
   # Upload PDF to S3 (use presigned_url from response)
   curl -X PUT "<presigned_url>" \
     -H "Content-Type: application/pdf" \
     --upload-file document.pdf
   
   # Trigger webhook (or wait for Lambda)
   curl -X POST http://localhost:8000/webhook/ingest \
     -H "Content-Type: application/json" \
     -d '{
       "s3_bucket": "swe-test-godwin-j",
       "s3_key": "uploads/<file_id>.pdf"
     }'
   ```

2. **Start a chat:**
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{
       "message": "What is this document about?",
       "file_id": "<file_id>"
     }'
   ```

3. **Continue conversation:**
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{
       "message": "Tell me more about section 2",
       "conversation_id": "<conversation_id>"
     }'
   ```

### Interactive API Documentation

The easiest way to test endpoints is using the FastAPI interactive docs:

1. Start the server: `poetry run uvicorn main:app --reload`
2. Open http://localhost:8000/docs
3. Click on any endpoint → "Try it out" → Fill in request body → "Execute"

## Project Structure

```
godwin-j-chat-with-pdf/
├── api/
│   ├── routes/           # FastAPI route handlers
│   │   ├── chat_router.py
│   │   ├── file_router.py
│   │   ├── retrieve_router.py
│   │   └── webhook_router.py
│   └── schemas/          # Pydantic request/response models
│       ├── request.py
│       └── response.py
├── core/                 # Core utilities and integrations
│   ├── aws/
│   │   └── s3_client.py
│   ├── chunker/
│   │   └── text_chunker.py
│   ├── openai/
│   │   └── openai_client.py
│   ├── parsers/
│   │   └── pdf_parser.py
│   └── vector/
│       └── upstash_client.py
├── dao/                  # Data Access Objects
│   ├── models/          # SQLAlchemy ORM models
│   │   ├── base.py
│   │   ├── file.py
│   │   ├── conversation.py
│   │   └── message.py
│   ├── base_dao.py
│   ├── file_dao.py
│   └── chat_dao.py
├── services/            # Business logic
│   ├── chat_service/
│   │   └── chat_handler.py
│   └── file_service/
│       ├── upload_service.py
│       ├── ingestion_service.py
│       └── file_service.py
├── alembic/             # Database migrations
├── docs/                # Documentation
│   ├── ARCHITECTURE.md
│   └── DEVELOPMENT_LOG.md
├── config.py            # Pydantic Settings
├── database.py          # Database connection
├── main.py              # FastAPI app entry point
├── pyproject.toml       # Poetry dependencies
└── README.md
```

### Architecture Layers

- **Routes** (`api/routes/`): HTTP request handling, validation, response formatting
- **Services** (`services/`): Business logic orchestration
- **DAOs** (`dao/`): Database operations and queries
- **Core** (`core/`): Reusable integrations (AWS, OpenAI, Upstash, etc.)

### Dependency Flow

```
Routes → Services → DAOs → Models
         ↓
      Core (AWS, OpenAI, Upstash)
```

---

## Additional Resources

- [Architecture Documentation](docs/ARCHITECTURE.md) - Detailed architecture decisions
- [Development Log](docs/DEVELOPMENT_LOG.md) - Architecture decisions and development notes
- [API Endpoints Reference](API_ENDPOINTS_REFERENCE.md) - Quick reference for all endpoints

---

## License

This project is part of a take-home assignment.
