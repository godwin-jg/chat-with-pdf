"""
Chat handler service for processing chat requests with Base64 PDF support.
"""
from typing import List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from dao.chat_dao import ConversationDAO, MessageDAO
from dao.file_dao import FileDAO
from dao.models.conversation import Conversation
from dao.models.message import Message, MessageRole, RetrievalMode
from dao.models.file import File, IngestionStatus
from core.openai.openai_client import get_openai_client
from core.aws.s3_client import get_s3_client
from core.parsers.pdf_parser import extract_text_from_pdf
import logging

logger = logging.getLogger(__name__)


class ChatHandler:
    """Service for handling chat requests with context patching."""

    def __init__(self):
        """Initialize chat handler."""
        self.conversation_dao = ConversationDAO()
        self.message_dao = MessageDAO()
        self.file_dao = FileDAO()
        self.openai_client = get_openai_client()
        self.s3_client = get_s3_client()

    async def get_or_create_conversation(
        self, session: AsyncSession, conversation_id: Optional[str] = None
    ) -> Conversation:
        """
        Get existing conversation or create a new one.

        Args:
            session: Database session
            conversation_id: Optional conversation ID (UUID string)

        Returns:
            Conversation instance
        """
        if conversation_id:
            conversation = await self.conversation_dao.get_by_id(
                session, conversation_id
            )
            if conversation:
                return conversation

        # Create new conversation
        conversation = await self.conversation_dao.create(session)
        return conversation

    async def build_message_history(
        self, session: AsyncSession, conversation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Build message history for OpenAI API with context patching.

        For messages with file_id:
        - If file.ingestion_status == "uploaded": Download PDF, convert to Base64, attach
        - If file.ingestion_status == "completed": Include text only (RAG will handle retrieval later)

        Args:
            session: Database session
            conversation_id: Conversation ID

        Returns:
            List of message dictionaries formatted for OpenAI API
        """
        messages = await self.message_dao.get_by_conversation_id(
            session, conversation_id
        )

        openai_messages = []

        for message in messages:
            if message.file_id:
                # Fetch file to check ingestion status
                file = await self.file_dao.get_by_id(session, str(message.file_id))
                if file and file.ingestion_status == IngestionStatus.UPLOADED:
                    # Inline mode: Convert PDF pages to images and send via vision API
                    # This works because vision API supports images (PNG/JPEG)
                    try:
                        pdf_bytes = self.s3_client.download_file(file.s3_key)
                        logger.info(f"Downloaded PDF from S3: {len(pdf_bytes)} bytes")
                        
                        # Convert PDF pages to images (PNG base64)
                        image_base64_list = self.openai_client.pdf_to_images_base64(
                            pdf_bytes, max_pages=10
                        )
                        
                        if image_base64_list:
                            # Create message with images (vision API format)
                            openai_message = self.openai_client.create_message_with_images(
                                role=message.role.value,
                                text=message.content,
                                image_base64_list=image_base64_list,
                            )
                            logger.info(
                                f"✅ Attached {len(image_base64_list)} PDF pages as images "
                                f"via vision API for message {message.id} (file: {file.id})"
                            )
                        else:
                            logger.warning(f"PDF conversion returned no images for file {file.id}")
                            openai_message = self.openai_client.create_text_message(
                                role=message.role.value, text=message.content
                            )
                    except ImportError as import_err:
                        logger.error(
                            f"pymupdf not installed. Install with: pip install pymupdf. Error: {import_err}"
                        )
                        # Fallback to text extraction
                        try:
                            pdf_bytes = self.s3_client.download_file(file.s3_key)
                            pdf_text = extract_text_from_pdf(pdf_bytes)
                            if pdf_text and len(pdf_text.strip()) > 0:
                                enhanced_content = f"{message.content}\n\nPDF Content:\n{pdf_text[:8000]}"
                                openai_message = self.openai_client.create_text_message(
                                    role=message.role.value, text=enhanced_content
                                )
                                logger.info(f"Fallback: Extracted PDF text ({len(pdf_text)} chars)")
                            else:
                                openai_message = self.openai_client.create_text_message(
                                    role=message.role.value, text=message.content
                                )
                        except Exception as fallback_err:
                            logger.error(f"Fallback text extraction also failed: {fallback_err}")
                            openai_message = self.openai_client.create_text_message(
                                role=message.role.value,
                                text=f"{message.content}\n\n[Note: PDF processing unavailable - install pymupdf: pip install pymupdf]"
                            )
                    except Exception as e:
                        logger.error(
                            f"Failed to convert PDF to images for message {message.id}: {e}"
                        )
                        import traceback
                        logger.error(traceback.format_exc())
                        # Fallback to text extraction
                        try:
                            pdf_bytes = self.s3_client.download_file(file.s3_key)
                            pdf_text = extract_text_from_pdf(pdf_bytes)
                            if pdf_text and len(pdf_text.strip()) > 0:
                                enhanced_content = f"{message.content}\n\nPDF Content:\n{pdf_text[:8000]}"
                                openai_message = self.openai_client.create_text_message(
                                    role=message.role.value, text=enhanced_content
                                )
                                logger.info(f"Fallback: Extracted PDF text ({len(pdf_text)} chars)")
                            else:
                                openai_message = self.openai_client.create_text_message(
                                    role=message.role.value, text=message.content
                                )
                        except Exception as fallback_err:
                            logger.error(f"Fallback text extraction failed: {fallback_err}")
                            openai_message = self.openai_client.create_text_message(
                                role=message.role.value, text=message.content
                            )
                else:
                    # File is completed or not found - use text only (RAG will handle retrieval)
                    openai_message = self.openai_client.create_text_message(
                        role=message.role.value, text=message.content
                    )
            else:
                # No file attached - simple text message
                openai_message = self.openai_client.create_text_message(
                    role=message.role.value, text=message.content
                )

            openai_messages.append(openai_message)

        return openai_messages

    async def build_message_history_with_text_extraction(
        self, session: AsyncSession, conversation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Build message history using text extraction instead of base64 PDFs.
        
        Used as fallback when vision API doesn't support PDFs.

        Args:
            session: Database session
            conversation_id: Conversation ID

        Returns:
            List of message dictionaries formatted for OpenAI API
        """
        messages = await self.message_dao.get_by_conversation_id(
            session, conversation_id
        )

        openai_messages = []

        for message in messages:
            if message.file_id:
                file = await self.file_dao.get_by_id(session, str(message.file_id))
                if file and file.ingestion_status == IngestionStatus.UPLOADED:
                    # Convert PDF pages to images (same as main build_message_history)
                    try:
                        pdf_bytes = self.s3_client.download_file(file.s3_key)
                        image_base64_list = self.openai_client.pdf_to_images_base64(
                            pdf_bytes, max_pages=10
                        )
                        if image_base64_list:
                            openai_message = self.openai_client.create_message_with_images(
                                role=message.role.value,
                                text=message.content,
                                image_base64_list=image_base64_list,
                            )
                            logger.info(f"Attached {len(image_base64_list)} PDF pages as images")
                        else:
                            openai_message = self.openai_client.create_text_message(
                                role=message.role.value, text=message.content
                            )
                    except Exception as e:
                        logger.error(f"Failed to convert PDF to images: {e}")
                        # Fallback to text extraction
                        try:
                            pdf_bytes = self.s3_client.download_file(file.s3_key)
                            pdf_text = extract_text_from_pdf(pdf_bytes)
                            if pdf_text and len(pdf_text.strip()) > 0:
                                enhanced_content = f"{message.content}\n\nPDF Content:\n{pdf_text[:8000]}"
                                openai_message = self.openai_client.create_text_message(
                                    role=message.role.value, text=enhanced_content
                                )
                            else:
                                openai_message = self.openai_client.create_text_message(
                                    role=message.role.value, text=message.content
                                )
                        except Exception as fallback_err:
                            logger.error(f"Fallback text extraction failed: {fallback_err}")
                            openai_message = self.openai_client.create_text_message(
                                role=message.role.value, text=message.content
                            )
                else:
                    openai_message = self.openai_client.create_text_message(
                        role=message.role.value, text=message.content
                    )
            else:
                openai_message = self.openai_client.create_text_message(
                    role=message.role.value, text=message.content
                )

            openai_messages.append(openai_message)

        return openai_messages

    async def process_chat(
        self,
        session: AsyncSession,
        message: str,
        conversation_id: Optional[str] = None,
        file_id: Optional[str] = None,
    ) -> Tuple[Conversation, Message, str]:
        """
        Process a chat request with inline PDF support.

        Args:
            session: Database session
            message: User's message text
            conversation_id: Optional conversation ID (creates new if not provided)
            file_id: Optional file ID to associate with this message

        Returns:
            Tuple of (conversation, user_message, assistant_response_text)

        Raises:
            ValueError: If file_id is provided but file not found
        """
        # Get or create conversation
        conversation = await self.get_or_create_conversation(
            session, conversation_id
        )

        # Validate file_id if provided
        file = None
        if file_id:
            file = await self.file_dao.get_by_id(session, file_id)
            if not file:
                raise ValueError(f"File with id {file_id} not found")

        # Store user message
        user_message = await self.message_dao.create(
            session,
            conversation_id=conversation.id,
            role=MessageRole.USER.value,
            content=message,
            file_id=file.id if file else None,
        )

        # Build message history with context patching
        message_history = await self.build_message_history(
            session, str(conversation.id)
        )

        # Get assistant response from OpenAI
        # If PDF format fails, retry with text extraction
        try:
            assistant_response_text = self.openai_client.chat_completion(
                messages=message_history
            )
        except ValueError as e:
            error_str = str(e)
            # If PDF format not supported, rebuild messages with text extraction
            if "Invalid MIME type" in error_str or "invalid_image_format" in error_str:
                logger.warning("Model doesn't support PDFs via vision API. Rebuilding messages with text extraction...")
                # Rebuild message history with text extraction instead of base64
                message_history = await self.build_message_history_with_text_extraction(
                    session, str(conversation.id)
                )
                assistant_response_text = self.openai_client.chat_completion(
                    messages=message_history
                )
            else:
                raise

        # Store assistant message with retrieval_mode="inline"
        assistant_message = await self.message_dao.create(
            session,
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT.value,
            content=assistant_response_text,
            retrieval_mode=RetrievalMode.INLINE.value,
            retrieved_chunks=None,  # No chunks for inline mode
        )

        # Commit transaction
        await session.commit()

        return conversation, user_message, assistant_response_text

