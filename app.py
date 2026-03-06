import os
import glob
import shutil
from pathlib import Path
from typing import List, Optional

import pdfplumber
import streamlit as st

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate


# ---------- CONFIG ----------

ROOT = Path(".").resolve()
PDF_DIR = ROOT / "downloads" / "newpdf"
IMPORTED_DIR = ROOT / "downloads" / "imported"
TXT_DIR = ROOT / "documents"
DB_DIR = ROOT / "chroma_db"

EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "deepseek-r1:14b"  # Ollama model tag [web:207][web:204]


# ---------- UTIL: STRIP DEEPSEEK THINKING ----------

def strip_deepseek_thinking(raw: str) -> str:
    """
    DeepSeek-R1 style:
      <think>...</think><answer>...</answer>
    Return only the <answer> section if present.
    """
    lower = raw.lower()
    start = lower.find("<answer>")
    end = lower.rfind("</answer>")
    if start != -1 and end != -1 and end > start:
        return raw[start + len("<answer>"):end].strip()
    return raw.strip()


# ---------- UTIL: IMPORT NEW PDFs ----------

def import_new_pdfs() -> str:
    """
    Import all new PDFs from downloads/newpdf/,
    write TXT to documents/, add to Chroma, and move PDFs to downloads/imported/.
    Returns a log string for display.
    """
    log_lines: List[str] = []

    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(IMPORTED_DIR, exist_ok=True)
    os.makedirs(TXT_DIR, exist_ok=True)

    log_lines.append(f"Looking for PDFs in: {PDF_DIR}")

    pdf_paths = sorted(
        [Path(p) for p in glob.glob(str(PDF_DIR / '*.pdf'))]
        + [Path(p) for p in glob.glob(str(PDF_DIR / '*.PDF'))]
    )

    if not pdf_paths:
        log_lines.append("No PDFs found.")
        return "\n".join(log_lines)

    def pdf_to_txt(pdf_path: Path) -> Optional[Path]:
        base_name = pdf_path.stem
        txt_path = TXT_DIR / f"{base_name}.txt"

        # Skip if TXT already exists
        if txt_path.exists():
            log_lines.append(f"Skipping (TXT exists): {pdf_path.name} -> {txt_path.name}")
            return None

        log_lines.append(f"\nExtracting: {pdf_path.name} -> {txt_path.name}")

        all_text = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            log_lines.append(f"  Pages: {len(pdf.pages)}")
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                all_text.append(text)
                if (i + 1) % 5 == 0 or i == len(pdf.pages) - 1:
                    log_lines.append(f"  Processed {i + 1}/{len(pdf.pages)} pages")

        full_text = "\n\n".join(all_text).strip()
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        log_lines.append(f"  Saved {txt_path.name} ({len(full_text)} chars)")
        return txt_path

    # 1) Convert all PDFs to TXT (skipping ones already done)
    txt_paths: List[Path] = []
    processed_pdfs: List[Path] = []

    for pdf_path in pdf_paths:
        txt_path = pdf_to_txt(pdf_path)
        if txt_path is not None:
            txt_paths.append(txt_path)
            processed_pdfs.append(pdf_path)

    if not txt_paths:
        log_lines.append("\nNo new TXT files created; nothing to add to DB.")
    else:
        # 2) Load TXT and add to Chroma
        log_lines.append("\nUpdating Chroma DB...")

        embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        db = Chroma(persist_directory=str(DB_DIR), embedding_function=embeddings)

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

        new_chunks: List[Document] = []
        for txt_path in txt_paths:
            loader = TextLoader(str(txt_path), encoding="utf-8")
            docs = loader.load()
            for d in docs:
                d.metadata["source"] = txt_path.name
            chunks = splitter.split_documents(docs)
            new_chunks.extend(chunks)
            log_lines.append(f"  Prepared {len(chunks)} chunks from {txt_path.name}")

        if new_chunks:
            db.add_documents(new_chunks)
            log_lines.append(f"\nAdded {len(new_chunks)} chunks to DB")
            data = db.get()
            sources = sorted({m.get("source") for m in data["metadatas"] if m})
            log_lines.append("\nSources now in DB:")
            for s in sources:
                log_lines.append(f"  • {s}")
        else:
            log_lines.append("No chunks created, nothing added to DB.")

    # 3) Move processed PDFs to 'imported' so they don't get re-processed
    if processed_pdfs:
        log_lines.append(f"\nMoving {len(processed_pdfs)} processed PDFs to: {IMPORTED_DIR}")
        for pdf_path in processed_pdfs:
            dest = IMPORTED_DIR / pdf_path.name
            shutil.move(str(pdf_path), str(dest))  # standard move [web:170][web:175]
            log_lines.append(f"  Moved {pdf_path.name} -> {dest}")
    else:
        log_lines.append("\nNo PDFs needed moving (all were previously processed).")

    return "\n".join(log_lines)


