import json
import os
import requests
import urllib.parse


def lambda_handler(event, context):
    """
    Lambda handler for S3 upload events.
    
    This function is automatically triggered by S3 when a file is uploaded.
    It extracts the bucket and key from the S3 event, then calls the FastAPI
    webhook endpoint to trigger ingestion.
    
    Args:
        event: S3 event containing bucket and key information
            {
                "Records": [
                    {
                        "s3": {
                            "bucket": {"name": "swe-test-godwin-j"},
                            "object": {"key": "uploads/file-id.pdf"}
                        }
                    }
                ]
            }
        context: Lambda context (unused)
    
    Returns:
        dict: Status code and response body
    
    Environment Variables:
        WEBHOOK_URL: Full URL to FastAPI webhook endpoint
            Example: https://abc123.ngrok.io/webhook/ingest
    """
    try:
        # Log incoming event for debugging
        print(f"Lambda triggered with event: {json.dumps(event, indent=2)}")
        
        # Validate event structure
        if 'Records' not in event or len(event['Records']) == 0:
            raise ValueError("Invalid event: No Records found")
        
        # Extract S3 event details
        record = event['Records'][0]
        if 's3' not in record:
            raise ValueError("Invalid event: No s3 data in record")
        
        s3_event = record['s3']
        bucket = s3_event['bucket']['name']
        key = s3_event['object']['key']
        
        # URL decode the key (S3 keys are URL-encoded)
        # Example: "uploads%2Ffile-id.pdf" → "uploads/file-id.pdf"
        key = urllib.parse.unquote_plus(key)
        
        print(f"Processing: Bucket={bucket}, Key={key}")
        
        # Validate key format (should be uploads/{file_id}.pdf)
        if not key.startswith('uploads/') or not key.endswith('.pdf'):
            print(f"WARNING: Key doesn't match expected format: {key}")
            # Continue anyway - let FastAPI handle validation
        
        # Get webhook URL from environment variable
        webhook_url = os.environ.get('WEBHOOK_URL')
        if not webhook_url:
            error_msg = "WEBHOOK_URL environment variable not set"
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        
        print(f"Calling webhook: {webhook_url}")
        
        # Prepare payload matching WebhookIngestRequest schema
        payload = {
            "s3_bucket": bucket,
            "s3_key": key
        }
        
        # Call FastAPI webhook endpoint
        print(f"Sending payload: {json.dumps(payload)}")
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=120,  # 2 minutes timeout
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AWS-Lambda-S3-Trigger/1.0"
            }
        )
        
        # Check for HTTP errors
        response.raise_for_status()
        
        # Log successful response
        response_data = response.json() if response.text else None
        print(f"✅ Webhook called successfully!")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response_data, indent=2)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Webhook called successfully',
                'bucket': bucket,
                'key': key,
                'webhook_response': response_data
            })
        }
        
    except KeyError as e:
        error_msg = f"Invalid S3 event structure: Missing key '{str(e)}'"
        print(f"ERROR: {error_msg}")
        print(f"Event structure: {json.dumps(event, indent=2)}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': error_msg,
                'event_keys': list(event.keys()) if isinstance(event, dict) else None
            })
        }
        
    except requests.exceptions.Timeout:
        error_msg = "Webhook request timed out after 120 seconds"
        print(f"ERROR: {error_msg}")
        return {
            'statusCode': 504,
            'body': json.dumps({
                'error': error_msg,
                'bucket': bucket if 'bucket' in locals() else None,
                'key': key if 'key' in locals() else None
            })
        }
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to call webhook: {str(e)}"
        print(f"ERROR: {error_msg}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   HTTP Status: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
        return {
            'statusCode': 502,
            'body': json.dumps({
                'error': error_msg,
                'bucket': bucket if 'bucket' in locals() else None,
                'key': key if 'key' in locals() else None,
                'http_status': e.response.status_code if hasattr(e, 'response') and e.response else None
            })
        }
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_msg,
                'error_type': type(e).__name__,
                'bucket': bucket if 'bucket' in locals() else None,
                'key': key if 'key' in locals() else None
            })
        }

