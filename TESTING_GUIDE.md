# Testing Guide for Milestone 1 Endpoints

This guide shows how to test all the file upload endpoints using Postman or curl.

## Prerequisites

1. **Start the FastAPI server:**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Ensure your `.env` file is configured** with:
   - `DATABASE_URL` (required)
   - `AWS_ACCESS_KEY_ID` (required for S3 operations)
   - `AWS_SECRET_ACCESS_KEY` (required for S3 operations)
   - `AWS_S3_BUCKET` (required for S3 operations)
   - Other optional settings

3. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

## Testing Flow

The complete flow is:
1. **POST /presign** → Get upload URL and file_id
2. **PUT to S3** → Upload PDF using presigned URL
3. **POST /webhook/ingest** → Create file record in database
4. **GET /files** → List all files
5. **GET /files/{file_id}** → Get file details with download URL

---

## 1. POST /presign - Get Upload URL

### Postman Setup:
- **Method:** `POST`
- **URL:** `http://localhost:8000/files/presign`
- **Headers:**
  - `Content-Type: application/json`
- **Body (raw JSON):**
  ```json
  {
    "filename": "test-document.pdf"
  }
  ```

### Expected Response:
```json
{
  "file_id": "123e4567-e89b-12d3-a456-426614174000",
  "presigned_url": "https://s3.amazonaws.com/your-bucket/uploads/123e4567-e89b-12d3-a456-426614174000.pdf?X-Amz-Algorithm=...",
  "expires_in_seconds": 3600
}
```

### curl Command:
```bash
curl -X POST "http://localhost:8000/files/presign" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test-document.pdf"
  }'
```

**Save the `file_id` and `presigned_url` from the response!**

---

## 2. Upload PDF to S3 (PUT Request)

### Postman Setup:
- **Method:** `PUT`
- **URL:** Use the `presigned_url` from step 1 (the entire URL including query parameters)
- **Headers:**
  - `Content-Type: application/pdf`
- **Body:**
  - Select `binary` or `file`
  - Upload a PDF file

### curl Command:
```bash
# Replace {presigned_url} with the actual URL from step 1
# Replace /path/to/your/file.pdf with your actual PDF file path
curl -X PUT "{presigned_url}" \
  -H "Content-Type: application/pdf" \
  --data-binary @/path/to/your/file.pdf
```

**Note:** The presigned URL includes all necessary authentication parameters. You don't need AWS credentials for this request.

### Troubleshooting Upload Issues:

If you get a `RequestTimeout` or other error:

1. **Verify the presigned URL is complete:**
   - The URL should be very long (includes query parameters like `?X-Amz-Algorithm=...`)
   - Copy the ENTIRE URL from the response, including all query parameters
   - The URL should start with `https://` and contain your bucket name

2. **Check your request method:**
   - Must be `PUT` (not POST, not GET)
   - In Postman: Select `PUT` from the method dropdown

3. **Verify headers:**
   - Must include: `Content-Type: application/pdf`
   - In Postman: Add this in the Headers tab
   - In curl: Use `-H "Content-Type: application/pdf"`

4. **Verify file data:**
   - In Postman: Use `Body` → `binary` → Select your PDF file
   - In curl: Use `--data-binary @/path/to/file.pdf` (not `-d` or `--data`)
   - Make sure the file path is correct and the file exists

5. **Test with a small PDF first:**
   - Large files may timeout
   - Try with a small test PDF (under 1MB) first

6. **Example curl command (replace placeholders):**
   ```bash
   # Get the presigned URL first (save it to a variable)
   PRESIGNED_URL="https://s3.amazonaws.com/your-bucket/uploads/123e4567...?X-Amz-Algorithm=..."
   
   # Upload the file
   curl -X PUT "$PRESIGNED_URL" \
     -H "Content-Type: application/pdf" \
     --data-binary @/path/to/your/file.pdf \
     -v  # -v for verbose output to see what's happening
   ```

7. **Check URL encoding:**
   - If copying from a terminal, the URL might be split across lines
   - Make sure the entire URL is on one line
   - Special characters in the URL should be URL-encoded (they usually are in presigned URLs)

---

## 3. POST /webhook/ingest - Create File Record

### Postman Setup:
- **Method:** `POST`
- **URL:** `http://localhost:8000/webhook/ingest`
- **Headers:**
  - `Content-Type: application/json`
- **Body (raw JSON):**
  ```json
  {
    "s3_bucket": "swe-test-godwin-j-uploads",
    "s3_key": "uploads/{file_id}.pdf"
  }
  ```
  Replace `{file_id}` with the file_id from step 1.

