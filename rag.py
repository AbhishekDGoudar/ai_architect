import os
import shutil
from datetime import date
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader, UnstructuredPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Configuration
KB_DIR = os.getenv("KB_DIR", "./knowledge_base")
DB_DIR = os.getenv("DB_DIR", "./chroma_db")
UPLOAD_DIR = "./temp_uploads"

class KnowledgeEngine:
    def __init__(self):
        # Web Search setup
        self.web_wrapper = DuckDuckGoSearchAPIWrapper(region="wt-wt", time="y", max_results=5)
        self.web_tool = DuckDuckGoSearchRun(api_wrapper=self.web_wrapper)

        # Local RAG (Chroma + HuggingFace embeddings)
        self.embedding_func = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = Chroma(
            collection_name="arch_patterns",
            embedding_function=self.embedding_func,
            persist_directory=DB_DIR
        )

        # Ensure directories exist
        os.makedirs(KB_DIR, exist_ok=True)
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Ingestion
    def ingest_directory(self):
        """Scans persistent KB_DIR and ingests files."""
        return self._process_folder(KB_DIR)

    def ingest_upload(self, uploaded_file):
        """Ingest a Streamlit UploadedFile immediately."""
        try:
            file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            loader = UnstructuredPDFLoader(file_path) if file_path.endswith(".pdf") else TextLoader(file_path)
            docs = loader.load()
            return self._add_docs_to_db(docs)
        except Exception as e:
            return f"Failed to ingest {uploaded_file.name}: {str(e)}"

    def _process_folder(self, folder_path):
        """Process all PDFs and text files in a folder."""
        if not os.path.exists(folder_path):
            return "Folder not found."

        pdf_loader = DirectoryLoader(folder_path, glob="**/*.pdf", loader_cls=UnstructuredPDFLoader)
        docs = pdf_loader.load()

        txt_loader = DirectoryLoader(folder_path, glob="**/*.txt", loader_cls=TextLoader)
        docs.extend(txt_loader.load())

        if not docs:
            return "No new files found."
        return self._add_docs_to_db(docs)

    def _add_docs_to_db(self, docs):
        """Splits and adds documents to Chroma."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = splitter.split_documents(docs)
        if splits:
            self.vector_store.add_documents(splits)
            return f"Indexed {len(splits)} chunks from {len(docs)} files."
        return "No content chunks created."

    # Search
    def search(self, query: str, use_web=True, use_kb=True) -> str:
        """Perform a hybrid search using web and local RAG."""
        report = []

        today = date.today().isoformat()
        query = f"{query} (as of {today})"

        if use_web:
            try:
                web_results = self.web_tool.invoke(f"{query} software architecture patterns limits")
                report.append(f"WEB SEARCH RESULTS:\n{web_results}")
            except Exception as e:
                report.append(f"Web Search Error: {e}")

        if use_kb:
            try:
                results = self.vector_store.similarity_search(query, k=4)
                if results:
                    content = "\n".join([f"- {d.page_content[:400]}..." for d in results])
                    report.append(f"KNOWLEDGE BASE RESULTS:\n{content}")
                else:
                    report.append("KNOWLEDGE BASE RESULTS:\nNo relevant documents found")
            except Exception as e:
                report.append(f"KB Error: {e}")

        return "\n\n".join(report)

    # Utility
    def clear_uploads(self):
        """Clears the temp uploads folder."""
        if os.path.exists(UPLOAD_DIR):
            shutil.rmtree(UPLOAD_DIR)
            os.makedirs(UPLOAD_DIR)

# Singleton instances
knowledge = KnowledgeEngine()
kb = knowledge
