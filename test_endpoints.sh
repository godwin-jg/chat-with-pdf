#!/bin/bash

# Test script for Milestone 1 endpoints
# Usage: ./test_endpoints.sh

BASE_URL="http://localhost:8000"
BUCKET_NAME="${AWS_S3_BUCKET:-swe-test-godwin-j-your-bucket-name}"  # Update this or set AWS_S3_BUCKET env var

echo "=========================================="
echo "Testing Chat with PDF API - Milestone 1"
echo "=========================================="
echo ""

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "⚠️  jq is not installed. Install it for better JSON formatting:"
    echo "   macOS: brew install jq"
    echo "   Linux: sudo apt-get install jq"
    echo ""
    JQ_CMD="cat"
else
    JQ_CMD="jq ."
fi

echo "=== Step 1: POST /files/presign ==="
echo "Request: POST ${BASE_URL}/files/presign"
echo "Body: {\"filename\": \"test-document.pdf\"}"
echo ""

RESPONSE=$(curl -s -X POST "${BASE_URL}/files/presign" \
  -H "Content-Type: application/json" \
  -d '{"filename": "test-document.pdf"}')

echo "Response:"
echo "$RESPONSE" | $JQ_CMD
echo ""

FILE_ID=$(echo "$RESPONSE" | grep -o '"file_id":"[^"]*"' | cut -d'"' -f4)
PRESIGNED_URL=$(echo "$RESPONSE" | grep -o '"presigned_url":"[^"]*"' | cut -d'"' -f4)

if [ -z "$FILE_ID" ]; then
    echo "❌ Failed to get file_id. Exiting."
    exit 1
fi

echo "✅ File ID: $FILE_ID"
echo "✅ Presigned URL: ${PRESIGNED_URL:0:80}..."
echo ""

echo "=== Step 2: Upload PDF to S3 ==="
echo "⚠️  You need to upload a PDF file to S3 using the presigned URL above."
echo "   You can use curl or Postman to upload the file."
echo ""
echo "Example curl command (replace /path/to/file.pdf with your PDF):"
echo "curl -X PUT \"$PRESIGNED_URL\" \\"
echo "  -H \"Content-Type: application/pdf\" \\"
echo "  --data-binary @/path/to/file.pdf"
echo ""

read -p "Press Enter after uploading the file to S3 (or Ctrl+C to exit)..."
echo ""

echo "=== Step 3: POST /webhook/ingest ==="
echo "Request: POST ${BASE_URL}/webhook/ingest"
echo "Body: {\"s3_bucket\": \"${BUCKET_NAME}\", \"s3_key\": \"uploads/${FILE_ID}.pdf\"}"
echo ""

WEBHOOK_RESPONSE=$(curl -s -X POST "${BASE_URL}/webhook/ingest" \
  -H "Content-Type: application/json" \
  -d "{
    \"s3_bucket\": \"${BUCKET_NAME}\",
    \"s3_key\": \"uploads/${FILE_ID}.pdf\"
  }")

echo "Response:"
echo "$WEBHOOK_RESPONSE" | $JQ_CMD
echo ""

if echo "$WEBHOOK_RESPONSE" | grep -q "file_id"; then
    echo "✅ File record created successfully"
else
    echo "❌ Failed to create file record"
fi
echo ""

echo "=== Step 4: GET /files (List All Files) ==="
echo "Request: GET ${BASE_URL}/files?limit=20&offset=0"
echo ""

LIST_RESPONSE=$(curl -s -X GET "${BASE_URL}/files?limit=20&offset=0")
echo "Response:"
echo "$LIST_RESPONSE" | $JQ_CMD
echo ""

echo "=== Step 5: GET /files/{file_id} ==="
echo "Request: GET ${BASE_URL}/files/${FILE_ID}"
echo ""

FILE_RESPONSE=$(curl -s -X GET "${BASE_URL}/files/${FILE_ID}")
echo "Response:"
echo "$FILE_RESPONSE" | $JQ_CMD
echo ""

if echo "$FILE_RESPONSE" | grep -q "presigned_download_url"; then
    echo "✅ File details retrieved successfully"
else
    echo "❌ Failed to retrieve file details"
fi

echo ""
echo "=========================================="
echo "Testing complete!"
echo "=========================================="

