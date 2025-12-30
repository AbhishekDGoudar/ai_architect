import os
import openai
import asyncio
import aiofiles
import numpy as np
import fitz  # PyMuPDF for PDF loading
from typing import List, Optional
from tqdm import tqdm  # For progress bar during batching
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader, UnstructuredPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.documents import Document
from tqdm import tqdm


import os
import fitz  # PyMuPDF
from typing import List, Optional
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# LangChain Imports
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class KnowledgeEngine:
    def __init__(self, openai_api_key: str, db_dir: str = "./chroma_db", kb_dir: str = "./knowledge_base"):
        print("--- [INIT] Initializing KnowledgeEngine ---")
        self.kb_dir = kb_dir
        self.upload_dir = "./temp_uploads"
        
        # 1. Setup OpenAI Embeddings
        self.embedding_func = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=openai_api_key,
            # Improve client side batching if needed, though we handle it manually below
            chunk_size=1000 
        )
        
        # 2. Connect to ChromaDB
        self.vector_store = Chroma(
            collection_name="arch_patterns",
            embedding_function=self.embedding_func,
            persist_directory=db_dir
        )
        
        os.makedirs(self.kb_dir, exist_ok=True)
        os.makedirs(self.upload_dir, exist_ok=True)
        print("--- [INIT] Ready. ---\n")

    def _load_single_file(self, file_path: str) -> List[Document]:
        """Helper to load a single file based on extension."""
        try:
            if file_path.lower().endswith(".pdf"):
                loader = PyMuPDFLoader(file_path)
                return loader.load()
            elif file_path.lower().endswith(".txt"):
                loader = TextLoader(file_path, encoding='utf-8')
                return loader.load()
            return []
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return []

    def ingest_directory(self) -> str:
        """Ingests all files in the knowledge base directory using Multithreading."""
        print(f"--- [BATCH INGEST] Scanning directory: {self.kb_dir} ---")
        
        all_files = []
        # Walk directory to find all valid files
        for root, _, files in os.walk(self.kb_dir):
            for file in files:
                if file.lower().endswith(('.pdf', '.txt')):
                    all_files.append(os.path.join(root, file))

        if not all_files:
            return "No files found."

        print(f"  > Found {len(all_files)} files. Loading in parallel...")
        
        docs = []
        # Use ThreadPool to load files concurrently (IO Bound)
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_file = {executor.submit(self._load_single_file, fp): fp for fp in all_files}
            
            for future in tqdm(as_completed(future_to_file), total=len(all_files), desc="Loading Files", unit="file"):
                docs.extend(future.result())
        
        print(f"  > Total documents loaded: {len(docs)}")
        return self._add_docs_to_db(docs)

    def _add_docs_to_db(self, docs: List[Document], cleanup_path: Optional[str] = None) -> str:
        """
        Splits and adds documents to the vector store concurrently.
        """
        print("  > Splitting documents into chunks...")
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = splitter.split_documents(docs)
        print(f"  > Created {len(splits)} chunks.")
        
        if not splits:
            return "No content to index."

        print("  > Embedding and Indexing (Concurrent Batches)...")
        
        # Batch size optimized for OpenAI limits vs Network latency
        batch_size = 200 
        batches = [splits[i:i + batch_size] for i in range(0, len(splits), batch_size)]
        
        # Function to process a single batch
        def process_batch(batch_docs):
            try:
                self.vector_store.add_documents(batch_docs)
                return len(batch_docs)
            except Exception as e:
                print(f"Batch failed: {e}")
                return 0

        # Run batches in parallel
        # Note: Chroma (SQLite) handles concurrency reasonably well, but don't go too high on workers
        total_indexed = 0
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_batch, b) for b in batches]
            
            with tqdm(total=len(splits), desc="Indexing Chunks", unit="chunk") as pbar:
                for future in as_completed(futures):
                    count = future.result()
                    total_indexed += count
                    pbar.update(count)
        
        if cleanup_path and os.path.exists(cleanup_path):
            os.remove(cleanup_path)
            print(f"  > Cleaned up temp file.")
            
        return f"Success: Indexed {total_indexed} chunks."

    def search(self, query: str, k: int = 4, score_threshold: float = 0.5) -> Optional[str]:
        # (Same as your original code)
        try:
            results = self.vector_store.similarity_search_with_relevance_scores(query, k=k)
            if not results: return None
            
            valid_results = [doc for doc, score in results if score >= score_threshold]
            if not valid_results: return None
            
            return "\n\n".join([f"[Source: {doc.metadata.get('source', 'Unknown')}]\n{doc.page_content}" for doc in valid_results])
        except Exception as e:
            print(f"Search Error: {str(e)}")
            return None
class WebKnowledgeEngine:
    def __init__(self):
        # Setup DuckDuckGo
        self.web_wrapper = DuckDuckGoSearchAPIWrapper(region="wt-wt", time="y", max_results=5)
        self.web_tool = DuckDuckGoSearchRun(api_wrapper=self.web_wrapper)

    def search(self, query: str) -> str:
        """Searches the public web."""
        try:
            results = self.web_tool.invoke(query)
            return f"**WEB RESULTS:**\n{results}"
        except Exception as e:
            return f"Web Search Error: {str(e)}"