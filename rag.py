import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

KB_DIR = os.getenv("KB_DIR", "./knowledge_base")
DB_DIR = os.getenv("DB_DIR", "./chroma_db")

class KnowledgeBase:
    def __init__(self):
        # Initialize local embeddings (runs on CPU, no API key needed)
        self.embedding_func = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = Chroma(
            collection_name="arch_patterns",
            embedding_function=self.embedding_func,
            persist_directory=DB_DIR
        )

    def ingest(self):
        """Scans the KB folder and ingests documents."""
        if not os.path.exists(KB_DIR):
            os.makedirs(KB_DIR)
            return "Folder created. Please add PDFs."

        loader = DirectoryLoader(KB_DIR, glob="**/*.pdf")
        docs = loader.load()
        
        if not docs:
            return "No PDFs found to ingest."

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = splitter.split_documents(docs)
        self.vector_store.add_documents(splits)
        return f"Ingested {len(splits)} architectural patterns."

    def search(self, query: str, k: int = 4) -> str:
        """Retrieves context relevant to the query."""
        try:
            results = self.vector_store.similarity_search(query, k=k)
            if not results:
                return "No specific knowledge found."
            
            return "\n\n".join([f"[Source: {d.metadata.get('source', 'Unknown')}]\n{d.page_content}" for d in results])
        except Exception:
            return "Knowledge Base unavailable (Did you run ingest?)"

# Global instance
kb = KnowledgeBase()