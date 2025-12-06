"""
PDF text extraction using pymupdf (preferred) or pypdf2 (fallback).
"""
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Try pymupdf first (better quality)
try:
    import fitz  # pymupdf
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Fallback to PyPDF2
try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

if not PYMUPDF_AVAILABLE and not PYPDF2_AVAILABLE:
    logger.warning("Neither pymupdf nor PyPDF2 is installed. PDF text extraction will not work.")


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF bytes using pymupdf (preferred) or PyPDF2 (fallback).

    Args:
        pdf_bytes: PDF file content as bytes

    Returns:
        Extracted text content

    Raises:
        ImportError: If neither pymupdf nor PyPDF2 is installed
        Exception: If PDF parsing fails
    """
    # Try pymupdf first (better quality)
    if PYMUPDF_AVAILABLE:
        try:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = len(pdf_doc)
            
            text_parts = []
            for page_num in range(page_count):
                text = pdf_doc[page_num].get_text()
                if text:
                    text_parts.append(text)
            
            pdf_doc.close()
            full_text = "\n\n".join(text_parts)
            logger.info(f"Extracted {len(full_text)} chars using pymupdf ({page_count} pages)")
            return full_text
        except Exception as e:
            logger.warning(f"pymupdf extraction failed: {e}. Trying PyPDF2 fallback...")
            try:
                if 'pdf_doc' in locals():
                    pdf_doc.close()
            except:
                pass

    # Fallback to PyPDF2
    if PYPDF2_AVAILABLE:
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
            logger.info(
                f"Extracted {len(full_text)} characters from PDF using PyPDF2 "
                f"({len(reader.pages)} pages)"
            )
            return full_text
        except Exception as e:
            logger.error(f"Error extracting text from PDF with PyPDF2: {e}")
            raise

    # Neither library available
    raise ImportError(
        "Neither pymupdf nor PyPDF2 is installed. "
        "Install one with: pip install pymupdf OR pip install pypdf2"
    )

