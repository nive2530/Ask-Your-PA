# 🤖 Ask Your PA – AI-Powered Personal Assistant

**Ask Your PA** is an intelligent assistant platform that allows users to upload personalized information (text or documents) and interact with a chatbot that understands their context. The system combines **FastAPI** and **Streamlit** with **OpenAI's GPT** and **Pinecone vector database** to deliver highly relevant, user-specific responses.

---

## 🔧 Tech Stack

| Layer              | Technologies                                                                 |
|-------------------|------------------------------------------------------------------------------|
| **Backend**        | FastAPI, Uvicorn                                                             |
| **Frontend**       | Streamlit (custom CSS for UI)                                                |
| **Vector Store**   | Pinecone (cosine similarity search)                                          |
| **Embedding**      | OpenAI Embeddings API (`text-embedding-3-small`)                             |
| **Chat Model**     | OpenAI GPT (`gpt-3.5-turbo`)                                                  |
| **File Handling**  | PDF: PyPDF2, DOCX: python-docx, TXT: standard read                           |
| **Persistence**    | JSON-based user store                                                        |

---

## 💡 Features

- **📝 User Sign-Up & Login**
  - Secure sign-up with personal details and resume-like documents.
  - Authenticated access for data persistence and personal queries.

- **📁 Upload + Embed**
  - Accepts `.pdf`, `.docx`, and `.txt` files.
  - Extracts and chunks text with overlap, converts to vector embeddings via OpenAI.
  - Stores vector chunks in Pinecone with associated user metadata.

- **💬 Context-Aware Chat**
  - Ask questions about previously uploaded data.
  - Retrieves top relevant chunks via Pinecone similarity search.
  - Sends context + query to GPT for final response.

- **📈 Streamlit UI**
  - Simple tab-based login and signup flow.
  - Logged-in users can upload additional info or chat interactively.
  - Styled with custom themes and smart feedback messages.

---

## 🧠 Workflow

```text
User Input (Query) ──▶ Embed via OpenAI ──▶ Pinecone (Top-k Search)
                                         │
                                         ▼
                          Retrieve matched user-specific chunks
                                         │
                                         ▼
                          GPT Query with Context + Question
                                         │
                                         ▼
                                 Streamlit Chat UI (Answer)
```

---

## 🚀 How to Run the Project

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/ask-your-pa.git
cd ask-your-pa
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set environment variables

Create a file named `.env` and paste your API keys:
```
OPENAI_API_KEY=your-openai-api-key
PINECONE_API_KEY=your-pinecone-api-key
```

### 5. Run the application
```bash
python ask_your_pa.py
```

This will launch the FastAPI backend and Streamlit UI simultaneously.

---

## 📂 File Structure
```
Ask-Your-PA/
├── ask_your_pa.py                # Main app file (FastAPI + Streamlit)
├── users.json             # Local user persistence file
├── requirements.txt       # Dependency list
├── README.md              # Project documentation
```

---

## 📎 Use Cases
- Smart resume Q&A
- HR intake assistant
- Personalized document agent
- Executive assistant chatbot
