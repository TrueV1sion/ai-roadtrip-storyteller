"""
Semantic embedding generation for code understanding
"""
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import openai
from sentence_transformers import SentenceTransformer
import numpy as np
import tiktoken


@dataclass
class CodeEmbedding:
    """Represents an embedding for a code snippet"""
    text: str
    embedding: List[float]
    model: str
    metadata: Dict[str, Any]


class EmbeddingGenerator:
    """Generate semantic embeddings for code"""
    
    def __init__(self, openai_api_key: Optional[str] = None, 
                 use_local_model: bool = True):
        self.use_local_model = use_local_model
        
        if use_local_model:
            # Use local model for cost efficiency
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.model_name = 'all-MiniLM-L6-v2'
        else:
            # Use OpenAI for higher quality
            openai.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            self.model_name = 'text-embedding-ada-002'
            self.encoding = tiktoken.encoding_for_model(self.model_name)
    
    def generate_embedding(self, text: str, metadata: Optional[Dict] = None) -> CodeEmbedding:
        """Generate embedding for a code snippet"""
        # Preprocess code for better embeddings
        processed_text = self._preprocess_code(text)
        
        if self.use_local_model:
            embedding = self.model.encode(processed_text).tolist()
        else:
            response = openai.Embedding.create(
                input=processed_text,
                model=self.model_name
            )
            embedding = response['data'][0]['embedding']
        
        return CodeEmbedding(
            text=text,
            embedding=embedding,
            model=self.model_name,
            metadata=metadata or {}
        )
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[CodeEmbedding]:
        """Generate embeddings for multiple code snippets"""
        if self.use_local_model:
            processed_texts = [self._preprocess_code(t) for t in texts]
            embeddings = self.model.encode(processed_texts).tolist()
            
            return [
                CodeEmbedding(
                    text=text,
                    embedding=emb,
                    model=self.model_name,
                    metadata={}
                )
                for text, emb in zip(texts, embeddings)
            ]
        else:
            # OpenAI batch processing
            results = []
            for text in texts:
                results.append(self.generate_embedding(text))
            return results
    
    def _preprocess_code(self, code: str) -> str:
        """Preprocess code for better semantic understanding"""
        # Remove excessive whitespace
        lines = code.split('\n')
        processed_lines = []
        
        for line in lines:
            # Remove leading/trailing whitespace
            line = line.strip()
            
            # Skip empty lines and pure comment lines
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            
            # Add meaningful context
            if 'import' in line or 'from' in line:
                line = f"[IMPORT] {line}"
            elif 'class' in line:
                line = f"[CLASS] {line}"
            elif 'def' in line:
                line = f"[FUNCTION] {line}"
            elif 'return' in line:
                line = f"[RETURNS] {line}"
            
            processed_lines.append(line)
        
        return ' '.join(processed_lines)[:2000]  # Limit length
    
    def calculate_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))


class CodeContextBuilder:
    """Build rich context for code embeddings"""
    
    @staticmethod
    def build_file_context(file_path: str, content: str) -> str:
        """Build context string for a file"""
        file_type = file_path.split('.')[-1] if '.' in file_path else 'unknown'
        
        context_parts = [
            f"FILE: {file_path}",
            f"TYPE: {file_type}",
        ]
        
        # Extract key elements
        if file_type == 'py':
            imports = [line for line in content.split('\n') if line.strip().startswith(('import', 'from'))]
            classes = [line for line in content.split('\n') if 'class ' in line]
            functions = [line for line in content.split('\n') if 'def ' in line]
            
            if imports:
                context_parts.append(f"IMPORTS: {len(imports)} modules")
            if classes:
                context_parts.append(f"CLASSES: {len(classes)} defined")
            if functions:
                context_parts.append(f"FUNCTIONS: {len(functions)} defined")
        
        # Add content summary
        context_parts.append(f"CONTENT: {content[:500]}")
        
        return ' | '.join(context_parts)
    
    @staticmethod
    def build_function_context(func_name: str, func_code: str, 
                             file_path: str, class_name: Optional[str] = None) -> str:
        """Build context string for a function"""
        context_parts = [
            f"FUNCTION: {func_name}",
            f"FILE: {file_path}",
        ]
        
        if class_name:
            context_parts.append(f"CLASS: {class_name}")
        
        # Extract function signature
        lines = func_code.split('\n')
        if lines:
            context_parts.append(f"SIGNATURE: {lines[0].strip()}")
        
        # Look for return statements
        returns = [line.strip() for line in lines if 'return' in line]
        if returns:
            context_parts.append(f"RETURNS: {returns[0]}")
        
        # Add docstring if present
        if '"""' in func_code or "'''" in func_code:
            context_parts.append("HAS_DOCSTRING: yes")
        
        return ' | '.join(context_parts)