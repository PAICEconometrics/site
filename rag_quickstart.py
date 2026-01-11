"""
PAIC RAG Research Assistant - Quick Start Script
================================================

This script helps you quickly test the RAG system with your documents.

SETUP:
1. Install dependencies:
   pip install chromadb sentence-transformers pypdf python-docx openpyxl pandas google-generativeai python-dotenv

2. Set your API key (choose ONE method):
   
   Method A - Environment Variable (RECOMMENDED):
   Windows CMD:    set GOOGLE_API_KEY=your_key_here
   Windows PS:     $env:GOOGLE_API_KEY="your_key_here"
   Linux/Mac:      export GOOGLE_API_KEY=your_key_here
   
   Method B - .env file:
   Create a file named ".env" in the same folder with:
   GOOGLE_API_KEY=your_key_here

3. Update DOCUMENT_PATHS below with your folders

4. Run: python rag_quickstart.py
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Try to load .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env file")
except ImportError:
    print("ℹ️ python-dotenv not installed, using system environment variables")

# ============================================================
# CONFIGURATION - UPDATE THESE PATHS!
# ============================================================

DOCUMENT_PATHS = [
    r"C:\Users\rodri\OneDrive - Grupo Marista\Doutorado\Doutorado_set2024\Doutorado\MultiObjective Optimization\Artigos",
    r"C:\Users\rodri\OneDrive - Grupo Marista\Doutorado\Doutorado_set2024\Doutorado\MultiObjective Optimization\Reinforcement Learning",
    r"C:\Users\rodri\OneDrive - Grupo Marista\Doutorado\Doutorado_set2024\Doutorado\MultiObjective Optimization\E-Books"
]

# Vector database storage location
PERSIST_DIRECTORY = "./paic_vectordb"

# Collection name in ChromaDB
COLLECTION_NAME = "paic_research"

# ============================================================
# IMPORTS
# ============================================================

print("\n🔄 Loading libraries...")

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
from pypdf import PdfReader
from docx import Document as DocxDocument
from sentence_transformers import SentenceTransformer
import chromadb

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ google-generativeai not installed. Run: pip install google-generativeai")

print("✅ Libraries loaded!")

# ============================================================
# CHECK API KEY
# ============================================================

API_KEY = os.environ.get("GOOGLE_API_KEY")

if not API_KEY:
    print("\n" + "="*60)
    print("❌ ERROR: GOOGLE_API_KEY not found!")
    print("="*60)
    print("\nPlease set your API key using one of these methods:")
    print("\n1. Environment variable:")
    print("   Windows: set GOOGLE_API_KEY=your_key_here")
    print("   Linux:   export GOOGLE_API_KEY=your_key_here")
    print("\n2. Create a .env file with:")
    print("   GOOGLE_API_KEY=your_key_here")
    print("\nGet your FREE key at: https://makersuite.google.com/app/apikey")
    print("="*60)
    sys.exit(1)
else:
    # Show only first/last 4 chars for security
    masked_key = API_KEY[:4] + "..." + API_KEY[-4:]
    print(f"✅ API Key found: {masked_key}")

# ============================================================
# DOCUMENT LOADER CLASS
# ============================================================

class DocumentLoader:
    """Multi-format document loader."""
    
    def __init__(self, base_paths: List[str]):
        self.base_paths = [Path(p) for p in base_paths]
        self.supported_extensions = {
            '.pdf': self._load_pdf,
            '.docx': self._load_docx,
            '.xlsx': self._load_excel,
            '.csv': self._load_csv,
            '.txt': self._load_text,
            '.md': self._load_text
        }
    
    def _load_pdf(self, file_path: Path) -> str:
        try:
            reader = PdfReader(str(file_path))
            return "\n\n".join([p.extract_text() or "" for p in reader.pages])
        except Exception as e:
            print(f"  ⚠️ Error loading {file_path.name}: {e}")
            return ""
    
    def _load_docx(self, file_path: Path) -> str:
        try:
            doc = DocxDocument(str(file_path))
            return "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        except Exception as e:
            print(f"  ⚠️ Error loading {file_path.name}: {e}")
            return ""
    
    def _load_excel(self, file_path: Path) -> str:
        try:
            xl = pd.ExcelFile(file_path)
            parts = []
            for sheet in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=sheet)
                parts.append(f"## Sheet: {sheet}\n{df.to_string(index=False)}")
            return "\n\n".join(parts)
        except Exception as e:
            print(f"  ⚠️ Error loading {file_path.name}: {e}")
            return ""
    
    def _load_csv(self, file_path: Path) -> str:
        try:
            df = pd.read_csv(file_path)
            return f"## CSV: {file_path.name}\n{df.to_string(index=False)}"
        except Exception as e:
            print(f"  ⚠️ Error loading {file_path.name}: {e}")
            return ""
    
    def _load_text(self, file_path: Path) -> str:
        try:
            for enc in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    return file_path.read_text(encoding=enc)
                except UnicodeDecodeError:
                    continue
            return ""
        except Exception as e:
            print(f"  ⚠️ Error loading {file_path.name}: {e}")
            return ""
    
    def scan_directories(self) -> List[Dict[str, Any]]:
        documents = []
        for base_path in self.base_paths:
            if not base_path.exists():
                print(f"⚠️ Path not found: {base_path}")
                continue
            
            print(f"\n📂 Scanning: {base_path.name}")
            
            for file_path in base_path.rglob("*"):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in self.supported_extensions:
                        content = self.supported_extensions[ext](file_path)
                        if content.strip():
                            documents.append({
                                'content': content,
                                'metadata': {
                                    'source': str(file_path),
                                    'filename': file_path.name,
                                    'extension': ext
                                }
                            })
                            print(f"  ✓ {file_path.name}")
        
        print(f"\n✅ Loaded {len(documents)} documents")
        return documents

# ============================================================
# TEXT CHUNKER
# ============================================================

class TextChunker:
    """Split documents into chunks."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_documents(self, documents: List[Dict]) -> List[Dict]:
        all_chunks = []
        for doc in documents:
            text = doc['content']
            chunks = []
            start = 0
            while start < len(text):
                end = start + self.chunk_size
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append({
                        'content': chunk_text,
                        'metadata': {
                            **doc['metadata'],
                            'chunk_id': len(chunks)
                        }
                    })
                start = end - self.chunk_overlap
            all_chunks.extend(chunks)
        
        print(f"✅ Created {len(all_chunks)} chunks")
        return all_chunks

