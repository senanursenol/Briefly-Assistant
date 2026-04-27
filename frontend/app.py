import streamlit as st
import requests
import time
from PIL import Image

# --- CONFIGURATION & CONSTANTS ---
import os
BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
ALLOWED_DOC_TYPES = ["pdf", "doc", "docx", "txt"]
ALLOWED_IMAGE_TYPES = ["jpg", "jpeg", "png"]

st.set_page_config(
    page_title="DocSage - Smart Document Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS STYLING (Fixed Sidebar Button Color & Position) ---
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
        color: #2c3e50 !important;
    }
    
    .stChatMessage p, .stChatMessage span, .stChatMessage div {
        color: #2c3e50 !important;
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
if "doc_ids" not in st.session_state:
    st.session_state.doc_ids = [] # List of {"id": doc_id, "name": filename}
if "messages" not in st.session_state:
    st.session_state.messages = [] 
if "history" not in st.session_state:
    st.session_state.history = []

def reset_chat():
    st.session_state.messages = [] 

# --- SIDEBAR (History & Actions) ---
with st.sidebar:
    # 1. Başlık
    st.markdown('<div class="history-header">🗂️ History</div>', unsafe_allow_html=True)
    
    # 2. Geçmiş Sorular
    if len(st.session_state.history) > 0:
        st.markdown("<h3 style='color: #bdc3c7; font-size: 1rem; margin-top: 10px;'>Recent Questions</h3>", unsafe_allow_html=True)
        for i, item in enumerate(reversed(st.session_state.history[-5:])): 
            st.caption(f"❓ **{item['question']}**")
            st.markdown("<hr style='margin: 5px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    else:
        st.info("No questions asked yet.")

    # 3. BUTONU EN ALTA İTMEK İÇİN BÜYÜK BOŞLUK
    # Ekran boyutuna göre otomatik boşluk oluşturur
    if st.session_state.doc_ids:
        st.markdown("<h3 style='color: #bdc3c7; font-size: 1.1rem; margin-top: 20px;'>📂 Yüklü Dokümanlar</h3>", unsafe_allow_html=True)
        for doc in st.session_state.doc_ids:
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                st.caption(f"📄 {doc['name']}")
            with col2:
                if st.button("📝", key=f"sum_{doc['id']}", help="Özet Çıkar"):
                    st.session_state.summarize_doc_id = doc['id']
                    st.session_state.summarize_doc_name = doc['name']
    
    st.markdown("""
        <style>
            div[data-testid="stSidebar"] > div:first-child {
                height: 100vh;
                display: flex;
                flex-direction: column;
            }
            div[data-testid="stSidebar"] > div:first-child > div:nth-child(2) {
                flex-grow: 1; /* Bu kısım aradaki boşluğu doldurur */
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Bu boş div yukarıdaki flex-grow sayesinde tüm boşluğu kaplayacak
    st.markdown("<div></div>", unsafe_allow_html=True)
    
    # 4. Clear Butonu (En Alta Sabitlenmiş Olacak)
    if st.button("🗑️ Sohbeti ve Dosyaları Temizle", use_container_width=True):
        st.session_state.messages = []
        st.session_state.history = []
        st.session_state.doc_ids = []
        st.rerun()

# --- MAIN PAGE ---

# ORTALANMIŞ BAŞLIK
st.markdown("<h1 style='text-align: center;'>🧠 DocSage Asistanı</h1>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# Özetleme Modalı / Alanı
if "summarize_doc_id" in st.session_state and st.session_state.summarize_doc_id:
    with st.status(f"📄 {st.session_state.summarize_doc_name} özetleniyor...", expanded=True):
        try:
            resp = requests.post(f"{BASE_URL}/qa/summarize", json={"doc_id": st.session_state.summarize_doc_id})
            if resp.status_code == 200:
                summary = resp.json()["summary"]
                st.markdown("### ✨ Döküman Özeti")
                st.markdown(summary)
            else:
                st.error(f"Özet hatası: {resp.text}")
        except Exception as e:
            st.error(f"Bağlantı hatası: {e}")
    if st.button("Kapat"):
        st.session_state.summarize_doc_id = None
        st.rerun()
    st.markdown("---")

# WARNING
st.info(
    "👋 **Hoş Geldiniz!** Bu sistem artık **Türkçe ve İngilizce** içerikler için optimize edilmiştir.\n\n"
    "Lütfen dökümanlarınızı (PDF, DOC, DOCX, TXT) yükleyin ve sorularınızı istediğiniz dilde sorun."
)

# FILE UPLOAD SECTION
with st.container():
    uploaded_files = st.file_uploader(
        "📄 Döküman (PDF, DOC, DOCX, TXT) veya Görsel Yükleyin",
        type=ALLOWED_DOC_TYPES + ALLOWED_IMAGE_TYPES,
        key="file_upload",
        accept_multiple_files=True
    )

    # Process Button
    if st.button("🚀 Dosyaları İşle", use_container_width=True):
        if uploaded_files:
            with st.spinner("⚙️ Dökümanlar analiz ediliyor... Lütfen bekleyin."):
                new_docs_count = 0
                for uploaded_file in uploaded_files:
                    # Zaten yüklenmiş mi kontrol et (isim bazlı basit kontrol)
                    if any(doc["name"] == uploaded_file.name for doc in st.session_state.doc_ids):
                        continue
                        
                    try:
                        uploaded_file.seek(0)
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        response = requests.post(f"{BASE_URL}/documents/upload", files=files)
                        
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.doc_ids.append({"id": data["doc_id"], "name": uploaded_file.name})
                            new_docs_count += 1
                        else:
                            st.error(f"❌ {uploaded_file.name} yüklenemedi: {response.text}")
                    except Exception as e:
                        st.error(f"❌ {uploaded_file.name} bağlantı hatası: {e}")
                
                if new_docs_count > 0:
                    st.success(f"✅ {new_docs_count} yeni döküman başarıyla hazırlandı!")
                    time.sleep(1) 
                    st.rerun()
                elif not st.session_state.doc_ids:
                    st.warning("⚠️ Hiçbir dosya işlenemedi.")
        else:
            st.warning("⚠️ Lütfen önce en az bir dosya seçin.")

# Image Preview (Sadece son yüklenen resimlerden biri için gösterim yapalım veya basitleştirelim)
if uploaded_files:
    for f in uploaded_files:
        if f.type.startswith("image"):
            with st.expander(f"🖼️ Görsel: {f.name}"):
                st.image(f, use_column_width=True)

st.markdown("---")

# CHAT INTERFACE
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("📚 Referans Kaynaklar (Kanıtlar)"):
                for source in message["sources"]:
                    text = source.get("text", "")
                    source_file = source.get("source", "Bilinmeyen Dosya")
                    clean_text = text.replace("\n", " ").strip()
                    st.caption(f"📄 **Kaynak: {source_file}**\n\n...{clean_text[:150]}...")

# USER INPUT
placeholder_text = "Sorunuzu buraya yazın (Örn: 'Dökümanların ana konusu nedir?')..."
if prompt := st.chat_input(placeholder_text):
    
    if not st.session_state.doc_ids:
        st.warning("⚠️ Sohbet başlatmak için lütfen önce en az bir döküman yükleyin.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        sources = []
        
        with st.spinner("Bilgi tabanı taranıyor..."):
            try:
                # Tüm döküman ID'lerini gönder
                doc_ids_to_query = [doc["id"] for doc in st.session_state.doc_ids]
                payload = {"doc_ids": doc_ids_to_query, "question": prompt}
                response = requests.post(f"{BASE_URL}/qa/", json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    answer_text = result.get("answer", "Cevap üretilemedi.")
                    sources = result.get("context_chunks", []) # List of {"text": ..., "source": ...}
                else:
                    answer_text = f"Hata: {response.text}"
            except Exception as e:
                answer_text = f"Bağlantı hatası: {e}"

        error_keywords = ["üzgünüm", "bulamadım", "bilgi bulunamadı", "i am sorry", "could not find"]
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
                with st.expander("🔍 Referans Kaynaklar (Kanıtlar)"):
                    for src in sources:
                        text = src.get("text", "")
                        source_file = src.get("source", "Bilinmeyen Dosya")
                        clean_text = text.replace("\n", " ").strip()
                        st.info(f"📄 **Kaynak: {source_file}**\n\n...{clean_text[:250]}...") 

        st.session_state.messages.append({
            "role": "assistant", 
            "content": full_response,
            "sources": sources if not is_negative_answer else []
        })
        
        st.session_state.history.append({"question": prompt, "answer": full_response})