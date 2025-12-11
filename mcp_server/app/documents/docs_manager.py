"""
Document Manager for handling document uploads and search
Uses ChromaDB for vector storage and retrieval
"""
from typing import Dict, List, Optional, Any
import os
import uuid
from datetime import datetime
import hashlib
import aiofiles
from pathlib import Path

import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# Document parsers
import PyPDF2
from docx import Document as DocxDocument
import json
import csv

from config.config import Config

class DocumentManager:
    def __init__(self, config: Config):
        self.config = config
        self.chroma_client = None
        self.collection = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.documents.chunk_size,
            chunk_overlap=config.documents.chunk_overlap,
            length_function=len,
        )
        
        # Ensure storage directory exists
        Path(config.documents.storage_path).mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize ChromaDB client and collection"""
        
        # Initialize ChromaDB client with new API
        self.chroma_client = chromadb.PersistentClient(
            path=self.config.chroma.persist_directory
        )
        
        # Get or create collection
        try:
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.config.documents.chroma_collection,
                metadata={"description": "Document embeddings for MCP server"}
            )
            print(f"✓ Initialized ChromaDB collection: {self.config.documents.chroma_collection}")
        except Exception as e:
            print(f"✗ Failed to initialize ChromaDB: {str(e)}")
            raise
    
    async def upload_document(
        self,
        content: str,
        filename: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Upload and index a document"""
        
        # Validate file format
        file_ext = filename.split('.')[-1].lower()
        if file_ext not in self.config.documents.supported_formats:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Generate document ID
        doc_id = str(uuid.uuid4())
        
        # Save file to storage
        file_path = os.path.join(
            self.config.documents.storage_path,
            f"{user_id}_{doc_id}_{filename}"
        )
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        # Parse document based on type
        try:
            parsed_content = await self._parse_document(file_path, file_ext)
        except Exception as e:
            os.remove(file_path)
            raise ValueError(f"Failed to parse document: {str(e)}")
        
        # Split into chunks
        chunks = self.text_splitter.split_text(parsed_content)
        
        # Create metadata for each chunk
        chunk_metadata = {
            "doc_id": doc_id,
            "filename": filename,
            "user_id": user_id,
            "upload_date": datetime.now().isoformat(),
            "file_type": file_ext,
            **(metadata or {})
        }
        
        # Add to ChromaDB
        chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        chunk_metadatas = [
            {**chunk_metadata, "chunk_index": i, "total_chunks": len(chunks)}
            for i in range(len(chunks))
        ]
        
        self.collection.add(
            documents=chunks,
            metadatas=chunk_metadatas,
            ids=chunk_ids
        )
        
        print(f"✓ Indexed document {filename} with {len(chunks)} chunks")
        
        return doc_id
    
    async def _parse_document(self, file_path: str, file_ext: str) -> str:
        """Parse document content based on file type"""
        
        if file_ext == 'txt' or file_ext == 'md':
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                return await f.read()
        
        elif file_ext == 'pdf':
            return self._parse_pdf(file_path)
        
        elif file_ext == 'docx':
            return self._parse_docx(file_path)
        
        elif file_ext == 'json':
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                data = json.loads(await f.read())
                return json.dumps(data, indent=2)
        
        elif file_ext == 'csv':
            return await self._parse_csv(file_path)
        
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
    
    def _parse_pdf(self, file_path: str) -> str:
        """Parse PDF file"""
        text = []
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text.append(page.extract_text())
        return '\n'.join(text)
    
    def _parse_docx(self, file_path: str) -> str:
        """Parse DOCX file"""
        doc = DocxDocument(file_path)
        return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    
    async def _parse_csv(self, file_path: str) -> str:
        """Parse CSV file"""
        text = []
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            reader = csv.DictReader(content.splitlines())
            for row in reader:
                text.append(json.dumps(row))
        return '\n'.join(text)
    
    async def search_documents(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search documents using semantic similarity"""
        
        # Build where clause for user filtering
        where_clause = {"user_id": user_id}
        if filter_metadata:
            where_clause.update(filter_metadata)
        
        # Query ChromaDB
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_clause
        )
        
        # Format results
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "content": doc,
                    "metadata": results['metadatas'][0][i],
                    "score": results['distances'][0][i] if results.get('distances') else None
                })
        
        return formatted_results
    
    async def get_document(self, doc_id: str, user_id: str) -> Dict[str, Any]:
        """Retrieve a specific document"""
        
        # Query all chunks for this document
        results = self.collection.get(
            where={
                "doc_id": doc_id,
                "user_id": user_id
            }
        )
        
        if not results['ids']:
            raise ValueError(f"Document {doc_id} not found")
        
        # Sort chunks by index
        chunks = sorted(
            zip(results['documents'], results['metadatas']),
            key=lambda x: x[1].get('chunk_index', 0)
        )
        
        # Combine chunks
        full_content = '\n'.join([chunk[0] for chunk in chunks])
        metadata = chunks[0][1] if chunks else {}
        
        return {
            "doc_id": doc_id,
            "content": full_content,
            "metadata": metadata,
            "chunk_count": len(chunks)
        }
    
    async def delete_document(self, doc_id: str, user_id: str):
        """Delete a document and its chunks"""
        
        # Get all chunk IDs for this document
        results = self.collection.get(
            where={
                "doc_id": doc_id,
                "user_id": user_id
            }
        )
        
        if not results['ids']:
            raise ValueError(f"Document {doc_id} not found")
        
        # Delete from ChromaDB
        self.collection.delete(ids=results['ids'])
        
        # Delete file from storage
        metadata = results['metadatas'][0] if results['metadatas'] else {}
        filename = metadata.get('filename', '')
        
        if filename:
            file_path = os.path.join(
                self.config.documents.storage_path,
                f"{user_id}_{doc_id}_{filename}"
            )
            if os.path.exists(file_path):
                os.remove(file_path)
        
        print(f"✓ Deleted document {doc_id}")
    
    async def list_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """List all documents for a user"""
        
        results = self.collection.get(
            where={"user_id": user_id}
        )
        
        # Group by doc_id
        docs = {}
        for metadata in results['metadatas']:
            doc_id = metadata.get('doc_id')
            if doc_id and doc_id not in docs:
                docs[doc_id] = {
                    "doc_id": doc_id,
                    "filename": metadata.get('filename'),
                    "upload_date": metadata.get('upload_date'),
                    "file_type": metadata.get('file_type'),
                    "chunk_count": 0
                }
            if doc_id:
                docs[doc_id]["chunk_count"] += 1
        
        return list(docs.values())
    
    async def update_document_metadata(
        self,
        doc_id: str,
        user_id: str,
        metadata: Dict[str, Any]
    ):
        """Update metadata for a document"""
        
        results = self.collection.get(
            where={
                "doc_id": doc_id,
                "user_id": user_id
            }
        )
        
        if not results['ids']:
            raise ValueError(f"Document {doc_id} not found")
        
        # Update metadata for all chunks
        updated_metadatas = []
        for existing_metadata in results['metadatas']:
            updated_metadata = {**existing_metadata, **metadata}
            updated_metadatas.append(updated_metadata)
        
        # Update in ChromaDB
        self.collection.update(
            ids=results['ids'],
            metadatas=updated_metadatas
        )
        
        print(f"✓ Updated metadata for document {doc_id}")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.chroma_client:
            # ChromaDB client doesn't need explicit cleanup
            print("✓ Document manager cleanup complete")
