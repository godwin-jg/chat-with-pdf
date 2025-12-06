"""
OpenAI client for chat completions with Base64 PDF support.
"""
import base64
from typing import List, Dict, Any, Optional
from openai import OpenAI
from config import settings
import logging

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for OpenAI API operations."""

    def __init__(self):
        """Initialize OpenAI client."""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be configured")

        # Initialize client - check if base_url is needed for company proxy
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        # Fallback models to try if primary model fails
        # Prioritize models that are actually available
        self.fallback_models = [
            "gpt-4.1",  # Available model
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
        ]
        
        # Try to get available models from API
        self._available_models = None
        try:
            self._check_available_models()
        except Exception as e:
            logger.warning(f"Could not check available models: {e}")
    
    def _check_available_models(self):
        """Check which models are available via the API."""
        try:
            # Try to list models (if API supports it)
            models = self.client.models.list()
            self._available_models = [model.id for model in models.data]
            logger.info(f"Found {len(self._available_models)} available models via API")
        except Exception as e:
            # API might not support model listing, that's okay
            logger.debug(f"Model listing not available: {e}")
            self._available_models = None

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
    ) -> str:
        """
        Send chat completion request to OpenAI with automatic model fallback.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
                For messages with PDF files, content should be a list with:
                - {"type": "text", "text": "message text"}
                - {"type": "image_url", "image_url": {"url": "data:application/pdf;base64,{base64}"}}
            temperature: Sampling temperature (default: 0.7)

        Returns:
            Assistant's response text

        Raises:
            ValueError: If no models are available or PDF format not supported
        """
        # If we have a list of available models, use those first
        if self._available_models:
            # Prioritize available models
            available_to_try = [m for m in self._available_models if m in [self.model] + self.fallback_models]
            other_models = [m for m in [self.model] + self.fallback_models if m not in available_to_try]
            models_to_try = available_to_try + other_models
        else:
            models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
        
        last_error = None
        last_error_details = []
        
        for model in models_to_try:
            try:
                logger.info(f"Trying model: {model}")
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                )
                if model != self.model:
                    logger.warning(f"Using fallback model: {model} (primary: {self.model} not available)")
                return response.choices[0].message.content
            except Exception as e:
                error_str = str(e)
                last_error = e
                
                # Extract error details for better debugging
                error_details = {
                    "model": model,
                    "error": error_str
                }
                last_error_details.append(error_details)
                logger.warning(f"Model {model} failed: {error_str[:100]}")
                
                # If model not found, try next model
                if "model_not_found" in error_str or "does not have access" in error_str:
                    continue
                # If PDF format error, this model doesn't support PDFs
                elif "Invalid MIME type" in error_str or "invalid_image_format" in error_str:
                    continue
                # Check for authentication errors
                elif "Invalid API key" in error_str or "unauthorized" in error_str.lower() or "401" in error_str:
                    raise ValueError(f"Invalid API key or authentication error: {error_str}")
                # Rate limit or timeout - try next model
                elif "rate_limit" in error_str.lower() or "timeout" in error_str.lower():
                    continue
                # Other errors - might be a different issue, but try next model anyway
                else:
                    # Check if it's a specific model issue or general API issue
                    if "project" in error_str.lower() and "access" in error_str.lower():
                        # This is a model access issue, continue to next
                        continue
                    # Unknown error, but continue trying
                    continue
        
        # All models failed - provide detailed error info
        error_summary = "\n".join([f"  - {d['model']}: {d['error'][:80]}..." for d in last_error_details[:3]])
        if "model_not_found" in str(last_error) or "does not have access" in str(last_error) or "project" in str(last_error).lower():
            raise ValueError(
                f"None of the models are available with your API key.\n"
                f"Tried: {', '.join(models_to_try)}\n\n"
                f"Error details:\n{error_summary}\n\n"
                f"Please check:\n"
                f"1. Your API key has model access enabled\n"
                f"2. Contact your API provider for available models\n"
                f"3. Check OpenAI dashboard for model access settings"
            )
        elif "Invalid MIME type" in str(last_error) or "invalid_image_format" in str(last_error):
            raise ValueError(
                f"None of the available models support PDFs via vision API. "
                f"Tried: {', '.join(models_to_try)}. "
                f"Please use a model that supports vision (e.g., gpt-4o, gpt-4-turbo) "
                f"or contact your API provider."
            )
        else:
            raise ValueError(f"OpenAI API error: {last_error}")

    def pdf_to_base64(self, pdf_bytes: bytes) -> str:
        """
        Convert PDF bytes to Base64 string for OpenAI API.

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            Base64 encoded string
        """
        return base64.b64encode(pdf_bytes).decode("utf-8")

    def pdf_to_images_base64(self, pdf_bytes: bytes, max_pages: int = 10) -> List[str]:
        """
        Convert PDF pages to images and encode as Base64 strings.
        
        This is used when the vision API doesn't support PDFs directly.
        We convert each page to a PNG image and send them via the vision API.

        Args:
            pdf_bytes: PDF file content as bytes
            max_pages: Maximum number of pages to convert (to avoid token limits)

        Returns:
            List of Base64 encoded PNG images (one per page)

        Raises:
            ImportError: If pymupdf is not installed
            Exception: If PDF conversion fails
        """
        try:
            import fitz  # type: ignore # pymupdf
        except ImportError:
            raise ImportError(
                "pymupdf is not installed. Install it with: pip install pymupdf"
            )

        try:
            # Open PDF from bytes
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            image_base64_list = []

            # Convert each page to image (limit to max_pages)
            for page_num in range(min(len(pdf_doc), max_pages)):
                page = pdf_doc[page_num]
                
                # Render page as PNG image (scale factor 2.0 for better quality)
                # DPI: 150 (2.0 * 72 = 144 DPI, good balance of quality and size)
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PNG bytes
                img_bytes = pix.tobytes("png")
                
                # Encode to base64
                img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                image_base64_list.append(img_base64)
                
                logger.info(
                    f"Converted PDF page {page_num + 1}/{len(pdf_doc)} to image "
                    f"({len(img_bytes)} bytes)"
                )

            pdf_doc.close()
            
            logger.info(
                f"Converted {len(image_base64_list)} PDF pages to images "
                f"(total: {len(pdf_doc)} pages in PDF)"
            )
            
            return image_base64_list
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            raise

    def create_message_with_pdf(
        self, role: str, text: str, pdf_base64: str
    ) -> Dict[str, Any]:
        """
        Create a message dictionary with PDF attachment for OpenAI API.

        Per OpenAI PDF Files Guide and technical-setup.md, we try the vision API format
        first (image_url with data URI). If the model doesn't support this, we'll fall
        back to text extraction in the chat handler.

        Format: Uses "image_url" type with data URI as per OpenAI's PDF Files guide.

        Args:
            role: Message role ("user" or "assistant")
            text: Text content of the message
            pdf_base64: Base64 encoded PDF content

        Returns:
            Message dictionary formatted for OpenAI API

        Note:
            If this format fails with "Invalid MIME type" error, the chat handler
            will automatically fall back to extracting text from the PDF.
        """
        return {
            "role": role,
            "content": [
                {"type": "text", "text": text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:application/pdf;base64,{pdf_base64}",
                    },
                },
            ],
        }

    def create_message_with_images(
        self, role: str, text: str, image_base64_list: List[str]
    ) -> Dict[str, Any]:
        """
        Create a message dictionary with multiple image attachments for OpenAI Vision API.

        Converts PDF pages to images and sends them via the vision API.
        This works when direct PDF format is not supported.

        Args:
            role: Message role ("user" or "assistant")
            text: Text content of the message
            image_base64_list: List of Base64 encoded PNG images

        Returns:
            Message dictionary formatted for OpenAI API with multiple images
        """
        content = [{"type": "text", "text": text}]
        
        # Add each image to the content
        for img_base64 in image_base64_list:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_base64}",
                },
            })
        
        return {
            "role": role,
            "content": content,
        }

    def create_text_message(self, role: str, text: str) -> Dict[str, Any]:
        """
        Create a simple text message dictionary for OpenAI API.

        Args:
            role: Message role ("user" or "assistant")
            text: Text content of the message

        Returns:
            Message dictionary formatted for OpenAI API
        """
        return {"role": role, "content": text}

    def get_embeddings(self, text_chunks: List[str]) -> List[List[float]]:
        """
        Generate embeddings for text chunks using OpenAI's text-embedding-3-small model.

        Args:
            text_chunks: List of text strings to embed

        Returns:
            List of embedding vectors (each is a list of floats)

        Raises:
            ValueError: If API call fails or no chunks provided
        """
        if not text_chunks:
            raise ValueError("text_chunks cannot be empty")

        try:
            logger.info(f"Generating embeddings for {len(text_chunks)} chunks using {settings.OPENAI_EMBEDDING_MODEL}")
            
            # Call OpenAI embeddings API
            response = self.client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=text_chunks,
            )
            
            # Extract embeddings from response
            embeddings = [item.embedding for item in response.data]
            
            logger.info(
                f"Successfully generated {len(embeddings)} embeddings "
                f"(dimension: {len(embeddings[0]) if embeddings else 0})"
            )
            
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise ValueError(f"Failed to generate embeddings: {str(e)}")


# Global OpenAI client instance (lazy initialization)
_openai_client: Optional[OpenAIClient] = None


def get_openai_client() -> OpenAIClient:
    """Get or create the global OpenAI client instance."""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAIClient()
    return _openai_client

