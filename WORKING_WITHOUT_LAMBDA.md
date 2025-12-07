Issue: I attempted to deploy the Lambda function for S3 event processing, but my current AWS credentials lack the lambda:CreateFunction permission.

Solution: Since the assignment states we "can simulate or use actual Lambda," I opted for a simulation approach to unblock development.

Implementation Details:

I created lambda_function.py to demonstrate exactly how the cloud function would look if deployed (runtime: Python 3.14).

## Current Webhook Invocation Method

**How:** The webhook is currently called **manually** via HTTP POST request to `/webhook/ingest` after a file is uploaded to S3.

**When:** The webhook is called immediately after the client successfully uploads a file to S3 using the presigned URL.

**Current Flow:**
1. Client calls `POST /files/presign` to get a presigned upload URL
2. Client uploads PDF directly to S3 using the presigned URL
3. **Manual Step:** Client (or developer) calls `POST /webhook/ingest` with the S3 bucket and key to trigger ingestion

**Example Manual Webhook Call:**
```bash
curl -X POST "http://localhost:8000/webhook/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "s3_bucket": "swe-test-godwin-j",
    "s3_key": "uploads/FILE_ID.pdf"
  }'
```

**What the Webhook Does:**
- Extracts `file_id` from the S3 key (format: `uploads/{file_id}.pdf`)
- Creates a file record in the database with status `"uploaded"`
- Starts a background task to process ingestion (extract, chunk, embed, upsert to vector DB)
- Returns immediately (ingestion runs asynchronously)

**Note:** In production with Lambda deployed, this webhook would be automatically triggered by S3 event notifications, eliminating the need for manual calls.
