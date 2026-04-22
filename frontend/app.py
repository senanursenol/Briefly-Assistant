import streamlit as st
import requests
import time
from PIL import Image

# --- CONFIGURATION & CONSTANTS ---
BASE_URL = "http://localhost:8000"
# TXT desteği eklendi
ALLOWED_DOC_TYPES = ["pdf", "docx", "txt"]
ALLOWED_IMAGE_TYPES = ["jpg", "jpeg", "png"]

st.set_page_config(
    page_title="Briefly - Smart Document Assistant", # İsim güncellendi
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS STYLING (SENİN TASARIMIN - HİÇ DOKUNULMADI) ---
st.markdown("""
<style>
    /* GENERAL BACKGROUND */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* HEADERS */
    h1, h2, h3 {
        color: #2c3e50;
        font-family: 'Helvetica Neue', sans-serif;
    }

    /* SIDEBAR - KOYU LACİVERT */
    [data-testid="stSidebar"] {
        background-color: #2c3e50;
        border-right: 1px solid #1a252f;
    }
    
    /* SIDEBAR METİNLERİ - GENEL BEYAZ */
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] div, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .caption {
        color: #ffffff !important;
    }

    /* SIDEBAR 'CLEAR' BUTONU - ÖZEL AYARLAR */
    /* 1. Buton Kutusu (Beyaz Arka Plan) */
    [data-testid="stSidebar"] .stButton button {
        background-color: #ffffff !important;
        border: 1px solid #ffffff;
        width: 100%;
    }
    
    /* 2. Buton İÇİNDEKİ Yazı Rengi (KESİN LACİVERT) */
    /* p etiketi ve butonun kendisi için renk zorlaması */
    [data-testid="stSidebar"] .stButton button, 
    [data-testid="stSidebar"] .stButton button p {
        color: #2c3e50 !important; 
        font-weight: 800 !important; /* Daha kalın yazı */
    }
    
    /* Hover Efekti */
    [data-testid="stSidebar"] .stButton button:hover {
        background-color: #ecf0f1 !important;
        border-color: #bdc3c7;
        transform: translateY(-2px);
    }

    /* HISTORY BAŞLIĞI */
    .history-header {
        font-size: 1.8rem !important;
        font-weight: bold !important;
        color: #ffffff !important;
        margin-bottom: 20px !important;
        text-align: center;
        border-bottom: 1px solid rgba(255,255,255,0.2);
        padding-bottom: 10px;
    }

    /* MAIN PAGE BUTTONS (Process File) */
    .main .stButton button {
        background-color: #2c3e50;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        transition: 0.3s;
        height: auto;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .main .stButton button:hover {
        background-color: #34495e;
        color: white;
    }
    
    /* CHAT STYLES */
    .stChatMessage {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #e1e4e8;
    }
    
    [data-testid="stFileUploader"] {
        background-color: #ffffff;
        padding: 10px;
        border-radius: 10px;
        border: 2px dashed #bdc3c7;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE MANAGEMENT ---
# YENİ: Artık tek bir doc_id değil, liste (doc_ids) tutuyoruz
if "doc_ids" not in st.session_state:
    st.session_state.doc_ids = []
if "messages" not in st.session_state:
    st.session_state.messages = [] 
if "history" not in st.session_state:
    st.session_state.history = []

def reset_doc_ids():
    st.session_state.doc_ids = []
    st.session_state.messages = [] 

# --- SIDEBAR (History & Actions) ---
with st.sidebar:
    st.markdown('<div class="history-header">🗂️ History</div>', unsafe_allow_html=True)
    
    if len(st.session_state.history) > 0:
        st.markdown("<h3 style='color: #bdc3c7; font-size: 1rem; margin-top: 10px;'>Recent Questions</h3>", unsafe_allow_html=True)
        for i, item in enumerate(reversed(st.session_state.history[-5:])): 
            st.caption(f"❓ **{item['question']}**")
            st.markdown("<hr style='margin: 5px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    else:
        st.info("No questions asked yet.")

    st.markdown("""
        <style>
            div[data-testid="stSidebar"] > div:first-child {
                height: 100vh;
                display: flex;
                flex-direction: column;
            }
            div[data-testid="stSidebar"] > div:first-child > div:nth-child(2) {
                flex-grow: 1; 
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div></div>", unsafe_allow_html=True)
    
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.history = []
        st.rerun()

# --- MAIN PAGE ---

# İsim Güncellendi
st.markdown("<h1 style='text-align: center;'>🧠 Briefly Assistant</h1>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

st.info(
    "👋 **Welcome!** This system is optimized for **English content**.\n\n"
    "Please upload **English** documents (PDF, DOCX, TXT) and ask your questions in **English** for the best accuracy."
)

# FILE UPLOAD SECTION
with st.container():
    # YENİ: accept_multiple_files=True eklendi
    uploaded_files = st.file_uploader(
        "📄 Upload English Documents (PDF, DOCX, TXT) or Images",
        type=ALLOWED_DOC_TYPES + ALLOWED_IMAGE_TYPES,
        accept_multiple_files=True,
        key="file_upload",
        on_change=reset_doc_ids
    )

    if st.button("🚀 Process Files", use_container_width=True):
        if uploaded_files:
            with st.spinner("⚙️ Analyzing documents... Please wait."):
                try:
                    # YENİ: Birden fazla dosyayı payload olarak hazırlıyoruz
                    files_payload = []
                    for uf in uploaded_files:
                        uf.seek(0)
                        files_payload.append(("files", (uf.name, uf.getvalue(), uf.type)))

                    response = requests.post(f"{BASE_URL}/documents/upload", files=files_payload)
                    
                    if response.status_code == 200:
                        data = response.json()
                        # YENİ: Gelen ID'leri doc_ids listesine atıyoruz
                        st.session_state.doc_ids = [doc["doc_id"] for doc in data["documents"]]
                        st.success(f"✅ {len(st.session_state.doc_ids)} Document(s) Ready!")
                        time.sleep(1) 
                        st.rerun()
                    else:
                        st.error(f"❌ Upload failed: {response.text}")
                except Exception as e:
                    st.error(f"❌ Connection error: {e}")
        else:
            st.warning("⚠️ Please select at least one file first.")

# --- PROCESS FILES BLOĞUNUN HEMEN ALTI (DIŞINDA) ---
        
        # 1. Kontrol: Eğer hafızada dökümanlar varsa butonu göster
        if "doc_ids" in st.session_state and st.session_state.doc_ids:
            # Çizgi yerine sadece temiz bir boşluk
            st.write("") 
            
            # Boyutlu, temiz ve net buton
            if st.button("✨ Summarize All Documents", use_container_width=True):
                with st.spinner("Briefly is generating a summary..."):
                    try:
                        # Backend isteği
                        sum_response = requests.post(
                            "http://localhost:8000/qa/summarize",
                            json={"doc_ids": st.session_state.doc_ids}
                        )
                        
                        if sum_response.status_code == 200:
                            summary_data = sum_response.json()["summary"]
                            # Özeti chat ekranına ekle
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": f"✨ **Summary:**\n\n{summary_data}"
                            })
                            st.rerun() 
                        else:
                            st.error(f"Error: {sum_response.text}")
                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")
        
# CHAT INTERFACE
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("📚 Reference Sources (Evidence)"):
                for source in message["sources"]:
                    st.caption(f"• {source}")

# USER INPUT
placeholder_text = "Ask your question here (e.g., 'What is the main topic?')..."
if prompt := st.chat_input(placeholder_text):
    
    if not st.session_state.doc_ids:
        st.warning("⚠️ Please upload a document first to start chatting.")
        st.stop()

    if any(char in prompt.lower() for char in "ğşüöçı"):
        st.toast("💡 Tip: Using English will provide better results.", icon="🇺🇸")

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        sources = []
        
        with st.spinner("Searching knowledge base..."):
            try:
                # YENİ: Artık [st.session_state.doc_id] yerine doğrudan listeyi gönderiyoruz
                payload = {"doc_ids": st.session_state.doc_ids, "question": prompt}
                response = requests.post(f"{BASE_URL}/qa/", json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    answer_text = result.get("answer", "No answer generated.")
                    sources = result.get("context_chunks", [])
                else:
                    answer_text = f"Error: {response.text}"
            except Exception as e:
                answer_text = f"Connection error: {e}"

        error_keywords = ["i am sorry", "could not find", "no information found"]
        is_negative_answer = any(keyword in answer_text.lower() for keyword in error_keywords)

        if is_negative_answer:
            st.warning(f"⚠️ {answer_text}")
            full_response = answer_text 
        else:
            for chunk in answer_text.split(" "): 
                full_response += chunk + " "
                time.sleep(0.05)
                message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)

            if sources:
                with st.expander("🔍 Reference Sources (Evidence)"):
                    for src in sources:
                        clean_src = src.replace("\n", " ").strip()
                        st.info(f"📄 ...{clean_src[:250]}...") 

        st.session_state.messages.append({
            "role": "assistant", 
            "content": full_response,
            "sources": sources if not is_negative_answer else []
        })
        
        st.session_state.history.append({"question": prompt, "answer": full_response})