Detailed Requirements
Hybrid-Inline PDF + RAG Chat System
User Journey
User uploads a PDF via the /presign endpoint to get a presigned S3 URL. The endpoint generates a unique file_id and embeds it in the S3 key path (e.g., uploads/{file_id}.pdf).
Presigned URL is returned with the file_id, expiring in 1 hour.
User uploads the PDF directly to S3 using the presigned URL with a PUT call.
AWS Lambda is triggered by the S3 upload event and calls /webhook/ingest with the S3 event payload.
Backend extracts the file_id from the S3 key and creates a file record in Postgres with ingestion_status = "uploaded".
Backend ingestion worker:
Downloads the PDF from S3
Extracts text and chunks it manually
Generates embeddings and stores them in Upstash Vector
Updates the file record to ingestion_status = "completed"
User starts chatting via the /chat endpoint:
User includes file_id in the chat request (typically with the first message, but can be any message)
If ingestion_status = "uploaded": System downloads the PDF from S3, converts it to base64, and patches it into the context window at the message where file_id was provided
If ingestion_status = "completed": System uses RAG with semantic search via OpenAI tool calling to retrieve relevant chunks
Chat maintains conversation history and dynamically patches the context window:
When building the message history for the LLM, the system checks each message's file_id
For messages with a file_id, check the file's current ingestion_status
If uploaded: Include the base64 PDF file block with that message in the context window
If completed: Exclude the file block, rely on retrieved chunks from semantic search instead
Messages without file_id are included as-is
General Requirements
Code Organization & Architecture
Your project should follow a clean, modular folder structure that separates concerns and promotes maintainability. While you have flexibility in your exact structure, here's a recommended approach:

project-root/
├── api/
│   ├── routes/
│   │   ├── chat_router.py       # Chat endpoints (/chat, /chats)
│   │   ├── file_router.py       # File endpoints (/presign, /files)
│   │   └── webhook_router.py    # Webhook endpoints (/webhook/ingest)
│   └── schemas/
│       ├── request.py           # Request Pydantic models
│       └── response.py          # Response Pydantic models
│
├── services/
│   ├── file_service/
│   │   ├── __init__.py
│   │   ├── upload_service.py   # Presigned URL generation
│   │   └── ingestion_service.py # PDF processing, chunking, embedding
│   ├── chat_service/
│   │   ├── __init__.py
│   │   ├── chat_handler.py     # Chat logic, context patching
│   │   └── retrieval_service.py # RAG and tool calling logic
│   └── __init__.py
│
├── dao/                        # Data Access Objects
│   ├── models/                # SQLAlchemy ORM models
│   │   ├── base.py           # Base model
│   │   ├── file.py           # File model
│   │   ├── conversation.py   # Conversation model
│   │   ├── message.py        # Message model
│   │   └── __init__.py
│   ├── base_dao.py            # Base DAO with common operations
│   ├── file_dao.py            # File CRUD operations
│   ├── chat_dao.py            # Conversation & message operations
│   └── __init__.py
│
├── core/                       # Core utilities and integrations
│   ├── aws/
│   │   ├── s3_client.py        # S3 operations (presigned URLs, download)
│   │   └── __init__.py
│   ├── parsers/
│   │   ├── pdf_parser.py       # PDF text extraction
│   │   └── __init__.py
│   ├── chunker/
│   │   ├── text_chunker.py     # Chunking logic
│   │   └── __init__.py
│   ├── embeddings/
│   │   ├── openai_embeddings.py # OpenAI embedding generation
│   │   └── __init__.py
│   ├── vector/
│   │   ├── upstash_client.py   # Upstash Vector operations
│   │   └── __init__.py
│   └── utils/
│       ├── logger.py           # Logging configuration
│       └── helpers.py          # Common helper functions
│
├── types/                      # Pydantic models (domain types)
│   ├── chat.py                 # Chat-related types
│   ├── file.py                 # File-related types
│   └── __init__.py
│
├── alembic/                     # Database migrations (optional)
│   ├── versions/
│   └── env.py
│
├── config.py                    # Pydantic Settings (loads from .env)
├── main.py                      # FastAPI app entry point
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (provided)
├── .gitignore
└── README.md
Architecture Principles
Separation of Concerns:

