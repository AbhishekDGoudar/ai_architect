import os
import shutil
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader, UnstructuredPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

KB_DIR = os.getenv("KB_DIR", "./knowledge_base")
DB_DIR = os.getenv("DB_DIR", "./chroma_db")
UPLOAD_DIR = "./temp_uploads"

class KnowledgeEngine:
    def __init__(self):
        # 1. Web Search
        self.web_wrapper = DuckDuckGoSearchAPIWrapper(region="wt-wt", time="y", max_results=5)
        self.web_tool = DuckDuckGoSearchRun(api_wrapper=self.web_wrapper)
        
        # 2. Local RAG
        self.embedding_func = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = Chroma(
            collection_name="arch_patterns",
            embedding_function=self.embedding_func,
            persist_directory=DB_DIR
        )
        
        # Ensure directories exist
        os.makedirs(KB_DIR, exist_ok=True)
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    def ingest_directory(self):
        """Scans the persistent KB_DIR."""
        return self._process_folder(KB_DIR)

    def ingest_upload(self, uploaded_file):
        """
        Takes a Streamlit UploadedFile, saves it, and ingests it.
        """
        try:
            file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Load based on extension
            if file_path.endswith(".pdf"):
                loader = UnstructuredPDFLoader(file_path)
            else:
                loader = TextLoader(file_path)
                
            docs = loader.load()
            self._add_docs_to_db(docs)
            
            return f"✅ Ingested {uploaded_file.name}"
        except Exception as e:
            return f"❌ Failed to ingest {uploaded_file.name}: {str(e)}"

    def _process_folder(self, folder_path):
        """Helper to process all PDFs in a folder."""
        if not os.path.exists(folder_path): return "Folder not found."
        
        loader = DirectoryLoader(folder_path, glob="**/*.pdf", loader_cls=UnstructuredPDFLoader)
        docs = loader.load()
        if not docs: return "No new files found."
        
        return self._add_docs_to_db(docs)

    def _add_docs_to_db(self, docs):
        """Splits and adds documents to Chroma."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = splitter.split_documents(docs)
        self.vector_store.add_documents(splits)
        return f"Indexed {len(splits)} chunks."

    def search(self, query: str, use_web=True, use_kb=True) -> str:
        report = []
        
        if use_web:
            try:
                web_results = self.web_tool.invoke(f"{query} software architecture limits")
                report.append(f"=== 🌐 WEB SEARCH ===\n{web_results}")
            except: pass

        if use_kb:
            try:
                # We search for slightly more results since we have user files now
                results = self.vector_store.similarity_search(query, k=5)
                if results:
                    content = "\n".join([f"- {d.page_content[:400]}..." for d in results])
                    report.append(f"=== 📂 UPLOADED CONTEXT & KB ===\n{content}")
            except: pass

        return "\n\n".join(report)

    def clear_uploads(self):
        """Clears the temp uploads folder."""
        if os.path.exists(UPLOAD_DIR):
            shutil.rmtree(UPLOAD_DIR)
            os.makedirs(UPLOAD_DIR)

knowledge = KnowledgeEngine()