Technical Setup Guide
AWS, Tools, and Constraints
AWS Resource Setup
Naming Convention (Mandatory)
All AWS resources (S3 bucket, Lambda function, etc.) must be prefixed with swe-test-<firstname-lastname> to help us track resource ownership and manage costs.

Examples:

S3 bucket: swe-test-john-doe-pdfs
Lambda function: swe-test-john-doe-ingest
Upstash Vector namespace: swe-test-john-doe
AWS Credentials Scope (Important)
Your AWS credentials are scoped to only work with resources prefixed with swe-test-<your-firstname>-<your-lastname>-*.

✅ You CAN create: swe-test-john-doe-pdfs, swe-test-john-doe-ingest, etc.
❌ You CANNOT create: Resources without this prefix or with other candidates' prefixes
If you try to create resources without the correct prefix, you will get permission errors

Make sure to use ONLY your assigned prefix for all AWS resources (S3 buckets, Lambda functions, IAM roles, etc.). This ensures resource isolation and prevents conflicts with other candidates.

Note: The aws-credentials-<your-name>.txt file provided to you contains your specific prefix mentioned in the instructions section. Refer to that file to confirm your exact prefix format.
S3 to Lambda to Webhook Flow
Step 1: S3 Upload
User calls /presign to get a presigned URL pointing to s3://swe-test-<firstname-lastname>/uploads/{file_id}.pdf
User uploads the file directly to S3 using the presigned URL (PUT request)
File lands in S3 bucket
Step 2: Lambda Trigger
S3 is configured to send an event to Lambda when a new object is created in the uploads/ prefix
Lambda is triggered with an S3 event payload containing bucket and key

Lambda Configuration:

