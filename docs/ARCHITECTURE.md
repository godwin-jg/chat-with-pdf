# Architecture Documentation

This document explains the architectural decisions and design patterns used in the Chat with PDF system.

## Table of Contents

- [Manual Chunking Strategy](#manual-chunking-strategy)
- [Hybrid Logic (State Machine)](#hybrid-logic-state-machine)
- [Database Schema Design](#database-schema-design)
- [System Architecture](#system-architecture)

## Manual Chunking Strategy

### Why Manual Chunking?

I implemented a **custom chunking solution** instead of using high-level frameworks (LangChain, LlamaIndex, etc.) for the following reasons:

1. **Precise Token Window Control**: Manual chunking allows us to control exactly how many tokens are in each chunk, ensuring optimal fit for embedding models and vector database constraints.

2. **Configurable Overlap**: I can fine-tune the overlap between chunks (default: 102 tokens, ~20% of 512-token chunks) to maintain context continuity while avoiding excessive redundancy.

3. **Word Boundary Awareness**: My implementation respects word boundaries and sentence endings, preventing chunks from breaking mid-word or mid-sentence, which improves semantic coherence.

4. **No External Dependencies**: By implementing chunking manually, we avoid adding heavy dependencies and maintain full control over the chunking logic.

### Implementation Details

**Location**: `core/chunker/text_chunker.py`

**Key Features:**
- **Token-based sizing**: Uses approximate token counting (4 characters per token)
- **Sliding window overlap**: Each chunk overlaps with the previous chunk by a configurable amount
- **Word boundary detection**: Attempts to break at spaces, newlines, or punctuation marks
- **Configurable parameters**:
  - `chunk_size`: Target chunk size in tokens (default: 512)
  - `overlap`: Overlap size in tokens (default: 102, ~20% of chunk_size)

**Example:**
```python
chunks = chunk_text(
    text="Long document text...",
    chunk_size=512,  # 512 tokens per chunk
    overlap=102      # 102 tokens overlap between chunks
)
```

**Why 512 tokens?**
- Optimal size for `text-embedding-3-small` (supports up to 8191 tokens)
- Balances context preservation with retrieval precision
- Common standard in RAG systems

**Why 102 token overlap?**
- ~20% overlap ensures context continuity
- Prevents important information from being split across chunk boundaries
- Reduces risk of losing semantic context at chunk edges

## Hybrid Logic (State Machine)

### Overview

The system implements a **state machine** that dynamically switches between two retrieval modes based on file ingestion status:

1. **Inline Mode** (`ingestion_status = "uploaded"`): PDF sent as Base64 images via Vision API
2. **RAG Mode** (`ingestion_status = "completed"`): Semantic search with retrieved chunks

### State Machine Flow

```
┌─────────────────┐
│  File Uploaded  │
│  (status:       │
│   "uploaded")    │
└────────┬────────┘
         │
         │ User chats
         ▼
┌─────────────────┐
│  Inline Mode    │
│  - Download PDF │
│  - Convert to   │
│    images       │
│  - Send via     │
│    Vision API   │
└─────────────────┘
         │
         │ Background ingestion completes
         ▼
┌─────────────────┐
│  Ingestion      │
│  Complete       │
│  (status:       │
│   "completed")  │
└────────┬────────┘
         │
         │ User chats again
         ▼
┌─────────────────┐
│  RAG Mode       │
│  - Tool calling │
│  - Vector search│
│  - Retrieve     │
│    chunks       │
└─────────────────┘
```

### Implementation Details

**Location**: `services/chat_service/chat_handler.py`

**Key Methods:**
- `build_message_history()`: Builds message history with context patching based on ingestion status
- `collect_file_ids_from_conversation()`: Collects all file_ids from conversation and checks completion status
- `process_chat()`: Main orchestration method that switches between modes

**Decision Logic:**

```python
# Pseudo-code
if file.ingestion_status == "uploaded":
    # Inline Mode
    pdf_bytes = download_from_s3(file.s3_key)
    images = convert_pdf_to_images(pdf_bytes)
    send_to_llm_with_images(message, images)
    
elif file.ingestion_status == "completed":
    # RAG Mode
    if has_completed_files:
        enable_tool_calling()
        if llm_calls_tool:
            query = extract_query_from_tool_call()
            chunks = vector_search(query, file_ids)
            send_to_llm_with_chunks(message, chunks)
```

### Why Hybrid Approach?

1. **Immediate Availability**: Users can chat with PDFs immediately after upload, without waiting for ingestion
2. **Optimized Retrieval**: Once ingestion completes, the system switches to RAG mode for more efficient and precise retrieval
3. **Seamless Transition**: The same conversation can use both modes as ingestion status changes
4. **Fallback Support**: If ingestion fails, the system can still use inline mode

### Context Window Patching

The system dynamically patches the context window based on ingestion status:

- **For "uploaded" files**: PDF is downloaded, converted to images, and attached to the message via Vision API
- **For "completed" files**: Only the text message is sent; retrieved chunks are added separately via tool calling
- **For messages without files**: Sent as-is

This ensures that:
- The LLM always has the most appropriate context
- Token usage is optimized (no redundant base64 data when RAG is available)
- The system gracefully handles mixed states (some files uploaded, some completed)

## Database Schema Design

### Schema Overview

The database uses three main tables: `files`, `conversations`, and `messages`.

### Files Table

**Purpose**: Store PDF file metadata and ingestion status.

**Schema:**
```sql
CREATE TABLE files (
    id UUID PRIMARY KEY,
    s3_key VARCHAR UNIQUE NOT NULL,
    ingestion_status ENUM('uploaded', 'completed', 'failed') NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

**Key Design Decisions:**

1. **UUID Primary Key**: Uses UUID to match the `file_id` embedded in S3 keys, enabling easy extraction and lookup.

2. **Ingestion Status Enum**: Tracks file processing state:
   - `uploaded`: File is in S3 but not yet processed
   - `completed`: File has been chunked, embedded, and indexed
   - `failed`: Ingestion failed (for debugging and retry logic)

3. **S3 Key as Unique Index**: Ensures one database record per S3 object, preventing duplicates.

4. **No Original Text Storage**: We don't store the extracted text in the database because:
   - Text can be large and would bloat the database
   - We can always re-extract from S3 if needed
   - Vector database stores chunk text in metadata

### Conversations Table

**Purpose**: Store conversation records (minimal structure).

**Schema:**
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

**Key Design Decisions:**

1. **No File Association at Conversation Level**: Unlike typical designs, we don't store `file_id` at the conversation level. This enables:
   - **Multi-file conversations**: A single conversation can reference multiple PDFs
   - **Flexible file association**: Files are associated with individual messages, not entire conversations
   - **Dynamic context**: Different messages in the same conversation can reference different files

2. **Minimal Structure**: Only stores ID and timestamps. All conversation data is in the `messages` table.

### Messages Table

**Purpose**: Store individual chat messages with file associations and retrieval metadata.

**Schema:**
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role ENUM('user', 'assistant') NOT NULL,
    content TEXT NOT NULL,
    file_id UUID REFERENCES files(id) ON DELETE SET NULL,
    retrieval_mode ENUM('inline', 'rag') NULL,
    retrieved_chunks JSON NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

**Key Design Decisions:**

1. **Message-level File Association**: `file_id` is stored per message, not per conversation. This enables:
   - Multiple files in one conversation
   - Different files referenced in different messages
   - Flexible context window patching

2. **Retrieval Mode Tracking**: Stores which mode was used (`inline` or `rag`) for each assistant response, enabling:
   - Debugging and analysis
   - Response quality comparison
   - System behavior verification

3. **Retrieved Chunks Storage**: Stores retrieved chunks as JSON for:
   - Debugging and transparency
   - Response quality analysis
   - User visibility into what context was used

4. **Cascade Deletes**: Messages are deleted when a conversation is deleted, but file references are set to NULL (not deleted) to preserve file records.

5. **Nullable File ID**: Not all messages reference files, so `file_id` is nullable.

### Relationships

```
conversations (1) ──< (many) messages
files (1) ──< (many) messages
```

**Why this design?**

- **Separation of Concerns**: Files, conversations, and messages are independent entities
- **Flexibility**: Messages can reference files without coupling conversations to files
- **Scalability**: Each table can be indexed and queried independently
- **Data Integrity**: Foreign keys ensure referential integrity while allowing flexible associations

### Indexes

- `files.s3_key`: Unique index for fast lookup
- `files.ingestion_status`: Index for filtering by status
- `messages.conversation_id`: Index for fast conversation retrieval
- `messages.file_id`: Index for file-based queries

## System Architecture

### Layered Architecture

The system follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────┐
│         API Layer (Routes)          │
│  - Request validation                │
│  - Response formatting               │
│  - HTTP status codes                 │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Service Layer (Business Logic) │
│  - Chat orchestration               │
│  - File ingestion                   │
│  - Context patching                 │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         DAO Layer (Data Access)     │
│  - Database queries                  │
│  - CRUD operations                   │
│  - Transaction management            │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Core Layer (Integrations)      │
│  - AWS S3 client                     │
│  - OpenAI client                     │
│  - Upstash Vector client             │
│  - PDF parser                        │
│  - Text chunker                      │
└─────────────────────────────────────┘
```

### Dependency Flow

**Routes → Services → DAOs → Models**

- Routes handle HTTP concerns (validation, status codes)
- Services contain business logic (orchestration, state management)
- DAOs handle data access (queries, transactions)
- Core provides reusable integrations

### Async/Await Pattern

All I/O operations use **async/await** for:
- Non-blocking database queries
- Concurrent API calls
- Efficient resource utilization

### Error Handling

- **Service Layer**: Handles business logic errors and converts them to appropriate exceptions
- **Route Layer**: Catches exceptions and returns appropriate HTTP status codes
- **Background Tasks**: Log errors and update file status to "failed" on ingestion errors

### Configuration Management

Uses **Pydantic Settings** for:
- Type-safe configuration
- Environment variable loading
- Validation and defaults
- Centralized configuration in `config.py`

---

## Summary

This architecture prioritizes:

1. **Control**: Manual chunking and custom logic for precise behavior
2. **Flexibility**: Hybrid mode switching and message-level file associations
3. **Scalability**: Layered architecture and async operations
4. **Maintainability**: Clear separation of concerns and comprehensive documentation

The design enables the system to handle complex scenarios (multi-file conversations, dynamic mode switching) while maintaining code clarity and testability.