# ============================================================
# RAG ASSISTANT
# ============================================================

class RAGAssistant:
    """Simple RAG assistant."""
    
    def __init__(self):
        print("\n🚀 Initializing RAG Assistant...")
        
        # Embedding model
        print("  Loading embedding model...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Vector store
        print("  Initializing vector store...")
        self.client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        
        # LLM
        print("  Configuring Gemini...")
        genai.configure(api_key=API_KEY)
        self.llm = genai.GenerativeModel('gemini-1.5-flash')
        
        print("✅ RAG Assistant ready!")
        print(f"   Documents in index: {self.collection.count()}")
    
    def index_documents(self, documents: List[Dict], chunks: List[Dict]):
        """Index document chunks."""
        if self.collection.count() > 0:
            print(f"ℹ️ Index already has {self.collection.count()} chunks. Skipping.")
            return
        
        print("\n🔄 Generating embeddings...")
        texts = [c['content'] for c in chunks]
        embeddings = self.embedder.encode(texts, show_progress_bar=True).tolist()
        
        print("💾 Storing in vector database...")
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        metadatas = [c['metadata'] for c in chunks]
        
        # Add in batches
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            end = min(i + batch_size, len(chunks))
            self.collection.add(
                ids=ids[i:end],
                embeddings=embeddings[i:end],
                documents=texts[i:end],
                metadatas=metadatas[i:end]
            )
        
        print(f"✅ Indexed {len(chunks)} chunks!")
    
    def query(self, question: str, n_results: int = 5) -> Dict:
        """Query the RAG system."""
        # Get query embedding
        query_emb = self.embedder.encode(question).tolist()
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_emb],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        # Build context
        context_parts = []
        sources = []
        for i, (doc, meta, dist) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            context_parts.append(f"[Source {i+1}: {meta['filename']}]\n{doc}")
            sources.append({
                'filename': meta['filename'],
                'relevance': f"{(1-dist)*100:.1f}%"
            })
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Generate response
        prompt = f"""You are a helpful research assistant. Answer the question based on the provided context.

## Context from Research Documents:
{context}

## Question:
{question}

## Instructions:
- Base your answer on the provided context
- Cite specific sources when possible
- If the context doesn't contain relevant information, say so
- Be precise and academic

## Answer:"""
        
        response = self.llm.generate_content(prompt)
        
        return {
            'answer': response.text,
            'sources': sources
        }

# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    print("\n" + "="*60)
    print("🔬 PAIC RAG Research Assistant")
    print("="*60)
    
    # Initialize
    rag = RAGAssistant()
    
    # Check if we need to index
    if rag.collection.count() == 0:
        print("\n📚 First run - indexing documents...")
        
        # Load documents
        loader = DocumentLoader(DOCUMENT_PATHS)
        documents = loader.scan_directories()
        
        if documents:
            # Chunk documents
            chunker = TextChunker()
            chunks = chunker.chunk_documents(documents)
            
            # Index
            rag.index_documents(documents, chunks)
        else:
            print("⚠️ No documents found. Check your DOCUMENT_PATHS.")
            return
    
    # Interactive loop
    print("\n" + "="*60)
    print("💬 Chat Mode - Type your questions (or 'quit' to exit)")
    print("="*60)
    
    while True:
        try:
            question = input("\n❓ You: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            print("\n🔄 Searching and generating response...")
            result = rag.query(question)
            
            print(f"\n💡 Answer:\n{result['answer']}")
            
            print("\n📚 Sources:")
            for i, src in enumerate(result['sources'], 1):
                print(f"   {i}. {src['filename']} ({src['relevance']})")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