### Expected Response:
```json
{
  "file_id": "123e4567-e89b-12d3-a456-426614174000",
  "s3_key": "uploads/123e4567-e89b-12d3-a456-426614174000.pdf",
  "ingestion_status": "uploaded",
  "message": "File record created successfully"
}
```

### curl Command:
```bash
# Replace {file_id} with the actual file_id from step 1
# Replace {bucket_name} with your actual S3 bucket name
curl -X POST "http://localhost:8000/webhook/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "s3_bucket": "{bucket_name}",
    "s3_key": "uploads/{file_id}.pdf"
  }'
```

---

## 4. GET /files - List All Files

### Postman Setup:
- **Method:** `GET`
- **URL:** `http://localhost:8000/files?limit=20&offset=0`
- **Query Parameters (optional):**
  - `limit`: Number of files to return (default: 20, max: 100)
  - `offset`: Pagination offset (default: 0)

### Expected Response:
```json
{
  "files": [
    {
      "file_id": "123e4567-e89b-12d3-a456-426614174000",
      "s3_key": "uploads/123e4567-e89b-12d3-a456-426614174000.pdf",
      "ingestion_status": "uploaded",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

### curl Command:
```bash
curl -X GET "http://localhost:8000/files?limit=20&offset=0"
```

---

## 5. GET /files/{file_id} - Get File Details

### Postman Setup:
- **Method:** `GET`
- **URL:** `http://localhost:8000/files/{file_id}`
  Replace `{file_id}` with the actual file_id from step 1.

### Expected Response:
```json
{
  "file_id": "123e4567-e89b-12d3-a456-426614174000",
  "s3_key": "uploads/123e4567-e89b-12d3-a456-426614174000.pdf",
  "ingestion_status": "uploaded",
  "presigned_download_url": "https://s3.amazonaws.com/your-bucket/uploads/123e4567-e89b-12d3-a456-426614174000.pdf?X-Amz-Algorithm=...",
  "download_url_expires_in_seconds": 3600,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### curl Command:
```bash
# Replace {file_id} with the actual file_id
curl -X GET "http://localhost:8000/files/{file_id}"
```

---

## Complete Test Script (bash)

Save this as `test_endpoints.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"
BUCKET_NAME="swe-test-godwin-j-your-bucket-name"  # Update this!

echo "=== Step 1: Get Presigned URL ==="
RESPONSE=$(curl -s -X POST "${BASE_URL}/files/presign" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test-document.pdf"}')

echo "$RESPONSE" | jq '.'

FILE_ID=$(echo "$RESPONSE" | jq -r '.file_id')
PRESIGNED_URL=$(echo "$RESPONSE" | jq -r '.presigned_url')

echo -e "\nFile ID: $FILE_ID"
echo "Presigned URL: $PRESIGNED_URL"

echo -e "\n=== Step 2: Upload PDF to S3 ==="
echo "Please upload a PDF file manually using the presigned URL above"
echo "Or use: curl -X PUT \"$PRESIGNED_URL\" -H \"Content-Type: application/pdf\" --data-binary @/path/to/file.pdf"

read -p "Press Enter after uploading the file to S3..."

echo -e "\n=== Step 3: Trigger Webhook ==="
curl -X POST "${BASE_URL}/webhook/ingest" \
  -H "Content-Type: application/json" \
  -d "{
    \"s3_bucket\": \"${BUCKET_NAME}\",
    \"s3_key\": \"uploads/${FILE_ID}.pdf\"
  }" | jq '.'

echo -e "\n=== Step 4: List All Files ==="
curl -X GET "${BASE_URL}/files?limit=20&offset=0" | jq '.'

echo -e "\n=== Step 5: Get File Details ==="
curl -X GET "${BASE_URL}/files/${FILE_ID}" | jq '.'
```

Make it executable:
```bash
chmod +x test_endpoints.sh
./test_endpoints.sh
```

---

## Troubleshooting

### Common Issues:

1. **"AWS credentials must be configured"**
   - Check your `.env` file has `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

2. **"AWS_S3_BUCKET must be configured"**
   - Set `AWS_S3_BUCKET` in your `.env` file

3. **"Invalid S3 key format"**
   - Ensure the S3 key is exactly: `uploads/{file_id}.pdf`
   - The file_id must be a valid UUID

4. **Database connection errors**
   - Verify `DATABASE_URL` in `.env` is correct
   - Ensure the database is running
   - Run migrations: `alembic upgrade head`

5. **404 Not Found**
   - Check the file_id exists in the database
   - Verify the endpoint URL is correct

6. **CORS errors (if testing from browser)**
   - Add CORS middleware to `main.py` if needed:
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   app.add_middleware(CORSMiddleware, allow_origins=["*"])
   ```

---

## FastAPI Interactive Docs

FastAPI automatically generates interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

You can test endpoints directly from these pages!

