"""
RAG Research Assistant - Interactive Chatbot
PAIC Econometrics Team - FAE Business School
"""

import os
import re
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

DOCUMENT_PATHS = [
    r"C:\Users\rodri\OneDrive - Grupo Marista\Doutorado\Doutorado_set2024\Doutorado\MultiObjective Optimization\Artigos",
    r"C:\Users\rodri\OneDrive - Grupo Marista\Doutorado\Doutorado_set2024\Doutorado\MultiObjective Optimization\Reinforcement Learning",
    r"C:\Users\rodri\OneDrive - Grupo Marista\Doutorado\Doutorado_set2024\Doutorado\MultiObjective Optimization\E-Books"
]

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

def clean_text(text):
    if text is None:
        return None
    if not isinstance(text, str):
        try:
            text = str(text)
        except:
            return None
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', text)
    text = ' '.join(text.split())
    if len(text) < 50:
        return None
    return text

import pandas as pd
from pypdf import PdfReader
from docx import Document as DocxDocument

class DocumentLoader:
    def __init__(self, base_paths):
        self.base_paths = [Path(p) for p in base_paths]
    
    def _load_pdf(self, file_path):
        try:
            reader = PdfReader(str(file_path))
            texts = []
            for p in reader.pages:
                t = p.extract_text()
                t = clean_text(t)
                if t:
                    texts.append(t)
            return " ".join(texts)
        except:
            return ""
    
    def _load_docx(self, file_path):
        try:
            doc = DocxDocument(str(file_path))
            texts = []
            for p in doc.paragraphs:
                t = clean_text(p.text)
                if t:
                    texts.append(t)
            return " ".join(texts)
        except:
            return ""
    
    def _load_excel(self, file_path):
        try:
            df = pd.read_excel(file_path)
            t = clean_text(df.to_string(index=False))
            return t if t else ""
        except:
            return ""
    
    def _load_text(self, file_path):
        try:
            text = file_path.read_text(encoding='utf-8', errors='ignore')
            return clean_text(text) or ""
        except:
            return ""
    
    def scan(self):
        loaders = {
            '.pdf': self._load_pdf,
            '.docx': self._load_docx,
            '.xlsx': self._load_excel,
            '.txt': self._load_text,
            '.md': self._load_text,
        }
        
        documents = []
        for base in self.base_paths:
            if not Path(base).exists():
                continue
            for f in Path(base).rglob("*"):
                if f.is_file() and f.suffix.lower() in loaders:
                    content = loaders[f.suffix.lower()](f)
                    content = clean_text(content)
                    if content:
                        documents.append({
                            'content': content,
                            'filename': f.name
                        })
        return documents


class TextChunker:
    def __init__(self, size=800, overlap=100):
        self.size = size
        self.overlap = overlap
    
    def chunk(self, documents):
        chunks = []
        for doc in documents:
            text = doc['content']
            if not text:
                continue
            start = 0
            idx = 0
            while start < len(text):
                chunk_text = text[start:start + self.size]
                chunk_text = clean_text(chunk_text)
                if chunk_text:
                    chunks.append({
                        'content': chunk_text,
                        'filename': doc['filename'],
                        'chunk_id': idx
                    })
                    idx += 1
                start += self.size - self.overlap
        return chunks


from sentence_transformers import SentenceTransformer
import numpy as np
import google.generativeai as genai

class RAGSystem:
    def __init__(self, api_key):
        print("Loading embedding model...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        print("Configuring Gemini...")
        genai.configure(api_key=api_key)
        self.llm = genai.GenerativeModel('gemini-2.0-flash')
        
        self.chunks = []
        self.embeddings = None
        print("RAG System ready!")
    
    def index(self, chunks):
        valid_chunks = []
        valid_texts = []
        
        for c in chunks:
            content = c.get('content', '')
            content = clean_text(content)
            if content and isinstance(content, str) and len(content) >= 50:
                valid_chunks.append(c)
                valid_texts.append(content)
        
        total = len(valid_texts)
        print("Indexing " + str(total) + " chunks one by one...")
        
        embeddings_list = []
        final_chunks = []
        
        for i, text in enumerate(valid_texts):
            try:
                emb = self.embedder.encode([text], show_progress_bar=False)
                embeddings_list.append(emb[0])
                final_chunks.append(valid_chunks[i])
            except Exception as e:
                print("Skipped chunk " + str(i) + ": " + str(e)[:50])
            
            if (i + 1) % 500 == 0:
                pct = int(100 * (i + 1) / total)
                print("Progress: " + str(i + 1) + "/" + str(total) + " (" + str(pct) + "%)")
        
        self.chunks = final_chunks
        self.embeddings = np.array(embeddings_list)
        print("Done! Indexed " + str(len(final_chunks)) + " chunks")
    
    def search(self, query, top_k=5):
        query_emb = self.embedder.encode(query)
        similarities = np.dot(self.embeddings, query_emb) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_emb)
        )
        top_idx = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_idx:
            if idx < len(self.chunks):
                result = dict(self.chunks[idx])
                result['score'] = float(similarities[idx])
                results.append(result)
        return results
    
    def query(self, question):
        results = self.search(question, top_k=5)
        
        context_parts = []
        for r in results:
            context_parts.append("[" + r['filename'] + "]\n" + r['content'])
        context = "\n\n---\n\n".join(context_parts)
        
        prompt = """You are a research assistant analyzing scientific documents about 
portfolio optimization, reinforcement learning, and financial modeling.

Based on the following context, answer the question. Cite sources when possible.

Context:
""" + context + """

Question: """ + question + """

Answer:"""
        
        response = self.llm.generate_content(prompt)
        
        source_lines = []
        for r in results[:3]:
            score_pct = str(int(r['score'] * 100)) + "%"
            source_lines.append("- " + r['filename'] + " (" + score_pct + ")")
        sources = "\n".join(source_lines)
        
        return response.text + "\n\n**Sources:**\n" + sources


def create_interface():
    import gradio as gr
    
    print("=" * 50)
    print("RAG RESEARCH ASSISTANT")
    print("=" * 50)
    
    if not GOOGLE_API_KEY:
        print("ERROR: GOOGLE_API_KEY not set!")
        return None
    
    print("\nLoading documents...")
    loader = DocumentLoader(DOCUMENT_PATHS)
    documents = loader.scan()
    print("Found " + str(len(documents)) + " documents")
    
    chunker = TextChunker(size=800, overlap=100)
    chunks = chunker.chunk(documents)
    print("Created " + str(len(chunks)) + " chunks")
    
    rag = RAGSystem(GOOGLE_API_KEY)
    rag.index(chunks)
    
    def chat(message, history):
        if not message.strip():
            return ""
        try:
            return rag.query(message)
        except Exception as e:
            return "Error: " + str(e)
          
    demo = gr.ChatInterface(
        fn=chat,
        title="RAG Research Assistant",
        description="PAIC Econometrics - FAE Business School",
        examples=[
            "What is multi-objective portfolio optimization?",
            "Explain reinforcement learning in trading",
            "What is NSGA-II?",
        ]
    )
    return demo


if __name__ == "__main__":
    demo = create_interface()
    if demo:
        print("\nOpening http://localhost:7860")
        demo.launch(share=False)
