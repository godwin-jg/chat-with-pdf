# What is Ingestion?

**Ingestion** is the process of processing a PDF file after it's uploaded to S3, preparing it for RAG (Retrieval-Augmented Generation).

## The Ingestion Pipeline (Step by Step)

1. **Download PDF from S3**
   - File is already in S3 (uploaded via presigned URL)
   - Download the PDF bytes

2. **Extract Text from PDF**
   - Use `pymupdf` or `PyPDF2` to extract all text content
   - Convert PDF pages to plain text

3. **Chunk the Text**
   - Split the text into smaller pieces (chunks)
   - Each chunk is ~512 tokens (approx 2048 characters)
   - Use sliding window with 102 token overlap
   - Why? LLMs have token limits, and smaller chunks are easier to search

4. **Generate Embeddings**
   - Convert each text chunk into a vector (list of numbers)
   - Use OpenAI's `text-embedding-3-small` model
   - Each chunk becomes a 1536-dimensional vector
   - Why? Vectors allow semantic search (finding similar meaning, not just keywords)

5. **Store in Upstash Vector**
   - Save each vector with metadata:
     - `file_id`: Which file this chunk came from
     - `chunk_index`: Position in the document
     - `chunk_text`: The actual text (for retrieval)
   - Store in namespace: `swe-test-godwin-j`

6. **Update File Status**
   - Mark file as `completed` (success) or `failed` (error)

## Why Ingestion is Needed

**Before Ingestion (Inline Mode):**
- PDF is sent as images to LLM
- Works but expensive and slow for large PDFs
- Limited by LLM context window

**After Ingestion (RAG Mode):**
- Only relevant chunks are retrieved based on query
- Much faster and cheaper
- Can handle large documents
- Better accuracy for specific questions

## Current Status

The ingestion is **failing** - the file status goes from `uploaded` → `failed`.

This means one of these steps is encountering an error:
- PDF download from S3
- Text extraction
- Chunking
- Embedding generation
- Upstash Vector storage