api/ handles HTTP routing and request/response validation
services/ contains business logic
dao/ manages database operations
core/ provides reusable integrations and utilities

Dependency Flow: Routes → Services → DAOs → Models

Routes should be thin, delegating to services
Services orchestrate business logic
DAOs handle database queries

Type Safety:

Use Pydantic models for API contracts (api/schemas/)
Use Pydantic models for domain types (types/)
Use SQLAlchemy models for database entities (models/)

Configuration Management:

Use pydantic-settings to load environment variables
Define all config in config.py (database URL, API keys, S3 bucket, etc.)
Never hardcode secrets

Error Handling:

Create custom exceptions where appropriate
Handle errors gracefully at the service layer
Return appropriate HTTP status codes at the route layer
Notes
This is a recommendation, not a strict requirement: Feel free to organize differently if you have a better approach
Document your structure in your README or ARCHITECTURE.md
Consistency matters more than the exact structure: Pick a pattern and stick with it
Don't over-engineer: For a 2-day assignment, a simpler structure is acceptable if it's clean and readable with good docstrings and comments
Functional Requirements
The endpoints are organized by milestone to match the implementation order.
Milestone 1: File Upload & CRUD APIs
1.1 PDF Upload Workflow (/presign)
Endpoint: POST /presign

Request:

{
  "filename": "document.pdf"
}

Response:

{
  "file_id": "uuid",
  "presigned_url": "https://s3.amazonaws.com/your-bucket/uploads/{file_id}.pdf?...",
  "expires_in_seconds": 3600
}

Behavior:

Generate a unique file_id (UUID)
Construct the S3 key as uploads/{file_id}.pdf
Return a presigned S3 URL valid for 1 hour
Important: Do NOT create a Postgres record yet. The record will be created by /webhook/ingest once the file is confirmed in S3
Return the file_id to the client so they can use it to track the upload and start chatting later
1.2 Ingestion Pipeline - Basic (/webhook/ingest)
Endpoint: POST /webhook/ingest

Request (called by AWS Lambda):

{
  "s3_bucket": "swe-test-yourname",
  "s3_key": "uploads/{file_id}.pdf"
}

Behavior:

Extract the file_id from the S3 key path
Create a file record in Postgres with ingestion_status = "uploaded", s3_key, and created_at
Download the PDF from S3
Extract text using a PDF parser (markitdown, pdfplumber, pymupdf, or pypdf2)
Chunk the text manually (fixed-size chunks with overlap, semantic boundaries, or sentence-based)
Generate embeddings for each chunk using OpenAI's text-embedding-3-small
Store embeddings in Upstash Vector with metadata including file_id, chunk_id, and chunk_text (the file_id is critical for metadata filtering during retrieval)
Update the file record to ingestion_status = "completed"
Handle errors gracefully (set status to "failed" if any step breaks)

Note for Milestone 1: Initially, this endpoint only needs to create the file record with status "uploaded". The full ingestion logic (text extraction, chunking, embeddings) is implemented in Milestone 3.

