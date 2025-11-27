"""Simple TF-IDF based retriever for local documents."""
import os
import re
from pathlib import Path
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class DocumentChunk:
    def __init__(self, id: str, content: str, source: str, metadata: Dict = None):
        self.id = id
        self.content = content
        self.source = source
        self.metadata = metadata or {}
    
    def __repr__(self):
        return f"Chunk({self.id}, source={self.source})"


class TFIDFRetriever:
    def __init__(self, docs_dir: str = "docs"):
        self.docs_dir = Path(docs_dir)
        self.chunks: List[DocumentChunk] = []
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.tfidf_matrix = None
        self._load_and_chunk_documents()
    
    def _load_and_chunk_documents(self):
        """Load all markdown files and chunk them."""
        if not self.docs_dir.exists():
            raise FileNotFoundError(f"Docs directory not found: {self.docs_dir}")
        
        for filepath in self.docs_dir.glob("*.md"):
            content = filepath.read_text(encoding='utf-8')
            source = filepath.stem
            
            # Simple paragraph-based chunking
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            
            for idx, para in enumerate(paragraphs):
                chunk_id = f"{source}::chunk{idx}"
                self.chunks.append(DocumentChunk(
                    id=chunk_id,
                    content=para,
                    source=source
                ))
        
        if not self.chunks:
            raise ValueError("No documents found to index")
        
        # Build TF-IDF matrix
        corpus = [chunk.content for chunk in self.chunks]
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
    
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve top-k most relevant chunks."""
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            chunk = self.chunks[idx]
            results.append({
                'id': chunk.id,
                'content': chunk.content,
                'source': chunk.source,
                'score': float(similarities[idx])
            })
        
        return results
    
    def get_all_chunks(self) -> List[DocumentChunk]:
        """Return all chunks (useful for debugging)."""
        return self.chunks