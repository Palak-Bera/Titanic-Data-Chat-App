import sys
import streamlit as st
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from openai import OpenAI
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage
import os

# Load environment variables
load_dotenv()

# Function to initialize Pinecone and check for existing index
def initialize_pinecone():
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    index_name = "titanic"

    if index_name not in pc.list_indexes().names():
        print("Creating Pinecone index...")
        pc.create_index(
            name=index_name,
            dimension=768,
            metric='euclidean',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
    else:
        print("Pinecone index already exists.")

    return pc, index_name

# Function to read the document
def reading_document(file):
    print("💙 Reading the document...")
    loader = PyPDFLoader(file)
    documents = loader.load()
    return documents

# Function to chunk the document
def chunk_data(docs, chunk_size=1000, chunk_overlap=50):
    print("💚 Chunking the document...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = text_splitter.split_documents(docs)
    return chunks

# Function to generate embeddings and upload to Pinecone
def generate_and_upload_embeddings(chunks, index):
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
    for i, chunk in enumerate(chunks):
        print(f"❤️ Processing chunk {i}...")
        chunk_text = chunk.page_content
        embedding = embeddings.embed_query(chunk_text)
        metadata = {"chunk_id": i, "text": chunk_text}
        index.upsert(vectors=[(f"chunk-{i}", embedding, metadata)])
    print("📌 All sections successfully uploaded to Pinecone!")

# Function to retrieve related sections
def retrieve_related_sections(user_query, embeddings, index):
    query_vector = embeddings.embed_query(user_query)
    response = index.query(vector=query_vector, top_k=5, include_metadata=True)
    results = []
    for match in response['matches']:
        metadata = match['metadata']
        results.append({
            "Text": metadata.get("text", ""),
            "Page": metadata.get("chunk_id", -1),
        })
    return results

# Function to generate a response
def generate_response(user_query, relevant_sections):
    context = "\n\n".join([f"Page {int(res['Page'])}:\n{res['Text']}" for res in relevant_sections])
    prompt = f"""
        You are a knowledgeable assistant specializing in Titanic Data Analysis.
        Use the following context information to address the user's query.

        Context:
        {context}

        User Query:
        {user_query}

        Generate a clear, precise, and actionable response.
    """
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o-mini"
    )
    return response.choices[0].message.content

# Function to process the user's query
def get_result(user_query, embeddings, index):
    relevant_sections = retrieve_related_sections(user_query, embeddings, index)
    if not relevant_sections:
        return "No relevant sections found."
    return generate_response(user_query, relevant_sections)

# Streamlit App
if "page" not in st.session_state:
    st.session_state.page = "first_page"
    st.session_state.index_initialized = False

if "pinecone_index" not in st.session_state:
    st.session_state.pinecone_index = None

if "embeddings" not in st.session_state:
    st.session_state.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

if st.session_state.page == "first_page":
    st.title("Welcome to Titanic Data Analysis! 🎉")

    st.markdown("""
    🌟 **Hello! Welcome to the Titanic Data Analysis Portal** 🌟

    🚢 Dive into Titanic data and ask your questions to uncover insightful patterns!

    📫 **Get in Touch**:
    - **GitHub**: [@Palak-Bera](https://github.com/Palak-Bera)
    - **LinkedIn**: [@Palak-Bera](https://www.linkedin.com/in/palak-bera)
    - **Email**: [berapalak2001@gmail.com](mailto:berapalak2001@gmail.com)

    🧭 Let's begin our journey with Titanic Data! Click the button below to start exploring. 🚀
    """)

    if st.button("Continue to Titanic Chatbot 💬"):
        with st.spinner("Hang tight! 🚀 We're gearing up your knowledge base...\n🔍 Building smart connections for your insights.\nThis might take a moment—grab a coffee or simply sit back and watch the magic happen! ☕✨"):
            pc, index_name = initialize_pinecone()
            st.session_state.pinecone_index = pc.Index(index_name)

            # Only initialize embeddings and index if not done before
            if not st.session_state.index_initialized:
                doc = reading_document(r"Knowledge_base/titanic_final_eda.pdf")
                chunks = chunk_data(doc)
                generate_and_upload_embeddings(chunks, st.session_state.pinecone_index)
                st.session_state.index_initialized = True

        st.session_state.page = "chatbot"

if st.session_state.page == "chatbot":
    st.title("Titanic Data Analysis - Query Assistant 🎤")
    st.markdown("""
    🌟 **Ask your query about Titanic Data** 🌟
    
    🧑‍💻 Type your question about the Titanic dataset below, and I'll help you analyze the data!
    
    ➡️ Type something like "What is the survival rate?" or "How many people were in first class?"
    """)

    user_query = st.text_input("Ask your query about Titanic Data:")

    if user_query:
        final_answer = get_result(user_query, st.session_state.embeddings, st.session_state.pinecone_index)
        st.write(f"Response: {final_answer}")

