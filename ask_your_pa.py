# Integrated FastAPI + Streamlit App with JSON-based User Persistence

from dotenv import load_dotenv
load_dotenv()
import uuid
import os
import json
import requests
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
import uvicorn
import streamlit as st
from pinecone import Pinecone, ServerlessSpec
from PyPDF2 import PdfReader
import docx
import openai

# --------------------------- CONFIGURATION ---------------------------
# Configuration constants including chunking parameters for text processing,
# OpenAI API settings, and user data file location.
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
embedding_model = "text-embedding-3-small"
llm_model = "gpt-3.5-turbo"
USER_FILE = "users.json"

# --------------------------- FASTAPI SETUP ---------------------------
# Initializes FastAPI app with CORS middleware and configures Pinecone vector DB index.
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = "user-profile-index"
embedding_dim = 1536

if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=embedding_dim,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

index = pc.Index(index_name)

users_db = {}

# --------------------------- PERSISTENCE HELPERS ---------------------------
# Helper functions to save and load user data to/from JSON file for persistence across sessions.
def save_users_to_file():
    with open(USER_FILE, "w") as f:
        json.dump(users_db, f)

def load_users_from_file():
    global users_db
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            users_db = json.load(f)

# --------------------------- API ROUTES ---------------------------
# FastAPI endpoints to handle user signup, login, appending info, and chat-based query resolution.
@app.post("/signup")
async def signup_user(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    about: str = Form(...),
    document: UploadFile = File(...)
):
    text = about + "\n" + extract_text(document)
    chunks = chunk_text(text)
    embeddings = get_openai_embeddings(chunks)
    user_id = str(uuid.uuid4())

    users_db[user_id] = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "password": password
    }
    save_users_to_file()

    vectors = [
        {
            "id": f"{user_id}-{i}",
            "values": emb,
            "metadata": {
                "user_id": user_id,
                "email": email,
                "text": chunks[i]
            }
        } for i, emb in enumerate(embeddings)
    ]
    index.upsert(vectors=vectors)
    return {"message": "User registered successfully", "user_id": user_id}

@app.post("/login")
async def login_user(email: str = Form(...), password: str = Form(...)):
    for uid, user in users_db.items():
        if user["email"].strip().lower() == email.strip().lower() and user["password"] == password:
            return {"message": "Login successful", "user_id": uid}
    return {"message": "Invalid credentials"}

@app.post("/append")
async def append_user_data(
    email: str = Form(...),
    about: str = Form(...),
    document: UploadFile = File(...)
):
    user_id = next((uid for uid, u in users_db.items() if u["email"] == email), None)
    if user_id is None:
        return {"message": "User not found"}, 404

    text = about + "\n" + extract_text(document)
    chunks = chunk_text(text)
    embeddings = get_openai_embeddings(chunks)
    vectors = [
        {
            "id": f"{user_id}-extra-{i}-{uuid.uuid4().hex[:6]}",
            "values": emb,
            "metadata": {
                "user_id": user_id,
                "email": email,
                "text": chunks[i]
            }
        } for i, emb in enumerate(embeddings)
    ]
    index.upsert(vectors=vectors)
    return {"message": "Data appended successfully"}

@app.post("/chat")
async def chat_user_query(email: str = Form(...), query: str = Form(...)):
    user_id = next((uid for uid, u in users_db.items() if u["email"] == email), None)
    if user_id is None:
        return {"response": "User not found"}, 404

    query_embedding = get_openai_embeddings([query])[0]
    results = index.query(vector=query_embedding, top_k=5, include_metadata=True)
    relevant_chunks = [m["metadata"]["text"] for m in results["matches"] if m["metadata"].get("user_id") == user_id]

    context = "\n".join(relevant_chunks)
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=llm_model,
        messages=[
            {"role": "system", "content": "You are an assistant answering user-specific questions based on their uploaded data."},
            {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
        ]
    )
    return {"response": response.choices[0].message.content.strip()}

# --------------------------- HELPERS ---------------------------
# Utility functions for text extraction, chunking, and embedding generation.
def extract_text(file: UploadFile) -> str:
    if file.filename.endswith(".txt"):
        return file.file.read().decode("utf-8", errors="ignore")
    elif file.filename.endswith(".pdf"):
        reader = PdfReader(file.file)
        return " ".join(page.extract_text() or "" for page in reader.pages)
    elif file.filename.endswith(".docx"):
        doc = docx.Document(file.file)
        return " ".join(p.text for p in doc.paragraphs)
    return ""

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def get_openai_embeddings(chunks):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.embeddings.create(input=chunks, model=embedding_model)
    return [r.embedding for r in response.data]

