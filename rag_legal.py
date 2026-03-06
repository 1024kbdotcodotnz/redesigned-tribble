#!/usr/bin/env python3
import os
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader

DOCS_PATH = "./documents/"
DB_PATH = "./chroma_db"
MODEL = "deepseek-r1:14b"

def load_documents():
    if not os.path.exists(DOCS_PATH):
        os.makedirs(DOCS_PATH)
        print(f"Created {DOCS_PATH} - add .txt files there")
        return []
    loader = DirectoryLoader(DOCS_PATH, glob="**/*.txt", loader_cls=TextLoader)
    return loader.load()

def setup_vectorstore(docs):
    if not docs:
        return None
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(docs)
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    return Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=DB_PATH)

def analyze(query, vectorstore):
    llm = OllamaLLM(model=MODEL)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    
    # Use invoke instead of get_relevant_documents
    docs = retriever.invoke(query)
    
    context = "\n\n".join([f"[{doc.metadata.get('source')}]: {doc.page_content[:500]}" for doc in docs])
    
    prompt = f"""You are a NZ legal analyst. Answer using the context below. Identify breaches, non-compliance, or risks.

Context:
{context}

Question: {query}

Answer:"""
    
    print("\n" + "="*60 + "\nANALYSIS\n" + "="*60)
    print(llm.invoke(prompt))
    print("\n" + "="*60 + "\nSOURCES\n" + "="*60)
    for doc in docs:
        print(f"  - {doc.metadata.get('source', 'Unknown')}")

def main():
    docs = load_documents()
    if os.path.exists(DB_PATH) and os.listdir(DB_PATH):
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    else:
        vectorstore = setup_vectorstore(docs)
    if not vectorstore:
        print("No documents found. Add .txt files to ./documents/")
        return
    print("\nNZ LEGAL ANALYZER - Type 'quit' to exit\n")
    while True:
        query = input("Question: ").strip()
        if query.lower() in ('quit', 'q', 'exit'):
            break
        if query:
            analyze(query, vectorstore)

if __name__ == "__main__":
    main()
