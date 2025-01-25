from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import hashlib 
from dotenv import load_dotenv
from backend.document_processor import AdvancedDocumentProcessor
from backend.embedding import EmbeddingService
from backend.model import LangChainQAService
from pydantic import BaseModel

load_dotenv()

app = FastAPI(
    title="Multi-Modal Document Processing API",
    description="Advanced document processing and Q&A system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

api_key = os.getenv('GOOGLE_API_KEY')
document_storage_path = os.getenv('DOCUMENT_STORAGE_PATH', 'data/documents')

os.makedirs(document_storage_path, exist_ok=True)

doc_processor = AdvancedDocumentProcessor()
embedding_service = EmbeddingService()
qa_service = LangChainQAService(api_key) 

class QueryModel(BaseModel):
    query: str

async def process_document_async(filename: str, content: bytes):
    """Process document and store embeddings"""
    temp_path = os.path.join(document_storage_path, filename)
    try:
        # Save uploaded file temporarily
        with open(temp_path, 'wb') as buffer:
            buffer.write(content)

        # Process document and split into chunks
        processed_doc = doc_processor.process_document(temp_path)
        chunks = processed_doc.get('chunks', [])
        
        if not chunks:
            raise ValueError("No text chunks generated from document")

        # Generate unique ID from content hash
        file_hash = hashlib.sha256(content).hexdigest()
        unique_id = f"{filename}_{file_hash}"
        
        # Prepare metadata for each chunk
        metadatas = [{
            'filename': filename,
            'file_type': processed_doc['file_type'],
            'chunk_index': i
        } for i in range(len(chunks))]

        # Store embeddings for all chunks
        embedding_service.store_embeddings(
            texts=chunks,
            metadatas=metadatas,
            unique_id=unique_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/upload/batch")
async def batch_upload(
    background_tasks: BackgroundTasks, 
    files: List[UploadFile] = File(...)
):
    results = []
    for file in files:
        content = await file.read()
        background_tasks.add_task(process_document_async, file.filename, content)
        results.append({"filename": file.filename, "status": "queued"})
    return {"message": "Documents queued for processing", "results": results}

@app.post("/ask")
async def ask_question(query: QueryModel):
    try:
        context = embedding_service.search_embeddings(query.query)
        answer = qa_service.generate_answer(query.query, context)
        return {"answer": answer, "sources": context}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Question answering failed: {str(e)}")

if __name__ == "__main__": 
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)