Local Testing with ngrok: During development, use ngrok to expose your local FastAPI server to the internet. Configure your AWS Lambda function to call your ngrok URL (e.g., https://abc123.ngrok.io/webhook/ingest). This allows you to test the full S3 → Lambda → FastAPI webhook flow locally without deploying your backend.
1.3 List Files API (/files)
Endpoint: GET /files

Query Parameters:

limit (optional, default: 20): Number of files to return
offset (optional, default: 0): Pagination offset

Response:

{
  "files": [
    {
      "file_id": "uuid",
      "s3_key": "uploads/{file_id}.pdf",
      "ingestion_status": "completed",
      "created_at": "timestamp",
      "updated_at": "timestamp"
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0
}

Behavior:

Retrieve all files ordered by created_at (most recent first)
Return file metadata including ingestion status
Support pagination via limit/offset
1.4 Get File API (/files/{file_id})
Endpoint: GET /files/{file_id}

Response:

{
  "file_id": "uuid",
  "s3_key": "uploads/{file_id}.pdf",
  "ingestion_status": "completed",
  "presigned_download_url": "https://s3.amazonaws.com/...",
  "download_url_expires_in_seconds": 3600,
  "created_at": "timestamp",
  "updated_at": "timestamp"
}

Behavior:

Retrieve a specific file by ID
Generate a presigned GET URL for downloading the PDF from S3 (valid for 1 hour)
Return file metadata and download URL
Return 404 if file not found
Milestone 2: Inline Chat with Base64 PDF
2.1 Chat Endpoint - Basic (/chat)
Endpoint: POST /chat

Request:

{
  "file_id": "uuid",
  "message": "What is the document about?",
  "conversation_id": "uuid"
}

Note:

file_id is optional. Include it when you want the message to reference a specific PDF file.
file_id can be included in any message (not just the first one).
conversation_id is optional for the first message; if not provided, a new conversation is created.

Response:

{
  "conversation_id": "uuid",
  "response": "assistant_response",
  "retrieval_mode": "inline" | "rag",
  "retrieved_chunks": [
    {
      "chunk_text": "...",
      "similarity_score": 0.92
    }
  ]
}

Behavior for Milestone 2 (Inline mode only):

Fetch or create conversation (if conversation_id not provided, create new conversation)
If file_id is provided in the request:
Fetch the file record
Store the file_id with this message in the database
Fetch the conversation history from the database
Context Window Patching (Milestone 2 - inline only):
Iterate through all messages in the conversation history
For each message with a file_id:
Download the PDF from S3
Convert the PDF to base64
Patch the context window to include the base64 PDF file block with that message
Messages without file_id are included as-is
Send the patched conversation history to OpenAI LLM (Use only gpt-4.1-mini)
Store the assistant's response in the database with retrieval_mode = "inline"
Return the response

Reference: Follow this guide to send the PDF file as base64 to the LLM: OpenAI PDF Files Guide
2.2 List Chats API (/chats)
Endpoint: GET /chats

Query Parameters:

limit (optional, default: 20): Number of chats to return
offset (optional, default: 0): Pagination offset

Response:

{
  "chats": [
    {
      "conversation_id": "uuid",
      "created_at": "timestamp",
      "message_count": 5
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}

Behavior:

Retrieve all conversations ordered by created_at (most recent first)
Return conversation metadata with message counts
Support pagination via limit/offset
Note: file_ids are not shown here since they're stored per message, not per conversation
2.3 Get Chat API (/chats/{conversation_id})
Endpoint: GET /chats/{conversation_id}

Response:

{
  "conversation_id": "uuid",
  "created_at": "timestamp",
  "messages": [
    {
      "role": "user",
      "content": "What is this document about?",
      "file_id": "uuid",
      "created_at": "timestamp"
    },
    {
      "role": "assistant",
      "content": "The document discusses...",
      "retrieval_mode": "inline",
      "retrieved_chunks": [],
      "created_at": "timestamp"
    }
  ]
}

Behavior:

Retrieve a specific conversation by ID
Return all messages in chronological order
Include file_id for each message (if the message referenced a file)
Include metadata about retrieval mode used for each response
Return 404 if conversation not found
Milestone 3: RAG Pipeline & Retrieval
3.1 Ingestion Pipeline - Full (/webhook/ingest)
For Milestone 3, extend the /webhook/ingest endpoint (defined in 1.2) to include the full ingestion pipeline:

Additional Steps:

Extract text from PDF using a library like markitdown, pymupdf, or pypdf2
Implement manual chunking logic (fixed-size, semantic, or hybrid approach)
Generate embeddings for each chunk using OpenAI's text-embedding-3-small
Store embeddings in Upstash Vector with metadata including file_id, chunk_id, and chunk_text
Update the file record to ingestion_status = "completed"
Handle errors gracefully (set status to "failed" if any step breaks)

References:

OpenAI Embeddings Guide
Upstash Vector Documentation
Upstash Vector Metadata Filtering
Operate within your vector namespace only (see TECHNICAL_SETUP) also see Upstash Vector Namespaces Docs
3.2 Retrieval API (/retrieve)
Endpoint: POST /retrieve

Request:

{
  "file_ids": ["uuid1", "uuid2"],
  "query": "What is the main topic?",
  "top_k": 5
}

Response:

{
  "results": [
    {
      "chunk_id": "uuid",
      "file_id": "uuid1",
      "chunk_text": "...",
      "similarity_score": 0.92
    }
  ]
}

Behavior:

Query Upstash Vector with the user's query
Use metadata filtering to retrieve chunks only from the specified file_ids (can be one or multiple)
Retrieve top-k similar chunks across all specified files
Return chunk text with similarity scores and which file each chunk came from
Note: This endpoint is for testing/debugging retrieval independently. In production, the /chat endpoint uses this same logic with file_ids collected from the conversation history
Milestone 4: Dynamic Mode Switching with Tool Calling
4.1 Chat Endpoint - Advanced (/chat)
For Milestone 4, extend the /chat endpoint (defined in 2.1) to support dynamic mode switching:

Extended Behavior:

Fetch or create conversation (if conversation_id not provided, create new conversation)
If file_id is provided in the request:
Fetch the file record to check ingestion_status
Store the file_id with this message in the database
Fetch the conversation history from the database
Context Window Patching (Dynamic based on ingestion status):
Collect all file_ids from messages in the conversation history
Iterate through all messages in the conversation history
For each message with a file_id:
Fetch the current ingestion_status of that file
If ingestion_status = "uploaded":
Download the PDF from S3
Convert the PDF to base64
Patch the context window to include the base64 PDF file block with that message
This message will use inline mode
If ingestion_status = "completed":
Add this file_id to the list of files to search in RAG mode
Messages without file_id are included as-is
Semantic Search (RAG Mode):
If there are any completed files in the conversation:
Use OpenAI tool calling to decide if semantic search is needed
If the tool is called, retrieve top-k chunks from Upstash Vector
Important: Use metadata filtering to only search chunks from the file_ids collected in step 4
Build the context from the retrieved chunks
Call the LLM again with the retrieved context
Store the assistant's response in the database with the appropriate retrieval_mode and retrieved_chunks
Return the response

Reference: OpenAI Function Calling Guide

Tool Definition (for OpenAI tool calling):

{
  "type": "function",
  "function": {
    "name": "semantic_search",
    "description": "Retrieve relevant chunks from the vector database",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "The search query to find relevant chunks"
        },
        "top_k": {
          "type": "integer",
          "description": "Number of top chunks to retrieve (default: 5)",
          "default": 5
        }
      },
      "required": ["query"]
    }
  }
}

Important Implementation Note:

The tool definition above does NOT include a file_ids parameter (the LLM doesn't need to know about file filtering)
When the LLM calls this tool, you extract the query and top_k from the tool call
Before calling your retriever, you manually add the file_ids parameter by collecting all file_ids from the conversation history
Then call your /retrieve endpoint (or retrieval logic) with: {"file_ids": [...], "query": "...", "top_k": 5}
This ensures the LLM focuses on semantic queries while you handle the file filtering logic in your implementation
Database Schema
Note: The schema below is a reference design to give you an idea of the data structure. You are free to design it however you think is best for your implementation. Feel free to add additional fields, indexes, or modify the structure as you see fit—just document your decisions in your DEVELOPMENT_LOG.md.
files Table
id (UUID, primary key)
s3_key (string, e.g., uploads/{file_id}.pdf)
original_text (text, extracted during ingestion - optional, may not be needed if using base64)
ingestion_status (enum: uploaded, completed, failed)
created_at (timestamp)
updated_at (timestamp)
conversations Table
id (UUID, primary key)
created_at (timestamp)

Note: Unlike typical designs, file_id is NOT stored at the conversation level. Files are associated with individual messages.
messages Table
id (UUID, primary key)
conversation_id (UUID, foreign key to conversations)
role (enum: user, assistant)
content (text)
file_id (UUID, foreign key to files, nullable - only set when user includes file in message)
retrieval_mode (enum: inline, rag, null)
retrieved_chunks (JSON, array of retrieved chunks)
created_at (timestamp)

Note: The file_id is stored per message. When a user includes a file_id in their chat request, it's stored with that specific message. Multiple messages in the same conversation can reference different files.
Upstash Vector Metadata (for each vector):
{
  "file_id": "uuid",
  "chunk_id": "uuid",
  "chunk_index": 0,
  "chunk_text": "..."
}

Important: The file_id in the metadata is critical for filtering during retrieval. When performing semantic search in the /chat endpoint, you must use metadata filtering to only retrieve chunks from files that are referenced in the conversation history. This ensures that RAG doesn't retrieve irrelevant context from other files in the database.
Milestones
Milestone 1: File Upload & CRUD APIs
Goal: Build the foundational file upload system with complete CRUD operations for files and conversations. Pure backend engineering—no AI yet.

Deliverables:

Set up FastAPI project with Neon Postgres connection
Implement database schema (files, conversations, messages tables)
Implement /presign endpoint (generate file_id and presigned S3 URL for upload)
Implement /webhook/ingest endpoint (extract file_id from S3 key, create file record with status "uploaded")
Implement /files endpoint (list all files with pagination)
Implement /files/{file_id} endpoint (get file details with presigned download URL)
Test end-to-end: call /presign → upload to S3 → call /webhook/ingest → list files → get file with download URL

Testing:

Manually upload a PDF to S3 using presigned URL
Call /webhook/ingest with S3 event payload (can simulate or use actual Lambda)
List all files and verify metadata
Get specific file and verify presigned download URL works
Verify file status is "uploaded"

Expected Completion: All candidates should complete this.

Estimated Time: 2–3 hours
Milestone 2: Inline Chat with Base64 PDF
Goal: Implement chat functionality that sends PDF files directly to the LLM as base64. Still no RAG—just file-based chat.

Deliverables:

Implement /chat endpoint:
Fetch file record and check status
Download PDF from S3 and convert to base64
Send PDF as base64 file block to OpenAI LLM (inline mode)
Store conversation and messages in DB with file_id
Implement /chats endpoint (list all conversations with pagination)
Implement /chats/{conversation_id} endpoint (get conversation with all messages)
Support conversation history (multi-turn conversations)
Context window patching: include base64 PDF with messages that have file_id
Test end-to-end: upload PDF → chat with it → verify responses use PDF content

Testing:

Upload a PDF
Start a conversation with the PDF
Ask multiple questions in the same conversation
Verify PDF is sent as base64 to LLM (check responses reference PDF content)
List conversations and verify messages are stored correctly
Get specific conversation and verify message history

Expected Completion: All candidates should complete this.

Estimated Time: 2–3 hours
Milestone 3: RAG Pipeline & Retrieval
Goal: Implement the full ingestion pipeline with manual chunking, embeddings, and vector storage. Add retrieval testing endpoint.

Deliverables:

Set up AWS Lambda trigger (or simulate via an HTTP endpoint for testing)
Update /webhook/ingest endpoint to include:
PDF text extraction
Manual chunking logic (fixed-size, semantic, or hybrid)
Embedding generation via OpenAI SDK (text-embedding-3-small)
Upstash Vector indexing with file_id metadata
File status update to "completed"
Implement /retrieve endpoint for testing retrieval with multiple file_ids
Test end-to-end: upload → ingest → retrieve chunks

Testing:

Upload a PDF
Call ingestion (via Lambda or directly)
Use /retrieve to test that chunks are indexed correctly
Verify similarity search returns relevant chunks
Test metadata filtering with multiple file_ids

Expected Completion: Good candidates should reach here.

Estimated Time: 3–4 hours
Milestone 4: Dynamic Mode Switching with Tool Calling
Goal: Integrate OpenAI tool calling to dynamically switch between inline (base64 PDF) and RAG modes in the /chat endpoint based on ingestion status.

Deliverables:

Update /chat endpoint to:
Check ingestion_status for all files in conversation history
If "uploaded": Download PDF, convert to base64, include in context (inline mode)
If "completed": Use OpenAI tool calling for semantic search (RAG mode)
Manually orchestrate the tool calling loop (call → execute → respond)
Collect file_ids from conversation and pass to retriever with metadata filtering
Return metadata about which mode was used
Test end-to-end:
Chat immediately after upload (uses inline base64 PDF mode)
Wait for or trigger ingestion completion
Chat again in same conversation (uses RAG mode with tool calling)
Verify conversation history is maintained and context window is patched correctly

Testing:

Upload a PDF
Chat before ingestion is complete (expect inline mode with base64 PDF)
Trigger or wait for ingestion to complete
Chat after ingestion (expect RAG mode with tool calling)
Verify tool calling logs and responses make sense
Verify the same conversation can switch modes dynamically

Expected Completion: Strong candidates should complete this.

Estimated Time: 3–4 hours
Progression & Expectations
| Milestone | Focus | Difficulty | Must-Have | Submission Expectation | | | - | -- | | | | 1 | Backend Engineering | Medium | Yes | All candidates should complete this. | | 2 | LLM Integration | Medium | Yes | All candidates should complete this. | | 3 | RAG & Embeddings | Medium-High | Ideal | Most candidates should reach here. | | 4 | Tool Calling & Dynamic Logic | High | Nice-to-have | Strong candidates should complete this. |

Grading Philosophy:

Completing all 4 milestones = Excellent
Completing milestones 1, 2, & 3 = Good
Completing milestones 1 & 2 = Acceptable (with clean code and good documentation)
Each milestone should be independent and testable

Progression Notes:

Milestones 1-2: Focus on backend engineering and basic LLM integration
Milestones 3-4: Focus on AI engineering (RAG, embeddings, tool calling)
Key Implementation Notes
Inline Mode (Base64 PDF): When ingestion_status = "uploaded", download the PDF from S3, convert it to base64, and include it as a file block in the OpenAI API call. Use the PDF File Uploads guide as reference for the format.

Context Window Patching: When building the message history for the LLM, dynamically include or exclude the base64 PDF file block based on the current ingestion_status. The file is only included when in "uploaded" state; once "completed", use retrieved chunks instead.

Metadata Filtering for RAG: When performing semantic search, collect all file_ids from messages in the conversation history and use metadata filtering in your Upstash Vector query. This ensures you only retrieve chunks from files that are actually referenced in this conversation, not from other files in the database. This is critical for multi-file support.

Chunking Strategy: You must decide how to chunk the text (fixed size, semantic, sentence-based, etc.). Document your choice and reasoning in your DEVELOPMENT_LOG.md.

Tool Calling: You must manually implement the tool calling loop. Do not use any framework that abstracts this away. See the OpenAI Function Calling Guide for reference.

Error Handling: Handle S3 failures, embedding API timeouts, and Postgres issues gracefully. Set ingestion_status = "failed" when errors occur and log details.

Documentation: Each milestone should have clear sections in your README explaining what you built and how to test it.

