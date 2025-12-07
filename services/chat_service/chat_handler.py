"""
Chat handler service for processing chat requests with Base64 PDF and RAG support.
"""
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from dao.chat_dao import ConversationDAO, MessageDAO
from dao.file_dao import FileDAO
from dao.models.conversation import Conversation
from dao.models.message import Message, MessageRole, RetrievalMode
from dao.models.file import File, IngestionStatus
from core.openai.openai_client import get_openai_client
from core.aws.s3_client import get_s3_client
from core.parsers.pdf_parser import extract_text_from_pdf
from core.vector.upstash_client import get_upstash_client

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
        self.upstash_client = get_upstash_client()

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
                file = await self.file_dao.get_by_id(session, str(message.file_id))
                if file and file.ingestion_status == IngestionStatus.UPLOADED:
                    try:
                        pdf_bytes = self.s3_client.download_file(file.s3_key)
                        logger.info(f"Downloaded PDF from S3: {len(pdf_bytes)} bytes")
                        
                        image_base64_list = self.openai_client.pdf_to_images_base64(
                            pdf_bytes, max_pages=10
                        )
                        
                        if image_base64_list:
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
                    openai_message = self.openai_client.create_text_message(
                        role=message.role.value, text=message.content
                    )
            else:
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

    async def collect_file_ids_from_conversation(
        self, session: AsyncSession, conversation_id: str
    ) -> Tuple[List[str], bool]:
        """
        Collect all file_ids from conversation and check if any are completed.
        
        Returns:
            Tuple of (list of file_ids, has_completed_files)
        """
        messages = await self.message_dao.get_by_conversation_id(
            session, conversation_id
        )
        
        file_ids = []
        has_completed = False
        
        for msg in messages:
            if msg.file_id:
                file_id_str = str(msg.file_id)
                if file_id_str not in file_ids:
                    file_ids.append(file_id_str)
                    file = await self.file_dao.get_by_id(session, file_id_str)
                    if file and file.ingestion_status == IngestionStatus.COMPLETED:
                        has_completed = True
        
        return file_ids, has_completed

    async def process_chat(
        self,
        session: AsyncSession,
        message: str,
        conversation_id: Optional[str] = None,
        file_id: Optional[str] = None,
    ) -> Tuple[Conversation, Message, str, str, Optional[List[Dict[str, Any]]]]:
        """
        Process a chat request with dynamic mode switching (inline or RAG).

        Args:
            session: Database session
            message: User's message text
            conversation_id: Optional conversation ID (creates new if not provided)
            file_id: Optional file ID to associate with this message

        Returns:
            Tuple of (conversation, user_message, assistant_response_text, retrieval_mode, retrieved_chunks)

        Raises:
            ValueError: If file_id is provided but file not found
        """
        conversation = await self.get_or_create_conversation(
            session, conversation_id
        )

        file = None
        if file_id:
            file = await self.file_dao.get_by_id(session, file_id)
            if not file:
                raise ValueError(f"File with id {file_id} not found")
            logger.info(f"File {file_id} status: {file.ingestion_status}")

        user_message = await self.message_dao.create(
            session,
            conversation_id=conversation.id,
            role=MessageRole.USER.value,
            content=message,
            file_id=file.id if file else None,
        )
        
        await session.commit()
        await session.refresh(user_message)

        file_ids, has_completed_files = await self.collect_file_ids_from_conversation(
            session, str(conversation.id)
        )
        
        if file and file.ingestion_status == IngestionStatus.COMPLETED:
            file_id_str = str(file.id)
            if file_id_str not in file_ids:
                file_ids.append(file_id_str)
            has_completed_files = True
        
        logger.info(f"Collected {len(file_ids)} file_id(s), has_completed={has_completed_files}, file_ids={file_ids}")

        message_history = await self.build_message_history(
            session, str(conversation.id)
        )

        retrieval_mode = RetrievalMode.INLINE.value
        retrieved_chunks = None

        if has_completed_files and file_ids:
            logger.info(f"RAG mode enabled: {len(file_ids)} file(s) with completed ingestion")
            
            tools = [self.openai_client.get_semantic_search_tool()]
            
            try:
                response_text, tool_calls = self.openai_client.chat_completion_with_tools(
                    messages=message_history,
                    tools=tools,
                )
                
                if tool_calls:
                    logger.info(f"LLM called {len(tool_calls)} tool(s)")
                    
                    tool_messages = []
                    all_retrieved_chunks = []
                    
                    for tool_call in tool_calls:
                        if tool_call["function"]["name"] == "semantic_search":
                            args = json.loads(tool_call["function"]["arguments"])
                            query = args.get("query", message)
                            top_k = args.get("top_k", 5)
                            
                            logger.info(f"Executing semantic_search: query='{query}', top_k={top_k}")
                            
                            query_embeddings = self.openai_client.get_embeddings([query])
                            query_vector = query_embeddings[0]
                            
                            if len(file_ids) == 1:
                                filter_str = f"file_id = '{file_ids[0]}'"
                            else:
                                filter_parts = [f"file_id = '{fid}'" for fid in file_ids]
                                filter_str = " OR ".join(filter_parts)
                            
                            results = self.upstash_client.query_vectors(
                                query_vector=query_vector,
                                top_k=top_k,
                                filter=filter_str,
                            )
                            
                            chunks = []
                            for result in results:
                                metadata = result.get("metadata", {})
                                chunk_data = {
                                    "chunk_text": metadata.get("chunk_text", ""),
                                    "similarity_score": result.get("score", 0.0),
                                }
                                chunks.append(chunk_data)
                                all_retrieved_chunks.append(chunk_data)
                            
                            logger.info(f"Retrieved {len(chunks)} chunks from vector database")
                            
                            tool_result = {
                                "role": "tool",
                                "content": json.dumps({
                                    "chunks": chunks,
                                    "count": len(chunks)
                                }),
                                "tool_call_id": tool_call["id"]
                            }
                            tool_messages.append(tool_result)
                    
                    assistant_message_with_tools = {
                        "role": "assistant",
                        "content": response_text or None,
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": tc["type"],
                                "function": {
                                    "name": tc["function"]["name"],
                                    "arguments": tc["function"]["arguments"]
                                }
                            }
                            for tc in tool_calls
                        ]
                    }
                    message_history.append(assistant_message_with_tools)
                    
                    message_history.extend(tool_messages)
                    
                    final_response = self.openai_client.chat_completion(
                        messages=message_history,
                        tools=None,
                    )
                    
                    retrieval_mode = RetrievalMode.RAG.value
                    retrieved_chunks = all_retrieved_chunks
                    assistant_response_text = final_response
                    
                else:
                    logger.warning("LLM did not call semantic_search tool, but RAG mode is enabled. Forcing retrieval...")
                    query_embeddings = self.openai_client.get_embeddings([message])
                    query_vector = query_embeddings[0]
                    
                    if len(file_ids) == 1:
                        filter_str = f"file_id = '{file_ids[0]}'"
                    else:
                        filter_parts = [f"file_id = '{fid}'" for fid in file_ids]
                        filter_str = " OR ".join(filter_parts)
                    
                    results = self.upstash_client.query_vectors(
                        query_vector=query_vector,
                        top_k=5,
                        filter=filter_str,
                    )
                    
                    all_retrieved_chunks = []
                    for result in results:
                        metadata = result.get("metadata", {})
                        chunk_data = {
                            "chunk_text": metadata.get("chunk_text", ""),
                            "similarity_score": result.get("score", 0.0),
                        }
                        all_retrieved_chunks.append(chunk_data)
                    
                    if all_retrieved_chunks:
                        chunks_text = "\n\n".join([chunk["chunk_text"] for chunk in all_retrieved_chunks[:3]])
                        enhanced_message = f"{message}\n\nRelevant context from documents:\n{chunks_text}"
                        message_history[-1]["content"] = enhanced_message
                    
                    assistant_response_text = self.openai_client.chat_completion(
                        messages=message_history
                    )
                    retrieval_mode = RetrievalMode.RAG.value
                    retrieved_chunks = all_retrieved_chunks
                    
            except Exception as e:
                logger.error(f"Tool calling failed: {e}", exc_info=True)
                assistant_response_text = self.openai_client.chat_completion(
                    messages=message_history
                )
                retrieval_mode = RetrievalMode.INLINE.value
        else:
            logger.info("Using inline mode (no completed files)")
            try:
                assistant_response_text = self.openai_client.chat_completion(
                    messages=message_history
                )
            except ValueError as e:
                error_str = str(e)
                if "Invalid MIME type" in error_str or "invalid_image_format" in error_str:
                    logger.warning("Model doesn't support PDFs via vision API. Rebuilding messages with text extraction...")
                    message_history = await self.build_message_history_with_text_extraction(
                        session, str(conversation.id)
                    )
                    assistant_response_text = self.openai_client.chat_completion(
                        messages=message_history
                    )
                else:
                    raise

        assistant_message = await self.message_dao.create(
            session,
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT.value,
            content=assistant_response_text,
            retrieval_mode=retrieval_mode,
            retrieved_chunks=retrieved_chunks,
        )

        await session.commit()

        return conversation, user_message, assistant_response_text, retrieval_mode, retrieved_chunks

