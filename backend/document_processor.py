import os
import logging
from typing import Dict, Any, Optional
from enum import Enum
from dotenv import load_dotenv
import pytesseract
import PyPDF2
import tabula
from PIL import Image
import magic
from langchain.text_splitter import RecursiveCharacterTextSplitter

load_dotenv()

class DocumentType(Enum):
    """Supported document types enumeration"""
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"
    EXCEL = "excel"

class AdvancedDocumentProcessor:
    """Main document processor class handling multiple file types"""
    
    def __init__(self, storage_path: Optional[str] = None, log_level: Optional[str] = None):
        """
        Initialize document processor
        
        Args:
            storage_path (Optional[str]): Path for processed documents
            log_level (Optional[str]): Logging verbosity level
        """
        self.storage_path = storage_path or os.getenv("DOCUMENT_STORAGE_PATH", "data/processed_documents")
        self.log_level = log_level or "INFO"
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False
        )
        
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format='%(asctime)s - %(levelname)s: %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        os.makedirs(self.storage_path, exist_ok=True)

    def detect_document_type(self, file_path: str) -> DocumentType:
        """
        Detect document type using MIME magic
        
        Args:
            file_path (str): Path to document file
        
        Returns:
            DocumentType: Detected document type
        
        Raises:
            ValueError: If detection fails
        """
        try:
            mime = magic.Magic(mime=True)
            mime_type = mime.from_file(file_path)
            type_mapping = {
                'application/pdf': DocumentType.PDF,
                'image/png': DocumentType.IMAGE,
                'image/jpeg': DocumentType.IMAGE,
                'text/plain': DocumentType.TEXT,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': DocumentType.EXCEL
            }
            return type_mapping.get(mime_type, DocumentType.TEXT)
        except Exception as e:
            self.logger.error(f"Type detection error: {e}")
            raise ValueError("Failed to detect document type") from e

    def process_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Process PDF document with text and table extraction
        
        Args:
            file_path (str): Path to PDF file
        
        Returns:
            dict: Processed document data with chunks and metadata
        
        Raises:
            RuntimeError: If PDF processing fails
        """
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text_pages = [page.extract_text() for page in reader.pages]
            
            full_text = '\n'.join(text_pages)
            chunks = self.text_splitter.split_text(full_text)
            
            # Extract tables
            processed_tables = []
            try:
                tables = tabula.read_pdf(file_path, pages='all', multiple_tables=True)
                processed_tables = [table.to_dict('records') for table in tables if not table.empty]
            except Exception as e:
                self.logger.warning(f"Table extraction failed: {e}")

            return {
                'text': full_text,
                'chunks': chunks,
                'tables': processed_tables,
                'page_count': len(reader.pages),
                'total_chunks': len(chunks)
            }
        except Exception as e:
            self.logger.error(f"PDF processing error: {e}")
            raise RuntimeError("PDF processing failed") from e

    def process_image(self, file_path: str) -> Dict[str, Any]:
        """
        Process image file with OCR
        
        Args:
            file_path (str): Path to image file
        
        Returns:
            dict: Processed OCR data with chunks
        
        Raises:
            RuntimeError: If image processing fails
        """
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image) or ""
            chunks = self.text_splitter.split_text(text)
            return {
                'text': text,
                'chunks': chunks,
                'format': image.format,
                'mode': image.mode,
                'total_chunks': len(chunks)
            }
        except Exception as e:
            self.logger.error(f"Image processing error: {e}")
            raise RuntimeError("Image processing failed") from e

    def process_text(self, file_path: str) -> Dict[str, Any]:
        """
        Process plain text file
        
        Args:
            file_path (str): Path to text file
        
        Returns:
            dict: Processed text with chunks
        
        Raises:
            RuntimeError: If text processing fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            chunks = self.text_splitter.split_text(text)
            return {
                'text': text,
                'chunks': chunks,
                'total_chunks': len(chunks)
            }
        except Exception as e:
            self.logger.error(f"Text processing error: {e}")
            raise RuntimeError("Text processing failed") from e

    def process_document(self, file_path: str) -> Dict[str, Any]:
        """
        Main document processing method
        
        Args:
            file_path (str): Path to document file
        
        Returns:
            dict: Processed document data with metadata
        
        Raises:
            ValueError: For unsupported document types
        """
        doc_type = self.detect_document_type(file_path)
        processor = {
            DocumentType.PDF: self.process_pdf,
            DocumentType.IMAGE: self.process_image,
            DocumentType.TEXT: self.process_text
        }.get(doc_type, None)
        
        if not processor:
            raise ValueError(f"Unsupported document type: {doc_type}")
        
        result = processor(file_path)
        result['filename'] = os.path.basename(file_path)
        result['file_type'] = doc_type.value
        return result