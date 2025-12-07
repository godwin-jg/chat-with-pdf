# Development Log

This document tracks the development process, architecture decisions, and key learnings during the implementation of the Chat with PDF system.

## Table of Contents

- [Architecture Decisions](#architecture-decisions)
- [Prompting Workflow](#prompting-workflow)
- [Key Learnings](#key-learnings)
- [Challenges and Solutions](#challenges-and-solutions)

## Architecture Decisions

### 1. Manual Chunking Implementation

**Decision**: Implemented custom chunking logic instead of using high-level frameworks (LangChain, LlamaIndex, etc.).

**Rationale**:
- **Precise Control**: Need exact control over token windows (512 tokens) and overlap (102 tokens) for optimal embedding model compatibility
- **No External Dependencies**: Avoids adding heavy dependencies and maintains full control over chunking behavior
- **Word Boundary Awareness**: Custom implementation respects word boundaries and sentence endings, improving semantic coherence
- **Assignment Requirement**: Explicitly required to implement chunking manually

**Implementation**:
- Location: `core/chunker/text_chunker.py`
- Algorithm: Sliding window with configurable overlap
- Token Estimation: ~4 characters per token (approximation)
- Boundary Detection: Attempts to break at spaces, newlines, or punctuation

**Trade-offs**:
- ✅ Full control over chunking behavior
- ✅ No framework dependencies
- ✅ Configurable parameters
- ❌ More code to maintain
- ❌ Manual token counting (approximation)

---

### 2. Hybrid State Machine (Inline ↔ RAG)

**Decision**: Implemented a state machine that dynamically switches between inline (Base64) and RAG modes based on file ingestion status.

**Rationale**:
- **Immediate Availability**: Users can chat with PDFs immediately after upload without waiting for ingestion
- **Optimized Retrieval**: Once ingestion completes, system switches to RAG for more efficient retrieval
- **Seamless Transition**: Same conversation can use both modes as ingestion status changes
- **Fallback Support**: If ingestion fails, system can still use inline mode

**Implementation**:
- Location: `services/chat_service/chat_handler.py`
- State Detection: Checks `file.ingestion_status` for each file in conversation
- Mode Selection:
  - `"uploaded"` → Inline mode (PDF → images → Vision API)
  - `"completed"` → RAG mode (Tool calling → Vector search → Chunks)
- Context Patching: Dynamically patches context window based on mode

**Trade-offs**:
- ✅ Best of both worlds (immediate + optimized)
- ✅ Graceful degradation
- ✅ Transparent to user
- ❌ More complex logic
- ❌ Requires careful state management

---

### 3. Message-Level File Association

**Decision**: Store `file_id` at the message level, not the conversation level.

**Rationale**:
- **Multi-file Support**: Enables referencing multiple PDFs in a single conversation
- **Flexible Context**: Different messages can reference different files
- **Dynamic Context Window**: System can patch context based on which files are referenced in which messages
- **Scalability**: More flexible than conversation-level association

**Implementation**:
- Schema: `messages.file_id` (nullable UUID, foreign key to `files.id`)
- Behavior: Each message can optionally reference a file
- Context Building: System iterates through messages and patches context for messages with `file_id`

**Trade-offs**:
- ✅ Maximum flexibility
- ✅ Multi-file conversations
- ✅ Message-level context control
- ❌ More complex context building logic
- ❌ Requires careful file_id collection

---

### 4. Database Schema Design

**Decision**: Three-table design (`files`, `conversations`, `messages`) with message-level file associations.

**Rationale**:
- **Separation of Concerns**: Files, conversations, and messages are independent entities
- **Flexibility**: Messages can reference files without coupling conversations to files
- **Scalability**: Each table can be indexed and queried independently
- **Data Integrity**: Foreign keys ensure referential integrity

**Schema Choices**:

1. **Files Table**:
   - UUID primary key (matches S3 key pattern)
   - `ingestion_status` enum (uploaded, completed, failed)
   - `s3_key` unique index for fast lookup
   - No original text storage (stored in vector DB metadata)

2. **Conversations Table**:
   - Minimal structure (ID + timestamps)
   - No file association (files are message-level)
   - Enables multi-file conversations

3. **Messages Table**:
   - Message-level `file_id` (nullable)
   - `retrieval_mode` tracking (inline/rag)
   - `retrieved_chunks` JSON storage for debugging
   - Cascade deletes for conversation cleanup

**Trade-offs**:
- ✅ Clean separation of concerns
- ✅ Flexible associations
- ✅ Scalable design
- ❌ More complex queries (joins required)
- ❌ More tables to manage

---

### 5. OpenAI Tool Calling for RAG

**Decision**: Use OpenAI function calling to let the LLM decide when to retrieve chunks.

**Rationale**:
- **Intelligent Retrieval**: LLM decides when semantic search is needed based on context
- **Efficiency**: Only retrieves when necessary, reducing unnecessary vector searches
- **Natural Integration**: Tool calling is the standard way to integrate external functions with LLM
- **Flexibility**: LLM can formulate the search query based on conversation context

**Implementation**:
- Tool Definition: `semantic_search(query: str, top_k: int)`
- Tool Execution: Manual orchestration (call → execute → respond)
- Metadata Filtering: File IDs are collected from conversation and added to filter (not exposed to LLM)
- Two-step Process: First call with tool, second call with retrieved chunks

**Trade-offs**:
- ✅ Intelligent retrieval decisions
- ✅ LLM-formulated queries
- ✅ Standard OpenAI pattern
- ❌ More complex orchestration
- ❌ Requires manual tool calling loop

---

### 6. Vision API for Inline Mode

**Decision**: Convert PDF pages to images and send via Vision API instead of base64 PDF files.

**Rationale**:
- **Model Compatibility**: Some models (e.g., `gpt-4.1-mini`) don't support PDF files directly
- **Wider Model Support**: Vision API supports images (PNG/JPEG) across more models
- **Better Quality**: Image conversion preserves visual layout and formatting
- **Fallback Support**: Can fall back to text extraction if image conversion fails

**Implementation**:
- Library: PyMuPDF (`pymupdf`) for PDF → image conversion
- Format: PNG base64 encoded images
- Limit: Max 10 pages per PDF (configurable)
- Fallback: Text extraction if image conversion fails

**Trade-offs**:
- ✅ Works with more models
- ✅ Preserves visual layout
- ✅ Better quality than text-only
- ❌ Larger payload (images vs text)
- ❌ Requires image conversion library

---

### 7. Background Task for Ingestion

**Decision**: Process file ingestion asynchronously in a background task.

**Rationale**:
- **Fast Response**: Webhook returns immediately, doesn't block on ingestion
- **User Experience**: Users can start chatting immediately (inline mode)
- **Error Handling**: Background task can handle errors without blocking webhook
- **Scalability**: Can process multiple files concurrently

**Implementation**:
- Framework: FastAPI `BackgroundTasks`
- Process: Download → Extract → Chunk → Embed → Upsert → Update status
- Error Handling: Updates status to "failed" on error, logs details
- Transaction Management: Uses separate database session for background task

**Trade-offs**:
- ✅ Fast webhook response
- ✅ Non-blocking
- ✅ Better user experience
- ❌ More complex error handling
- ❌ Requires separate session management

---

### 8. Metadata Filtering in Vector Search

**Decision**: Use metadata filtering to only retrieve chunks from files referenced in conversation.

**Rationale**:
- **Precision**: Prevents retrieving irrelevant chunks from other files
- **Multi-file Support**: Can search across multiple files while excluding others
- **Context Relevance**: Only retrieves chunks from files actually referenced in conversation
- **Performance**: Reduces search space, improving query performance

**Implementation**:
- Filter Format: `"file_id = 'uuid1' OR file_id = 'uuid2'"`
- Collection: Gathers all `file_id`s from conversation messages
- Application: Applied to Upstash Vector query
- Single vs Multiple: Handles both single and multiple file scenarios

**Trade-offs**:
- ✅ Precise retrieval
- ✅ Multi-file support
- ✅ Better performance
- ❌ Requires file_id collection logic
- ❌ More complex filter construction

---

## Prompting Workflow

> **Note**: This section is a placeholder for you to document your specific prompting workflow and AI-assisted development process.

### Initial Setup and Planning

[Document your initial prompts and how you structured the project]

### Iterative Development

[Document how you used prompts to build each milestone]

### Debugging and Refinement

[Document prompts used for debugging and optimization]

### Key Prompts That Shaped the Architecture

[Document specific prompts that led to important architectural decisions]

---

## Key Learnings

### Technical Learnings

1. **Manual Chunking**: Implementing chunking manually gave us precise control but required careful token counting and boundary detection.

2. **State Machine Complexity**: The hybrid mode switching added complexity but provided significant value in user experience.

3. **Tool Calling Orchestration**: Manual tool calling loop required careful message history management and error handling.

4. **Vision API Limitations**: Some models don't support PDF files directly, requiring image conversion as a workaround.

5. **Metadata Filtering**: Upstash Vector metadata filtering is critical for multi-file conversations to avoid retrieving irrelevant chunks.

### Architecture Learnings

1. **Message-Level Associations**: Storing file associations at the message level provided maximum flexibility but required more complex context building.

2. **Background Tasks**: Async ingestion improved user experience but required careful session management and error handling.

3. **Layered Architecture**: Clear separation of routes → services → DAOs → core made the codebase maintainable and testable.

4. **Type Safety**: Using Pydantic for all API I/O provided excellent validation and documentation.

### Process Learnings

1. **Incremental Development**: Building in milestones (upload → inline → RAG → hybrid) made the system testable at each stage.

2. **Error Handling**: Comprehensive error handling and status tracking made debugging much easier.

3. **Documentation**: Writing documentation alongside code helped clarify design decisions.

---

## Challenges and Solutions

### Challenge 1: PDF Format Support

**Problem**: Some OpenAI models don't support PDF files directly via the file API.

**Solution**: Convert PDF pages to images using PyMuPDF and send via Vision API. Fallback to text extraction if image conversion fails.

**Result**: Works with a wider range of models while preserving visual layout.

---

### Challenge 2: Dynamic Mode Switching

**Problem**: Need to switch between inline and RAG modes based on ingestion status, potentially within the same conversation.

**Solution**: Implemented state machine that checks ingestion status for each file in conversation history and patches context accordingly.

**Result**: Seamless transition between modes, transparent to the user.

---

### Challenge 3: Multi-file Context Building

**Problem**: Need to build context window with multiple files, some in inline mode, some in RAG mode.

**Solution**: Iterate through conversation messages, check each file's ingestion status, and patch context dynamically. Collect all completed file_ids for vector search filtering.

**Result**: Supports complex multi-file conversations with mixed ingestion states.

---

### Challenge 4: Tool Calling Orchestration

**Problem**: Manual tool calling requires careful message history management and two-step LLM calls.

**Solution**: Implemented explicit tool calling loop: first call with tool enabled, execute tool if called, add tool results to history, second call with retrieved context.

**Result**: Reliable tool calling with proper context management.

---

### Challenge 5: Metadata Filtering for Multi-file

**Problem**: Need to search only chunks from files referenced in conversation, not all files in database.

**Solution**: Collect all file_ids from conversation messages, build metadata filter string, apply to Upstash Vector query.

**Result**: Precise retrieval that only includes relevant file chunks.

---

## Future Improvements

1. **Chunking Strategy**: Could experiment with semantic chunking (sentence-based, paragraph-based) for better semantic coherence.

2. **Caching**: Could cache embeddings or retrieved chunks to reduce API calls.

3. **Retry Logic**: Could implement retry logic for failed ingestion tasks.

4. **Monitoring**: Could add metrics and monitoring for ingestion success rates and retrieval quality.

5. **Optimization**: Could optimize chunk size and overlap based on retrieval quality metrics.

---

## Conclusion

This development log documents the key architectural decisions and learnings from building the Chat with PDF system. The hybrid approach, manual chunking, and message-level file associations provide a flexible and scalable foundation for PDF-based chat interactions.

