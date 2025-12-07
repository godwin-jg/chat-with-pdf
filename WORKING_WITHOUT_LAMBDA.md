Issue: I attempted to deploy the Lambda function for S3 event processing, but my current AWS credentials lack the lambda:CreateFunction permission.

Solution: Since the assignment states we "can simulate or use actual Lambda," I opted for a simulation approach to unblock development.

Implementation Details:

I created lambda_function.py to demonstrate exactly how the cloud function would look if deployed (runtime: Python 3.12).

I updated the API to verify it accepts the standard S3 event JSON structure.

I updated test_endpoints.sh to mock the Lambda behavior by sending a POST request to /webhook/ingest immediately after a successful S3 upload.

Result: The API processes files correctly without requiring additional AWS infrastructure permissions.