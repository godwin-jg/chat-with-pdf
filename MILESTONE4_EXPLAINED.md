# Milestone 4 Requirements Explained

This document explains **why** each requirement exists and provides concrete examples.

## Overview

Milestone 4 implements **dynamic mode switching** between:
- **Inline mode**: Send PDF as base64 when `ingestion_status = "uploaded"`
- **RAG mode**: Use vector search when `ingestion_status = "completed"`

The key challenge is: **How do we let the LLM decide when to search, while ensuring we only search files from the current conversation?**

---

## 1. Tool Definition WITHOUT `file_ids` Parameter

### What It Means

The tool definition you give to OpenAI **does NOT include `file_ids`** as a parameter. The LLM only sees `query` and `top_k`.

### Example: Tool Definition

```python
# ✅ CORRECT: Tool definition without file_ids
tool_definition = {
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

# ❌ WRONG: Tool definition with file_ids
tool_definition = {
    "type": "function",
    "function": {
        "name": "semantic_search",
        "parameters": {
            "properties": {
                "query": {...},
                "top_k": {...},
                "file_ids": {...}  # ❌ Don't include this!
            }
        }
    }
}
```

### Why This Is Required

**Security & Correctness**: The LLM should NOT decide which files to search. Here's why:

1. **Multi-file conversations**: A conversation might reference multiple files:
   ```
   Message 1: "What's in document1.pdf?" (file_id: abc-123)
   Message 2: "What's in document2.pdf?" (file_id: def-456)
   Message 3: "Compare both documents" (no file_id, but should search BOTH)
   ```

2. **If LLM chooses files**: The LLM might:
   - Search files from OTHER conversations (security issue)
   - Forget which files were mentioned earlier
   - Make mistakes about file IDs

3. **Your code controls files**: You know exactly which files belong to this conversation by looking at the database.

### Real Example

```python
# LLM sees this tool and calls it:
{
    "name": "semantic_search",
    "arguments": '{"query": "What is the main topic?", "top_k": 5}'
}

# Your code then adds file_ids BEFORE executing:
{
    "file_ids": ["abc-123", "def-456"],  # ← You add this from conversation history
    "query": "What is the main topic?",
    "top_k": 5
}
```

---

## 2. Collect `file_ids` from Conversation History

### What It Means

Before executing the tool, you must:
1. Look at ALL messages in the conversation
2. Extract every `file_id` that was mentioned
3. Use those `file_ids` to filter the vector search

### Example: Conversation History

```python
# Conversation with ID: "conv-789"
messages = [
    {
        "role": "user",
        "content": "What's in document1.pdf?",
        "file_id": "abc-123"  # ← File 1
    },
    {
        "role": "assistant",
        "content": "Document1 discusses..."
    },
    {
        "role": "user",
        "content": "What about document2.pdf?",
        "file_id": "def-456"  # ← File 2
    },
    {
        "role": "assistant",
        "content": "Document2 covers..."
    },
    {
        "role": "user",
        "content": "Compare both documents",  # ← No file_id, but should search BOTH
        "file_id": None
    }
]

# Your code collects file_ids:
collected_file_ids = ["abc-123", "def-456"]  # From messages 1 and 3
```

### Why This Is Required

**Context Awareness**: The user might ask questions about files mentioned earlier in the conversation, even if the current message doesn't have a `file_id`.

### Real Example from Your Code

```python
# From chat_handler.py, line 251-277
async def collect_file_ids_from_conversation(
    self, session: AsyncSession, conversation_id: str
) -> Tuple[List[str], bool]:
    """
    Collect all file_ids from conversation and check if any are completed.
    """
    messages = await self.message_dao.get_by_conversation_id(
        session, conversation_id
    )
    
    file_ids = []
    has_completed = False
    
    for msg in messages:
        if msg.file_id:
            file_id_str = str(msg.file_id)
            if file_id_str not in file_ids:
                file_ids.append(file_id_str)
                # Check ingestion status
                file = await self.file_dao.get_by_id(session, file_id_str)
                if file and file.ingestion_status == IngestionStatus.COMPLETED:
                    has_completed = True
    
    return file_ids, has_completed
```

### Example Flow

