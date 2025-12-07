# Development Log

This document tracks my development process, architecture decisions, and key learnings during the implementation of the Chat with PDF system.

## Table of Contents

- [Architecture Decisions](#architecture-decisions)
- [Prompting Workflow](#prompting-workflow)
- [Key Learnings](#key-learnings)
- [Challenges and Solutions](#challenges-and-solutions)

## Architecture Decisions

### 1. Manual Chunking Implementation

**Decision**: I implemented custom chunking logic instead of using high-level frameworks (LangChain, LlamaIndex, etc.).

**Rationale**:
- **Precise Control**: I needed exact control over token windows (512 tokens) and overlap (102 tokens) to ensure optimal compatibility with the embedding model.
- **No External Dependencies**: This avoids adding heavy dependencies and keeps the codebase lightweight.
- **Word Boundary Awareness**: My custom implementation respects word boundaries and sentence endings, which improves semantic coherence compared to naive character splitting.
- **Assignment Requirement**: The assignment explicitly required manual implementation of the chunking logic.

**Implementation**:
- **Location**: `core/chunker/text_chunker.py`
- **Algorithm**: Sliding window with configurable overlap.
- **Token Estimation**: Using a heuristic of ~4 characters per token.
- **Boundary Detection**: It attempts to break at natural delimiters like spaces, newlines, or punctuation.

**Trade-offs**:
- ✅ Full control over behavior
- ✅ Zero framework overhead
- ❌ More code to maintain personally
- ❌ Token counting is an approximation rather than exact tokenizer math

---

### 2. Hybrid State Machine (Inline ↔ RAG)

**Decision**: I implemented a state machine that dynamically switches between "Inline" (Base64/Vision) and "RAG" modes based on the file's ingestion status.

**Rationale**:
- **Immediate Availability**: Users shouldn't have to wait. They can chat with PDFs immediately after upload (using the Vision API) while the heavy lifting happens in the background.
- **Optimized Retrieval**: Once ingestion completes, the system automatically switches to RAG for efficient, cost-effective retrieval.
- **Seamless Transition**: The same conversation ID can handle both modes.

**Implementation**:
- **Location**: `services/chat_service/chat_handler.py`
- **State Detection**: Checks `file.ingestion_status`.
- **Mode Selection**:
  - `uploaded` → Inline mode (PDF → images → Vision API)
  - `completed` → RAG mode (Tool calling → Vector search → Chunks)

**Trade-offs**:
- ✅ Best user experience (zero wait time)
- ✅ Graceful degradation if ingestion fails
- ❌ Significantly higher logic complexity in the chat handler

---

### 3. Message-Level File Association

**Decision**: I chose to store the `file_id` at the *message* level, rather than at the conversation level.

**Rationale**:
- **Multi-file Support**: This allows a user to reference File A in one turn and File B in the next within the same chat.
- **Dynamic Context Window**: The system can build context dynamically based on which files are relevant to the current messages.

**Implementation**:
- **Schema**: `messages.file_id` is a nullable UUID foreign key.
- **Context Building**: I iterate through the message history to determine which file contexts need to be pulled.

**Trade-offs**:
- ✅ Maximum flexibility for the user
- ❌ Context building logic is more expensive (requires joining tables)

---

### 4. Database Schema Design

**Decision**: A three-table design (`files`, `conversations`, `messages`) using SQLModel.

**Rationale**:
- **Separation of Concerns**: Keeps metadata separate from chat history.
- **Data Integrity**: Enforced via foreign keys.

**Schema Choices**:
1.  **Files Table**: UUID primary keys (matching S3), status enums.
2.  **Conversations Table**: Minimal structure, acts as a container.
3.  **Messages Table**: Stores content, role, and the specific `file_id` associated with that turn.

---

### 5. OpenAI Tool Calling for RAG

**Decision**: I used OpenAI function calling to let the LLM decide *when* to retrieve chunks.

**Rationale**:
- **Intelligent Retrieval**: Instead of forcing a vector search on every query (which adds noise), the LLM decides if it needs external information.
- **Natural Integration**: It fits the standard OpenAI pattern for RAG.

**Implementation**:
- **Tool Definition**: `semantic_search(query: str, top_k: int)`
- **Orchestration**: A manual loop: Call LLM → Check for Tool Call → Execute Tool → Feed Result back to LLM → Get Final Answer.

---

### 6. Vision API for Inline Mode

**Decision**: I convert PDF pages to images using PyMuPDF and send them to the model via the Vision API.

**Rationale**:
- **Model Compatibility**: Not all OpenAI models accept direct PDF file uploads via the API, but they generally handle images well.
- **Visual Layout**: Images preserve tables and charts better than raw text extraction during the "inline" phase.

---

### 7. Background Task for Ingestion

**Decision**: File ingestion happens asynchronously using FastAPI `BackgroundTasks`.

**Rationale**:
- **Responsiveness**: The webhook returns `202 Accepted` immediately.
- **Reliability**: If ingestion fails, it logs the error to the database without crashing the user's request.

---

## Prompting Workflow

My development process heavily utilized iterative prompting to accelerate boilerplate generation while reserving architectural control for manual refinement.

### Initial Setup and Planning

I began by establishing the persona and constraints for the project to ensure all generated code adhered to the assignment guidelines.

* **Persona Prompt**: *"Act as a Senior Python Backend Engineer. We are building a FastAPI-based RAG application. Strict constraints: Use SQLModel, Pydantic v2, and Upstash Vector. No high-level RAG frameworks (LangChain/LlamaIndex) are allowed for the core logic."*
* **Scaffolding**: I provided the file structure (Clean Architecture) and asked for the initial `main.py` and `database.py` configurations to ensure the environment variables and async sessions were set up correctly from the start.

### Iterative Development

I adopted a "Component-First" approach, prompting for specific services rather than the entire application at once.

1.  **Database Layer**: *"Create a SQLModel schema for `Files`, `Conversations`, and `Messages`. Requirement: Files must be associated with specific messages, not just the conversation, to allow multi-file chats."*
2.  **Ingestion Service**: *"Write a Python service that takes a PDF byte stream, extracts text using PyMuPDF, and prepares it for chunking. Include error handling for corrupt files."*
3.  **Chat Logic**: *"Implement a function `process_message` that decides whether to use RAG or Inline mode based on a file status flag. If the status is 'completed', return a tool call definition. If 'uploaded', return a prompt with Base64 image attachments."*

### Debugging and Refinement

When complex bugs arose, I used "Root Cause Analysis" prompting:

* **Circular Imports**: When the `models/` folder grew complex, I pasted the stack trace and asked: *"Refactor these Pydantic models to resolve Circular Import errors using `TYPE_CHECKING` and `ForwardRef` patterns."*
* **Context Patching**: When the chat history wasn't retaining context, I prompted: *"Analyze this `build_context` function. It needs to iterate through past messages and re-inject chunk data if it exists in the message metadata. Suggest a logic flow."*

### Key Prompts That Shaped the Architecture

Two specific prompts were critical in defining the unique architecture of this system:

1.  **The Manual Chunker**:
    > *"Write a pure Python text chunker class. Constraints: Sliding window algorithm. Window size 512 tokens, overlap 100 tokens. Do not import any AI libraries. Use a heuristic of 4 chars = 1 token. Ensure chunks do not split words in the middle."*
    (This resulted in the `TextChunker` core component).

2.  **The Hybrid State Machine**:
    > *"I need a strategy to allow users to chat with a PDF immediately while it indexes in the background. Propose a flow where the API checks the database status and swaps the retrieval strategy dynamically per request."*
    (This led to the `uploaded` vs `completed` status check in `chat_service`).

---

## Key Learnings

### Technical Learnings

1.  **Manual Chunking**: Implementing chunking manually gave me a much deeper appreciation for how embedding models view text.
2.  **State Machine Complexity**: The hybrid mode switching added significant complexity, but it was worth it for the UX.
3.  **Vision API Limitations**: I learned that sending PDFs as images is a viable (and sometimes superior) alternative to text extraction for immediate, low-latency "chatting."

### Architecture Learnings

1.  **Layered Architecture**: Strictly separating routes, services, and DAOs made testing individual components (like the chunker) much easier.
2.  **Type Safety**: Using Pydantic for everything (I/O) caught so many bugs before I even ran the code.

---

## Challenges and Solutions

### Challenge 1: PDF Format Support
**Problem**: Some OpenAI models don't support PDF files directly via the file API.
**Solution**: I implemented the `PyMuPDF` to Image conversion pipeline. This acts as a bridge, allowing any visual model to "read" the PDF.

### Challenge 2: Dynamic Mode Switching
**Problem**: Switching between Inline and RAG modes within the same conversation was breaking context.
**Solution**: I created a context builder that iterates through history. If a previous message used RAG, we inject the *text of the chunks* into the context window so the model retains the "memory" of that retrieval.

### Challenge 3: Metadata Filtering
**Problem**: The vector search was returning chunks from *other* uploaded files.
**Solution**: I implemented strict metadata filtering in Upstash (`filter="file_id = '...'"`), ensuring queries are scoped only to the relevant documents.