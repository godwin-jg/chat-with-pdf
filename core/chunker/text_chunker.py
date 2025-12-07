"""
Manual text chunker implementation (pure Python, no external libraries).
Implements sliding window overlap for RAG chunking.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 102) -> List[str]:
    """
    Chunk text into fixed-size chunks with overlap using pure Python.
    
    Uses approximate token counting (4 characters per token) and word boundaries
    to create chunks with sliding window overlap.
    
    Args:
        text: Input text to chunk
        chunk_size: Target chunk size in tokens (default: 512)
        overlap: Overlap size in tokens (default: 102, which is ~20% of 512)
    
    Returns:
        List of text chunks
    
    Example:
        >>> text = "This is a long document..."
        >>> chunks = chunk_text(text, chunk_size=512, overlap=102)
        >>> len(chunks)  # Number of chunks created
    """
    if not text or not text.strip():
        return []
    
    chunk_size_chars = chunk_size * 4
    overlap_chars = overlap * 4
    
    if len(text) <= chunk_size_chars:
        return [text.strip()]
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size_chars
        
        if end < text_length:
            search_limit = int(chunk_size_chars * 0.2)
            boundary_pos = end
            
            for i in range(end, max(start, end - search_limit), -1):
                if i < text_length and text[i] in [' ', '\n', '.', '!', '?', '\t']:
                    boundary_pos = i + 1
                    break
            
            end = boundary_pos
        
        chunk = text[start:end].strip()
        
        if chunk:
            chunks.append(chunk)
            logger.debug(
                f"Created chunk {len(chunks)}: {len(chunk)} chars "
                f"(start={start}, end={end})"
            )
        
        if end >= text_length:
            break
        
        start = max(start + 1, end - overlap_chars)
    
    logger.info(
        f"Chunked text into {len(chunks)} chunks "
        f"(chunk_size={chunk_size} tokens, overlap={overlap} tokens)"
    )
    
    return chunks