```
User sends: "Compare both documents" (no file_id)

Your code:
1. Collects file_ids from conversation: ["abc-123", "def-456"]
2. LLM calls tool with: {"query": "compare both documents", "top_k": 5}
3. You execute search with: {
    "file_ids": ["abc-123", "def-456"],  # ← Added by you
    "query": "compare both documents",
    "top_k": 5
}
```

---

## 3. Metadata Filtering in Vector Search

### What It Means

When searching Upstash Vector, you must filter results to **only include chunks from the collected `file_ids`**. This prevents retrieving chunks from other files/conversations.

### Example: Vector Database Contents

```python
# Upstash Vector contains chunks from MANY files:
chunks_in_database = [
    {"file_id": "abc-123", "chunk_text": "Document1 content..."},
    {"file_id": "abc-123", "chunk_text": "More Document1..."},
    {"file_id": "def-456", "chunk_text": "Document2 content..."},
    {"file_id": "xyz-999", "chunk_text": "Different file, not in this conversation..."},  # ← Should be excluded!
    {"file_id": "xyz-999", "chunk_text": "Another chunk from different file..."},  # ← Should be excluded!
]
```

### Without Metadata Filtering (❌ WRONG)

```python
# Search without filtering - retrieves chunks from ALL files
results = upstash_client.query_vectors(
    query_vector=query_vector,
    top_k=5,
    # ❌ No filter - might return chunks from xyz-999!
)
```

### With Metadata Filtering (✅ CORRECT)

```python
# Search with filter - only retrieves chunks from conversation files
filter_str = "file_id = 'abc-123' OR file_id = 'def-456'"

results = upstash_client.query_vectors(
    query_vector=query_vector,
    top_k=5,
    filter=filter_str,  # ✅ Only search in relevant files
)
```

### Why This Is Required

**Security & Accuracy**: Without filtering, you might:
- Retrieve chunks from files in OTHER conversations (privacy issue)
- Get irrelevant context that confuses the LLM
- Mix information from unrelated documents

### Real Example from Your Code

```python
# From chat_handler.py, line 384-396
# Build filter for file_ids
if len(file_ids) == 1:
    filter_str = f"file_id = '{file_ids[0]}'"
else:
    filter_parts = [f"file_id = '{fid}'" for fid in file_ids]
    filter_str = " OR ".join(filter_parts)

# Query Upstash Vector
results = self.upstash_client.query_vectors(
    query_vector=query_vector,
    top_k=top_k,
    filter=filter_str,  # ✅ Metadata filtering
)
```

---

## 4. Manual Tool Calling Loop

### What It Means

You must manually implement the tool calling loop instead of using a framework. The flow is:

1. **First LLM call**: Send messages with tools enabled
2. **Check for tool calls**: If LLM wants to use a tool, extract the tool call
3. **Execute tool**: Run your retrieval logic with collected `file_ids`
4. **Second LLM call**: Send messages + tool results back to LLM
5. **Get final response**: LLM generates answer using retrieved chunks

### Example: Tool Calling Flow

```python
# Step 1: First LLM call with tools enabled
response = openai_client.chat_completion_with_tools(
    messages=message_history,
    tools=[semantic_search_tool],
)

# Response might be:
# {
#   "content": None,  # LLM didn't provide text yet
#   "tool_calls": [
#     {
#       "id": "call_123",
#       "function": {
#         "name": "semantic_search",
#         "arguments": '{"query": "What is the main topic?", "top_k": 5}'
#       }
#     }
#   ]
# }

# Step 2: Check if tool was called
if response.tool_calls:
    # Step 3: Execute tool
    tool_call = response.tool_calls[0]
    args = json.loads(tool_call.function.arguments)
    query = args["query"]
    top_k = args["top_k"]
    
    # Add file_ids (collected from conversation)
    file_ids = ["abc-123", "def-456"]  # From step 2 above
    
    # Execute retrieval
    chunks = retrieve_chunks(
        file_ids=file_ids,  # ← You add this
        query=query,
        top_k=top_k
    )
    
    # Step 4: Build tool response message
    tool_message = {
        "role": "tool",
        "content": json.dumps({"chunks": chunks}),
        "tool_call_id": tool_call.id
    }
    
    # Step 5: Second LLM call with tool results
    message_history.append({
        "role": "assistant",
        "tool_calls": [tool_call]  # Show what LLM requested
    })
    message_history.append(tool_message)  # Show tool results
    
    final_response = openai_client.chat_completion(
        messages=message_history,
        tools=None  # No tools on second call
    )
    
    # final_response contains the answer using retrieved chunks
```

