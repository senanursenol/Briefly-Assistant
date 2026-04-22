import os
import re
import numpy as np
from routers.documents import DOCUMENT_STORE
from typing import List
from groq import Groq
from dotenv import load_dotenv
from services.documents import DocumentObject

# Çevresel değişkenleri yükle (.env dosyasından)
load_dotenv()

# --- AYARLAR ---
MODEL_NAME = "llama-3.1-8b-instant" 
NO_ANSWER_MSG = "I am sorry, I could not find the answer to this question in the provided documents."

# Groq istemcisini başlat
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# --- HİBRİT ARAMA VE RETRIEVAL FONKSİYONLARI ---

def calculate_hybrid_match(question: str, text: str) -> float:
    stops = {
        "what", "how", "why", "when", "does", "do", "did", "can", "could", 
        "use", "using", "used", "code", "file", "make", "create",
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
        "with", "by", "of", "is", "are", "was", "were", "be", "been", "should"
    }
    
    words = [w for w in re.findall(r"\b\w{3,}\b", question.lower()) if w not in stops]
    
    if not words: return 0.5 
    
    weights = {}
    question_words_original = re.findall(r"\b\w{3,}\b", question)
    word_case_map = {w.lower(): w for w in question_words_original}

    for w_lower in words:
        original = word_case_map.get(w_lower, w_lower)
        if original[0].isupper():
            weights[w_lower] = 3.0
        elif len(w_lower) > 6:
            weights[w_lower] = 1.5
        else:
            weights[w_lower] = 1.0
    
    total_weight = sum(weights.values())
    text_lower = text.lower()
    score, penalty = 0.0, 0.0

    for word, weight in weights.items():
        if re.search(rf"\b{re.escape(word)}\b", text_lower):
            score += weight
        elif weight >= 3.0: 
            penalty += 1.0

    return max(0.0, (score - penalty) / total_weight)

def retrieve_globally_relevant_chunks(
    question: str,
    documents: List[DocumentObject],
    k_per_doc: int = 5,
    max_chunks: int = 8,
    threshold: float = 0.15,  # 0.10'dan 0.15'e çıkardık
    vec_weight: float = 0.60  # %60 Anlam, %40 Kelime Eşleşmesi
) -> List[str]:
    candidates = list({r["text"] for doc in documents for r in doc.embedding_store.search(question, k=k_per_doc)})
    if not candidates: return []

    emb_model = documents[0].embedding_store.model
    q_vec = emb_model.encode([question], convert_to_numpy=True)
    c_vecs = emb_model.encode(candidates, convert_to_numpy=True)
    
    v_scores = (c_vecs @ q_vec.T).squeeze() / (np.linalg.norm(c_vecs, axis=1) * np.linalg.norm(q_vec))
    if v_scores.ndim == 0: v_scores = [v_scores]

    final_results = []
    
    for text, v_score in zip(candidates, v_scores):
        k_score = calculate_hybrid_match(question, text)
        h_score = (v_score * vec_weight) + (k_score * (1 - vec_weight))
        
        if h_score >= threshold:
            final_results.append((h_score, text))

    return [res[1] for res in sorted(final_results, key=lambda x: x[0], reverse=True)[:max_chunks]]

# --- GENERATION (GROQ İLE CEVAP ÜRETME) ---

def generate_answer_from_contexts(
    question: str,
    contexts: List[str]
) -> str:
    """
    Bulunan bağlamları kullanarak Groq API üzerinden Briefly asistanına cevap ürettirir.
    """
    if not contexts:
        return NO_ANSWER_MSG

    context_text = "\n\n".join(contexts)

    try:
        # Groq API Çağrısı
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Briefly, a helpful AI assistant. Your task is to answer user questions "
                        "strictly based on the provided context. Be concise and accurate.\n"
                        f"If the context does not contain the answer, reply exactly with: '{NO_ANSWER_MSG}'"
                    )
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context_text}\n\nQuestion:\n{question}"
                }
            ],
            model=MODEL_NAME,
            temperature=0.0,
            max_tokens=1024,
        )
        
        answer = chat_completion.choices[0].message.content.strip()
        
        # Temizlik ve Kontrol
        if len(answer) < 5 or "NO_ANSWER_MSG" in answer:
            return NO_ANSWER_MSG
            
        return answer

    except Exception as e:
        return f"Briefly Connection Error (Groq): {str(e)}"
    
def summarize_documents(doc_ids: List[str]) -> str:
    """
    Verilen doküman ID'lerine ait tüm metinleri birleştirir ve Groq ile özetler.
    """
    all_text = ""
    for doc_id in doc_ids:
        if doc_id in DOCUMENT_STORE:
            # Dokümanın tüm parçalarını (chunks) birleştir
            all_text += " ".join(DOCUMENT_STORE[doc_id].chunks) + "\n"
            
    if not all_text.strip():
        return "Özetlenecek herhangi bir metin bulunamadı."

    # Groq'un token sınırını aşmamak için metni belirli bir karakterle sınırlandırıyoruz
    max_chars = 15000 
    text_to_summarize = all_text[:max_chars]

    try:
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert executive assistant. Summarize the provided text clearly and comprehensively. Use bullet points for key takeaways. Respond in the same language as the provided text."
                },
                {
                    "role": "user", 
                    "content": f"Please summarize the following document(s):\n\n{text_to_summarize}"
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.3, # Özetleme için yaratıcılığı çok hafif açıyoruz
        )
        return response.choices[0].message.content
    except Exception as e:
        raise ValueError(f"Özetleme sırasında Groq API hatası: {str(e)}")