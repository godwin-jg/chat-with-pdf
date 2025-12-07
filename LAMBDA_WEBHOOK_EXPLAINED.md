# Lambda & Webhook: What's Required vs. What's Allowed for Testing

## Quick Answer

**Assignment Requirement:**
- ✅ You MUST create a real AWS Lambda function that triggers on S3 uploads
- ✅ Lambda MUST call your `/webhook/ingest` endpoint

**For Local Testing:**
- ✅ You CAN manually call `/webhook/ingest` to simulate Lambda (this is NOT cheating)
- ✅ This is explicitly allowed in the assignment (see line 516 of assignment_requirements.md)

---

## The Full Flow (Production)

```
1. Client → POST /presign
   ↓ Returns presigned URL

2. Client → PUT to S3 (using presigned URL)
   ↓ File uploaded to S3

3. S3 → Triggers Lambda (automatic)
   ↓ Lambda receives S3 event

4. Lambda → POST /webhook/ingest
   ↓ Calls your FastAPI endpoint

5. FastAPI → Processes ingestion
   ↓ Creates DB record, extracts, chunks, embeds
```

---

## What the Assignment Actually Requires

### From `assignment_requirements.md` (line 7, 162, 183):

> **"AWS Lambda is triggered by the S3 upload event and calls /webhook/ingest with the S3 event payload."**

> **"Request (called by AWS Lambda):"**

> **"Local Testing with ngrok: During development, use ngrok to expose your local FastAPI server to the internet. Configure your AWS Lambda function to call your ngrok URL (e.g., https://abc123.ngrok.io/webhook/ingest). This allows you to test the full S3 → Lambda → FastAPI webhook flow locally without deploying your backend."**

### From `assignment_requirements.md` (line 516):

> **"Call /webhook/ingest with S3 event payload (can simulate or use actual Lambda)"**

**Key Point:** The assignment explicitly allows simulation for testing!

---

## Two Valid Approaches

### Approach 1: Real Lambda (Production/Proper Testing)

**Setup:**
1. Create AWS Lambda function: `swe-test-<your-name>-ingest`
2. Configure S3 bucket to trigger Lambda on `uploads/` prefix
3. Lambda code extracts `bucket` and `key` from S3 event
4. Lambda makes HTTP POST to `/webhook/ingest` with:
   ```json
   {
     "s3_bucket": "swe-test-godwin-j",
     "s3_key": "uploads/{file_id}.pdf"
   }
   ```

**Lambda Function Code Example:**
```python
import json
import os
import requests

def lambda_handler(event, context):
    # Extract S3 event details
    s3_event = event['Records'][0]['s3']
    bucket = s3_event['bucket']['name']
    key = s3_event['object']['key']
    
    # Get webhook URL from environment variable
    webhook_url = os.environ.get('WEBHOOK_URL')
    
    # Call FastAPI webhook endpoint
    payload = {
        "s3_bucket": bucket,
        "s3_key": key
    }
    
    response = requests.post(
        webhook_url,
        json=payload,
        timeout=120
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps('Webhook called successfully')
    }
```

**For Local Testing with Lambda:**
- Use ngrok to expose your local FastAPI server
- Set Lambda environment variable: `WEBHOOK_URL=https://abc123.ngrok.io/webhook/ingest`
- Lambda will call your local server via ngrok

---

### Approach 2: Manual Simulation (Local Development)

**This is what your `test_endpoints.sh` does:**

```bash
# Step 3: POST /webhook/ingest
WEBHOOK_RESPONSE=$(curl -s -X POST "${BASE_URL}/webhook/ingest" \
  -H "Content-Type: application/json" \
  -d "{
    \"s3_bucket\": \"${BUCKET_NAME}\",
    \"s3_key\": \"uploads/${FILE_ID}.pdf\"
  }")
```

**This is NOT cheating!** The assignment explicitly allows this for testing.

---

## Why Both Are Allowed

### Real Lambda (Required for Production)
- ✅ Tests the full production flow
- ✅ Verifies S3 → Lambda integration works
- ✅ Shows you understand AWS event-driven architecture
- ✅ Required for proper end-to-end testing