### Why This Is Required

**Control & Flexibility**: Manual implementation gives you:
1. **Control over file_ids**: You can inject `file_ids` between tool call and execution
2. **Error handling**: You can handle tool failures gracefully
3. **Logging**: You can log exactly what happened at each step
4. **No framework dependencies**: As per assignment requirements (no LangChain, etc.)

### Real Example from Your Code

```python
# From chat_handler.py, line 356-452
# First LLM call with tool enabled
response_text, tool_calls = self.openai_client.chat_completion_with_tools(
    messages=message_history,
    tools=tools,
)

# If LLM called the tool, execute it and call LLM again
if tool_calls:
    # Process tool calls
    tool_messages = []
    all_retrieved_chunks = []
    
    for tool_call in tool_calls:
        if tool_call["function"]["name"] == "semantic_search":
            # Parse arguments
            args = json.loads(tool_call["function"]["arguments"])
            query = args.get("query", message)
            top_k = args.get("top_k", 5)
            
            # Generate query embedding
            query_embeddings = self.openai_client.get_embeddings([query])
            query_vector = query_embeddings[0]
            
            # Build filter for file_ids (collected earlier)
            if len(file_ids) == 1:
                filter_str = f"file_id = '{file_ids[0]}'"
            else:
                filter_parts = [f"file_id = '{fid}'" for fid in file_ids]
                filter_str = " OR ".join(filter_parts)
            
            # Query Upstash Vector with metadata filtering
            results = self.upstash_client.query_vectors(
                query_vector=query_vector,
                top_k=top_k,
                filter=filter_str,
            )
            
            # Build tool response
            tool_result = {
                "role": "tool",
                "content": json.dumps({"chunks": chunks}),
                "tool_call_id": tool_call["id"]
            }
            tool_messages.append(tool_result)
    
    # Add assistant message with tool_calls
    message_history.append({
        "role": "assistant",
        "tool_calls": [...]
    })
    
    # Add tool results
    message_history.extend(tool_messages)
    
    # Second LLM call with tool results
    final_response = self.openai_client.chat_completion(
        messages=message_history,
        tools=None,
    )
```

---

## Why All Four Requirements Work Together

Here's the complete flow showing how all four requirements connect:

```
1. User sends message: "Compare both documents" (no file_id)

2. Your code collects file_ids from conversation history:
   → file_ids = ["abc-123", "def-456"]

3. You build message history and call LLM with tool definition:
   → Tool definition: {name: "semantic_search", parameters: {query, top_k}}
   → ❌ NO file_ids in tool definition (Requirement 1)

4. LLM decides to call tool:
   → Tool call: {"query": "compare both documents", "top_k": 5}

5. Your code executes tool:
   → Adds file_ids: {"file_ids": ["abc-123", "def-456"], ...} (Requirement 2)
   → Searches with metadata filter: "file_id = 'abc-123' OR file_id = 'def-456'" (Requirement 3)
   → Retrieves chunks only from those files

6. Your code manually orchestrates second LLM call:
   → Sends tool results back to LLM (Requirement 4)
   → LLM generates final answer using retrieved chunks
```

---

## Summary

| Requirement | Purpose | Why It's Needed |
|------------|---------|----------------|
| **1. Tool without file_ids** | LLM doesn't choose files | Security: Prevents searching wrong files |
| **2. Collect file_ids** | Get files from conversation | Context: User might reference earlier files |
| **3. Metadata filtering** | Filter vector search results | Security: Only search relevant files |
| **4. Manual tool loop** | Control tool execution | Flexibility: Inject file_ids between call and execution |

All four work together to ensure:
- ✅ LLM focuses on **what to search** (query)
- ✅ Your code controls **where to search** (file_ids)
- ✅ Results are **secure and accurate** (metadata filtering)
- ✅ Process is **transparent and debuggable** (manual loop)