# ---------- VECTORSTORE & RETRIEVAL HELPERS ----------

@st.cache_resource(show_spinner=False)
def get_vectorstore() -> Chroma:
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    db = Chroma(persist_directory=str(DB_DIR), embedding_function=embeddings)
    return db


@st.cache_resource(show_spinner=False)
def get_retriever(k: int = 4):
    db = get_vectorstore()
    return db.as_retriever(search_kwargs={"k": k})


@st.cache_resource(show_spinner=False)
def get_llm():
    # DeepSeek-R1 via Ollama [web:204][web:207]
    llm = ChatOllama(model=LLM_MODEL, temperature=0.1)
    return llm


def list_sources() -> List[str]:
    db = get_vectorstore()
    data = db.get()
    sources = sorted({m.get("source") for m in data["metadatas"] if m})
    return sources


def rag_answer(question: str, k: int = 4):
    """
    Simple RAG: retrieve top-k chunks, stuff into a prompt, call DeepSeek.
    Returns (answer_text, source_docs).
    """
    retriever = get_retriever(k=k)
    llm = get_llm()

    docs: List[Document] = retriever.invoke(question)

    context = "\n\n---\n\n".join(d.page_content for d in docs)

    prompt_tmpl = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are a New Zealand legal assistant. Answer using only the context "
                    "from the provided legal documents. If you are unsure or the answer "
                    "is not clearly stated, say you are unsure and suggest what statute or "
                    "document to check."
                ),
            ),
            (
                "user",
                (
                    "Context:\n{context}\n\n"
                    "Question:\n{question}\n\n"
                    "Give a concise, legally accurate answer, and if helpful, cite the Act, "
                    "section, or guideline name explicitly."
                ),
            ),
        ]
    )

    prompt = prompt_tmpl.invoke({"context": context, "question": question})
    raw_response = llm.invoke(prompt).content
    answer = strip_deepseek_thinking(raw_response)

    return answer, docs


# ---------- STREAMLIT APP ----------

st.set_page_config(page_title="NZ Legal RAG", layout="wide")

if "import_log" not in st.session_state:
    st.session_state.import_log = ""

st.title("NZ Legal RAG Assistant")

# Sidebar
with st.sidebar:
    st.header("Documents in database")
    try:
        sources = list_sources()
        if sources:
            for s in sources:
                st.write(f"- {s}")
        else:
            st.write("_No documents found in DB._")
    except Exception as e:
        st.error(f"Error loading sources: {e}")
        sources = []

    st.markdown("---")
    st.subheader("Maintenance")

    if st.button("Import new PDFs"):
        with st.spinner("Importing and indexing PDFs..."):
            log = import_new_pdfs()
            st.session_state.import_log = log
        # Clear cached vectorstore/llm so new docs are visible immediately
        get_vectorstore.clear()
        get_retriever.clear()
        get_llm.clear()
        st.success("Import complete. Vector store reloaded.")

    if st.button("Clear import log"):
        st.session_state.import_log = ""

    st.markdown("---")
    k = st.slider("Number of retrieved chunks", min_value=2, max_value=12, value=4, step=1)

# Main area
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Ask a question about the documents")

    question = st.text_area(
        "Your question",
        placeholder="e.g. Does this treatment breach NZBORA s9 or the Corrections Act?",
        height=100,
    )

    if st.button("Run analysis"):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Thinking..."):
                answer, docs = rag_answer(question, k=k)

            st.markdown("### Answer")
            st.write(answer)

            st.markdown("### Sources used")
            if not docs:
                st.write("_No source documents returned by retriever._")
            else:
                for i, d in enumerate(docs, start=1):
                    st.markdown(f"**Source {i}:** {d.metadata.get('source', 'unknown')}")
                    st.caption(d.page_content[:600] + ("..." if len(d.page_content) > 600 else ""))

with col2:
    st.subheader("Last import run")
    if st.session_state.import_log:
        st.text(st.session_state.import_log)
    else:
        st.caption("No import has been run yet in this session.")