### Manual Simulation (Allowed for Local Dev)
- ✅ Faster iteration during development
- ✅ No need to set up Lambda for every test
- ✅ Easier debugging (direct API calls)
- ✅ Explicitly mentioned in assignment as valid testing method

---

## What You Should Do

### For Milestone 1-2 (Development):
1. ✅ Use manual `/webhook/ingest` calls (like `test_endpoints.sh`)
2. ✅ Focus on getting the backend logic working
3. ✅ Test with curl/Postman/scripts

### For Milestone 3-4 (Production Testing):
1. ✅ Set up real AWS Lambda function
2. ✅ Configure S3 → Lambda trigger
3. ✅ Use ngrok for local testing with Lambda
4. ✅ Verify full S3 → Lambda → FastAPI flow works

### For Submission:
1. ✅ Document both approaches in your README
2. ✅ Show Lambda function code (if you created it)
3. ✅ Explain how to test with Lambda vs. manual calls
4. ✅ Include test scripts for both methods

---

## Current Implementation Status

Looking at your code:

**✅ Webhook Endpoint:** Your `/webhook/ingest` endpoint is correctly implemented and accepts the Lambda payload format.

**✅ Test Script:** Your `test_endpoints.sh` manually calls the webhook (which is allowed).

**❓ Lambda Function:** No Lambda function code found in the repo (which is fine - Lambda code lives in AWS, not in your repo).

---

## Example: Full Lambda Setup

If you want to set up the real Lambda, here's what you need:

### 1. Create Lambda Function in AWS Console

**Name:** `swe-test-godwin-j-ingest`  
**Runtime:** Python 3.12  
**Memory:** 512 MB  
**Timeout:** 120 seconds  
**Layer:** `arn:aws:lambda:ap-south-1:770693421928:layer:Klayers-p312-requests:19`

### 2. Lambda Code

```python
import json
import os
import requests

def lambda_handler(event, context):
    """
    Lambda handler for S3 upload events.
    Extracts bucket and key, then calls FastAPI webhook.
    """
    try:
        # Extract S3 event details
        s3_event = event['Records'][0]['s3']
        bucket = s3_event['bucket']['name']
        key = s3_event['object']['key']
        
        # Get webhook URL from environment variable
        webhook_url = os.environ.get('WEBHOOK_URL')
        if not webhook_url:
            raise ValueError("WEBHOOK_URL environment variable not set")
        
        # Prepare payload
        payload = {
            "s3_bucket": bucket,
            "s3_key": key
        }
        
        # Call FastAPI webhook endpoint
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=120,
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Webhook called successfully',
                'bucket': bucket,
                'key': key
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
```

### 3. Configure S3 Trigger

In AWS Console:
- Go to your S3 bucket
- Properties → Event notifications
- Create event notification:
  - **Event type:** Object creation (PUT)
  - **Prefix:** `uploads/`
  - **Suffix:** `.pdf`
  - **Destination:** Lambda function → `swe-test-godwin-j-ingest`

### 4. Set Environment Variable

In Lambda Console:
- Configuration → Environment variables
- Add: `WEBHOOK_URL=https://your-ngrok-url.ngrok.io/webhook/ingest`

### 5. Test with ngrok

```bash
# Terminal 1: Start FastAPI
uvicorn main:app --reload

# Terminal 2: Start ngrok
ngrok http 8000

# Terminal 3: Upload file to S3 (triggers Lambda automatically)
curl -X PUT "$PRESIGNED_URL" \
  -H "Content-Type: application/pdf" \
  --data-binary @test.pdf
```

---

## Summary

| Aspect | Requirement | Status |
|--------|------------|--------|
| **Lambda Function** | ✅ Required (for production) | ❓ Not in repo (fine - lives in AWS) |
| **Webhook Endpoint** | ✅ Required | ✅ Implemented correctly |
| **Manual Testing** | ✅ Allowed | ✅ Using `test_endpoints.sh` |
| **S3 → Lambda Trigger** | ✅ Required (for production) | ❓ Need to configure in AWS |
| **ngrok for Local Testing** | ✅ Recommended | ❓ Optional but helpful |

**Bottom Line:**
- Your current approach (manual webhook calls) is **valid for testing**
- You should **also set up Lambda** for proper end-to-end testing
- Both approaches are acceptable per the assignment requirements