Runtime: Python 3.12
Memory: 512 MB (adequate for PDF processing)
Timeout: 60–120 seconds (for small-to-medium PDFs; increase if needed for large files)
Lambda Layer: Use the pre-built layer for Python 3.12: arn:aws:lambda:ap-south-1:770693421928:layer:Klayers-p312-requests:19
This layer includes the requests library, boto3, and other common packages
Find more ARNs here: https://github.com/keithrozario/Klayers/tree/master/deployments/python3.12
Step 3: Webhook API Call
Lambda extracts bucket and key from the S3 event
Lambda makes an HTTP POST request to your backend's /webhook/ingest endpoint
Your backend processes the request and ingests the PDF
Local Testing with ngrok
During development, Lambda can't reach your local backend. Use ngrok to expose your local FastAPI server to the internet, allowing Lambda to call your local /webhook/ingest endpoint.
Setup:
Install ngrok: https://ngrok.com/download
Start your FastAPI server locally (e.g., uvicorn main:app --reload on port 8000)
In a new terminal, run: ngrok http 8000
ngrok will provide a public URL like https://abc123.ngrok.io
Lambda Configuration for ngrok:
Set an environment variable in Lambda: WEBHOOK_URL=https://abc123.ngrok.io/webhook/ingest
Lambda function code should read this environment variable and POST the S3 event payload to this URL
Set a higher timeout in your Lambda request call (e.g., timeout=120) to avoid hanging
Timeout Tips:
Lambda timeout: Increase to 60–120 seconds if processing large PDFs
requests.post() timeout: Always set a timeout (e.g., timeout=120) to avoid hanging
ngrok URL regeneration: Each time you restart ngrok, you get a new URL. Update Lambda's WEBHOOK_URL accordingly
Debugging:
Check CloudWatch Logs for Lambda execution logs
Check ngrok terminal for incoming requests
Use print() statements in Lambda; they appear in CloudWatch
Important Notes:
ngrok URLs are temporary and regenerate on restart. Save the URL or use ngrok's paid service for persistent domains
Never expose credentials in ngrok URLs or Lambda logs
For production, deploy your FastAPI server to a service like AWS EC2, Fargate, Modal, or Heroku
S3 CORS Configuration
When clients upload directly to S3 using presigned URLs, ensure CORS is configured for PUT requests.
S3 CORS Policy:
[
  {
    "AllowedMethods": ["PUT", "POST", "GET"],
    "AllowedOrigins": ["*"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3000
  }
]
Package Requirements
Mandatory Packages:
FastAPI - Backend framework (required)
OpenAI SDK - For embeddings and chat completions (required)
SQLAlchemy - ORM for database operations (recommended)
Pydantic - Data validation and type safety (strongly recommended)
boto3 - AWS S3 operations (required)
upstash-vector - Vector database operations (required)
Recommended Packages:
markitdown - Microsoft's PDF to Markdown parser (high-quality output)
pymupdf - Alternative PDF parser (fast and reliable)
pypdf2 - Lightweight PDF parser (minimal dependencies)
pdfplumber - Layout-preserving PDF parser (good for structured documents)
Alembic - Database migrations (recommended)
python-dotenv - Environment variables management
psycopg2 or asyncpg - Postgres connection drivers
tiktoken - Token counting for OpenAI (optional but useful)
Forbidden Packages:
You may NOT use these frameworks:

❌ LangChain
❌ LlamaIndex
❌ DSPy
❌ Haystack
❌ Semantic Kernel
❌ Any framework that abstracts RAG, chunking, or tool calling

Why? We want to see that you understand the fundamentals of RAG, embeddings, and tool calling by implementing them manually.
AI Models
Chat Completions: gpt-4.1-mini (only this model allowed)

Embeddings: text-embedding-3-small (only this model allowed)

Your provided API key has access only to these models. Do not attempt to use any other models.
Upstash Vector Setup
Namespace Configuration (Mandatory):
Create a namespace for your vectors using the same naming convention: swe-test-<firstname-lastname>
All embeddings for your PDFs should be stored within this namespace
When querying vectors, always specify this namespace to filter results correctly
Documentation: See Upstash Vector Namespaces for implementation details
Why Namespaces?
Isolate vectors by project or candidate
Prevent cross-contamination between different PDFs or datasets
Makes cleanup and resource tracking easier
Type Safety with Pydantic
Why Pydantic?
Pydantic ensures data validation, type safety, and automatic API documentation. All request/response models should be defined as Pydantic models.
Benefits:
✅ Automatic validation: Invalid requests return 422 automatically
✅ Type hints: IDE autocomplete and static type checking
✅ OpenAPI docs: FastAPI auto-generates Swagger UI from Pydantic models
✅ Serialization: JSON ↔ Python objects seamlessly
✅ Documentation: Models serve as clear API contracts

Define request and response models for all endpoints (/presign, /webhook/ingest, /retrieve, /chat) using Pydantic BaseModel.
Environment Variables
You will receive a pre-configured .env file with all necessary credentials:

OPENAI_API_KEY - OpenAI API key
DATABASE_URL - Neon Postgres connection string
UPSTASH_VECTOR_URL - Upstash Vector API URL
UPSTASH_VECTOR_TOKEN - Upstash Vector token
AWS_ACCESS_KEY_ID - AWS access key
AWS_SECRET_ACCESS_KEY - AWS secret key
AWS_REGION - AWS region (ap-south-1)
S3_BUCKET_NAME - Your S3 bucket name (swe-test-)

Place the .env file in your project root and use python-dotenv to load environment variables.
PDF Text Extraction & Chunking
PDF Extraction:
You can choose any of these libraries:

markitdown: Microsoft's library for converting PDFs to Markdown. Handles complex layouts and preserves structure well.
pymupdf: Fast and reliable PDF parser with good text extraction quality.
pdfplumber: Preserves layout and formatting better. Excellent for tabular data and structured PDFs.
pypdf2: Lightweight, simple text extraction. Good for straightforward PDFs.

Recommendation: Use markitdown if you want high-quality Markdown output. Use pdfplumber for a good balance of simplicity and quality. Use pypdf2 only if you need minimal dependencies. But whatever gives you the quickest result, use that.
Chunking Strategy:
You must decide and document your chunking approach. Common strategies:

Fixed-size chunks: E.g., 512 tokens per chunk with 20% overlap. Simple and effective. Recommended for this assignment since it's the simplest and most common.
Semantic chunking: Split on sentence or paragraph boundaries. Preserves meaning.
Hybrid: Combine fixed size with semantic boundaries.

Document your choice in your DEVELOPMENT_LOG.md, including:

Chunk size (in tokens or characters)
Overlap percentage
How you handle edge cases (very small or large documents)
Error Handling & Resilience
Expected Failures:
S3 key not found → Return 404 from /webhook/ingest
PDF parsing fails → Set ingestion_status to "failed", log error
OpenAI API timeout → Retry with exponential backoff
Upstash Vector API fails → Gracefully degrade or set status to "failed"
Logging:
Use Python's logging module to log all errors, API calls, and important events. This will help with debugging during development and review.
API Testing Tools
Use Postman or Insomnia to test your APIs during development.
Key Endpoints to Test:
POST /presign → Get presigned URL
Manual S3 upload using the presigned URL
POST /webhook/ingest → Trigger ingestion (or simulate with curl)
POST /retrieve → Test retrieval independently
POST /chat → Test chat with inline and RAG modes
Tips:
Save requests in collections for easy re-testing
Use environment variables in Postman to store file_id, base_url, etc.
Test error cases (missing fields, invalid file_id, etc.)
Reference Documentation
OpenAI:
PDF Files (Base64): https://platform.openai.com/docs/guides/pdf-files?api-mode=chat#base64-encoded-files
Learn how to send PDF files directly to gpt-4.1-mini as base64 data
Embeddings API: https://platform.openai.com/docs/guides/embeddings
Generate embeddings using text-embedding-3-small
Understand token limits and batch processing
Function Calling: https://platform.openai.com/docs/guides/function-calling
Define your semantic_search tool with proper schema
Implement the tool calling loop manually
Upstash Vector:
Getting Started: https://upstash.com/docs/vector/overall/getstarted
Namespaces: https://upstash.com/docs/vector/features/namespaces (mandatory for this assignment)
Metadata Filtering: https://upstash.com/docs/vector/features/filtering (required for filtering by file_id)
Klayers (Lambda Layers):
Python 3.12 Layers: https://github.com/keithrozario/Klayers/tree/master/deployments/python3.12
Pre-built Lambda layers with common Python packages including requests
Database Setup
Connection String Format:
You will be provided a Neon Postgres connection string in your .env file:

postgresql://user:password@ep-xyz.us-east-1.neon.tech/dbname
Recommended Approach:
Use SQLAlchemy with Pydantic models for type safety
Use Alembic for migrations (even if simple)
Create models for files, conversations, and messages tables
Test the connection before starting ingestion
Final Reminders
✅ Always prefix AWS resources with swe-test-<firstname-lastname> (S3, Lambda)
✅ Always create Upstash Vector namespace with the same prefix
✅ Use .env for secrets (provided to you pre-configured)
✅ Test each milestone independently before moving to the next
✅ Document your chunking and tool-calling logic clearly
✅ Use AI tools to accelerate boilerplate, but verify the logic
✅ Reference the provided docs when stuck (OpenAI, Upstash)
✅ Use ngrok for local Lambda testing - it's the easiest way to test the full flow

