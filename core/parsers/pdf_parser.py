"""
PDF text extraction using pypdf2.
"""
from typing import Optional
import logging

logger = logging.getLogger(__name__)

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 not installed. PDF text extraction will not work.")


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF bytes.

    Args:
        pdf_bytes: PDF file content as bytes

    Returns:
        Extracted text content

    Raises:
        ImportError: If PyPDF2 is not installed
        Exception: If PDF parsing fails
    """
    if not PYPDF2_AVAILABLE:
        raise ImportError("PyPDF2 is not installed. Install it with: pip install pypdf2")

    try:
        from io import BytesIO
        pdf_file = BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        
        full_text = "\n\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} characters from PDF ({len(reader.pages)} pages)")
        return full_text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise

