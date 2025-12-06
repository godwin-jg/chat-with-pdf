# Setup Instructions

## ✅ What's Working

1. **All endpoints are functional:**
   - POST /chat ✅
   - GET /chats ✅
   - GET /chats/{conversation_id} ✅
   - All file endpoints ✅

2. **Model access fixed:**
   - Found available models: `gpt-4.1-mini`, `gpt-4.1`
   - Model fallback implemented
   - Config updated to use `gpt-4.1-mini`

3. **PDF handling:**
   - Since `gpt-4.1-mini` doesn't support PDFs via vision API, we extract text from PDFs
   - Text extraction implemented using PyPDF2

## ⚠️ Action Required

### Install PyPDF2

The server needs PyPDF2 installed to extract text from PDFs:

```bash
# If using pip directly:
pip install pypdf2

# If using poetry:
poetry add pypdf2

# If using virtual environment:
source venv/bin/activate  # or your venv path
pip install pypdf2
```

**Then restart your server:**
```bash
uvicorn main:app --reload
```

## Testing

After installing PyPDF2 and restarting:

1. **Test chat with PDF:**
   ```bash
   curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "What is this document about?",
       "file_id": "500107f2-4445-4be2-9a5e-aca7144780d2"
     }'
   ```

2. **Test all endpoints:**
   - POST /chat with file_id
   - GET /chats
   - GET /chats/{conversation_id}

## Current Status

- ✅ Database: Working
- ✅ File uploads: Working  
- ✅ Chat endpoints: Working
- ✅ Model access: Fixed (gpt-4.1-mini)
- ⚠️ PDF text extraction: Needs PyPDF2 installation

Once PyPDF2 is installed and server restarted, everything should work!

