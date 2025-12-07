# Comprehensive Testing Guide

This document outlines the testing procedures I established to verify the requirements of the assignment. It covers the hybrid architecture (Inline vs. RAG), multi-file context switching, and state persistence.

## Prerequisites

- **Server**: Ensure the FastAPI server is running (`uvicorn main:app --reload`).
- **Test Files**: For the RAG scenarios, I am using two specific files that have already been ingested into the system:
  - **File A** (`minecraft.pdf`): `9f2d89bf-18b4-4bf4-a55c-3475db992210`
  - **File B** (`SamplePDF.pdf`): `fc952142-4b8a-401f-80f1-ddf5c11e90af`

---

## Test Scenarios

### 1. Single File Inline Mode (Fresh Upload)

**Objective**: Verify that the system defaults to "Inline Mode" (using Vision API/Base64) when a file is uploaded but not yet ingested.

*Note: Since the prerequisite files are already "completed", I must upload a new file to test this specific state.*

**Steps:**
1.  **Upload a new PDF** via the `/presign` and `/upload` flow (or use `test_endpoints.sh`).
2.  **Verify Status**: Ensure `ingestion_status` is `"uploaded"`.((you can use this `file_id: 500107f2-4445-4be2-9a5e-aca7144780d2` which is manually set as status `uploaded`for sample testing))
3.  **Chat Request**:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is this document about?",
    "file_id": "YOUR_NEW_FILE_ID"
  }'
Verification:

✅ retrieval_mode must be "inline".

✅ retrieved_chunks must be empty [].

✅ Response should describe the document (proving the Vision API received the images).

2. Single File RAG Mode
Objective: Verify that the system automatically switches to "RAG Mode" (Vector Search) for completed files.

Request:

Bash

curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the main theme of this document?",
    "file_id": "9f2d89bf-18b4-4bf4-a55c-3475db992210"
  }'
Verification:

✅ retrieval_mode must be "rag".

✅ retrieved_chunks must contain data with similarity scores.

✅ Server logs should show Executing semantic_search.

3. Multi-File RAG Mode (Core Requirement)
Objective: Verify that the system correctly aggregates context from multiple files within a single conversation history.

Step 1: Start Conversation with File A

Bash

# This returns a conversation_id. Save it.
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do you craft items?",
    "file_id": "9f2d89bf-18b4-4bf4-a55c-3475db992210"
  }'
Step 2: Add File B to the Same Conversation

Bash

# Replace CONVERSATION_ID below
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Compare the previous crafting info with this document",
    "conversation_id": "INSERT_CONVERSATION_ID_HERE",
    "file_id": "fc952142-4b8a-401f-80f1-ddf5c11e90af"
  }'
Verification:

✅ The final response should synthesize information from both PDFs.

✅ retrieved_chunks in the final response should list chunks from both 9f2d... and fc95....

✅ The system correctly identified that the context window required both files.

4. Direct Retrieval Endpoint
Objective: Verify the vector search logic works independently of the LLM and properly handles list filtering.

Request:

Bash

curl -X POST "http://localhost:8000/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mining and crafting",
    "file_ids": [
      "9f2d89bf-18b4-4bf4-a55c-3475db992210",
      "fc952142-4b8a-401f-80f1-ddf5c11e90af"
    ],
    "top_k": 5
  }'
Verification:

✅ The results list should contain mixed entries from both file IDs.

✅ Similarity scores should be sorted in descending order.

5. Mode Switching & Persistence
Objective: Ensure the transition from Inline to RAG is seamless and history is preserved accurately.

Flow:

Upload File -> Status is uploaded.

Chat 1: System uses Inline Mode.

Simulate Webhook: Call /webhook/ingest manually.

Check Status: Status becomes completed.

Chat 2: System uses RAG Mode for the same file in the same conversation.

Verification (History Check):

Bash

curl -X GET "http://localhost:8000/chats/{CONVERSATION_ID}"
✅ Message 1 metadata: retrieval_mode: "inline"

✅ Message 2 metadata: retrieval_mode: "rag"

Quick Validation Script
Run this bash script to quickly verify the RAG status of the two main test files.

Bash

#!/bin/bash
FILE_1="500107f2-4445-4be2-9a5e-aca7144780d2"
FILE_2="fc952142-4b8a-401f-80f1-ddf5c11e90af"
BASE_URL="http://localhost:8000"

echo "--- Testing File 1 (Minecraft) ---"
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Test query\", \"file_id\": \"$FILE_1\"}" \
  | grep -o '"retrieval_mode":"[^"]*"'

echo -e "\n--- Testing File 2 (Sample) ---"
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Test query\", \"file_id\": \"$FILE_2\"}" \
  | grep -o '"retrieval_mode":"[^"]*"'