# --------------------------- STREAMLIT UI ---------------------------
# Streamlit-based frontend UI for user interaction - login, registration, adding info, and querying AI assistant.
st.set_page_config(page_title="AI Assistant", layout="wide")

def launch_streamlit():
    st.markdown("""
        <style>
        body { background-color: #1e1e1e; color: white; }
        .stButton > button {
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
            border-radius: 10px;
        }
        .stButton > button:hover {
            background-color: #45a049;
            transform: scale(1.05);
        }
        .sidebar .sidebar-content {
            background-color: #111;
            padding: 1rem;
        }
        .stRadio > div > label {
            color: #ddd !important;
        }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("👤 User Navigation")
        if "email" in st.session_state:
            st.write(f"**Logged in as:** {st.session_state.email}")
            if st.button("🏠 Home"):
                del st.session_state["user_id"]
                del st.session_state["email"]
                st.rerun()
            if st.button("🔒 Logout"):
                st.session_state.clear()
                st.rerun()
        else:
            st.write("🟢 Please sign up or log in.")

    st.title("🤖 AI Personal Assistant")

    if "user_id" not in st.session_state:
        tabs = st.tabs(["Sign Up", "Login"])

        with tabs[0]:
            st.subheader("Create a New Account")
            with st.form("signup_form"):
                first_name = st.text_input("First Name")
                last_name = st.text_input("Last Name")
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                about = st.text_area("Tell us about yourself")
                document = st.file_uploader("Upload Document", type=["pdf", "txt", "docx"])
                if st.form_submit_button("Register"):
                    if all([first_name, last_name, email, password, about, document]):
                        files = {"document": (document.name, document.read(), document.type)}
                        data = {
                            "first_name": first_name,
                            "last_name": last_name,
                            "email": email,
                            "password": password,
                            "about": about
                        }
                        res = requests.post("http://localhost:8000/signup", data=data, files=files)
                        try:
                            res_json = res.json()
                            st.write("API Response:", res_json)
                            if res.status_code == 200 and "user_id" in res_json:
                                st.success(res_json["message"])
                                st.session_state.user_id = res_json["user_id"]
                                st.session_state.email = email
                        except Exception as e:
                            st.error(f"Signup failed: {e}")
                    else:
                        st.warning("Please fill all fields")

        with tabs[1]:
            st.subheader("Login to Your Account")
            email = st.text_input("Login Email")
            password = st.text_input("Login Password", type="password")
            if st.button("Login"):
                res = requests.post("http://localhost:8000/login", data={"email": email, "password": password})
                try:
                    res_json = res.json()
                    st.write("API Response:", res_json)
                    if res.status_code == 200:
                        if "user_id" in res_json:
                            st.session_state.user_id = res_json["user_id"]
                            st.session_state.email = email
                            st.rerun()  # ⬅️ instantly show post-login UI
                        else:
                            st.warning(res_json.get("message", "Login failed"))
                    else:
                        st.error("Login request failed.")
                except Exception as e:
                    st.error(f"Login failed: {e}")

    

    else:
        st.success(f"Welcome {st.session_state.email}!")
        option = st.radio("Choose an action", ["Add Info", "Retrieve Info"], horizontal=True)

        if option == "Add Info":
            with st.form("append_form"):
                about = st.text_area("Additional Info")
                doc = st.file_uploader("Upload Document", type=["pdf", "txt", "docx"])
                if st.form_submit_button("Submit"):
                    if about and doc:
                        files = {"document": (doc.name, doc.read(), doc.type)}
                        data = {"email": st.session_state.email, "about": about}
                        res = requests.post("http://localhost:8000/append", data=data, files=files)
                        if res.status_code == 200:
                            st.success("Information appended successfully!")
                        else:
                            st.error("Failed to append info.")
                    else:
                        st.warning("Please provide all inputs.")

        elif option == "Retrieve Info":
            query = st.text_input("Ask a question about your profile")
            if st.button("Ask") and query:
                data = {"email": st.session_state.email, "query": query}
                res = requests.post("http://localhost:8000/chat", data=data)
                try:
                    res_json = res.json()
                    st.write("API Response:", res_json)
                    if res.status_code == 200 and "response" in res_json:
                        st.write("**Response:**", res_json["response"])
                    else:
                        st.error("Unexpected chat response.")
                except Exception as e:
                    st.error(f"Failed to process chat response: {e}")

# --------------------------- MAIN ---------------------------
# Entry point to start the FastAPI server in a background thread and launch the Streamlit frontend.
def start_fastapi():
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    load_users_from_file()
    thread = Thread(target=start_fastapi, daemon=True)
    thread.start()
    launch_streamlit()
