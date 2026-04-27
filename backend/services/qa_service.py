import os
import numpy as np
from typing import List
import re
import threading
from services.documents import DocumentObject

# --- AYARLAR ---
# Yerel model ayarları (Fallback için tutuyoruz)
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
NO_ANSWER_MSG = "Üzgünüm, bu sorunun cevabını dökümanlarda bulamadım."

# --- GROQ ENTEGRASYONU ---
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "False").lower() == "true"

_groq_client = None
if GROQ_API_KEY and not USE_LOCAL_LLM:
    _groq_client = Groq(api_key=GROQ_API_KEY)

# --- TÜRKÇE STOP WORDS ---
TURKISH_STOPS = {
    "ne", "nasıl", "neden", "niçin", "ne zaman", "mı", "mi", "mu", "mü",
    "ve", "veya", "ama", "fakat", "lakin", "ancak", "ile", "için", "gibi",
    "bir", "bu", "şu", "o", "da", "de", "ki", "ise", "miyim", "misin",
    "mısınız", "misiniz", "mıdır", "midir", "olan", "olarak", "tarafından",
    "hakkında", "ilgili", "dair", "ait", "kendi", "hepsi", "her", "hiç",
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "with", "by", "of", "is", "are", "was", "were", "be", "been", "should"
}

# --- YEREL MODEL YÜKLEME (LAZY) ---
_tokenizer = None
_model = None
_llm_lock = threading.Lock()

def _ensure_local_llm_loaded():
    global _tokenizer, _model
    if _model is not None:
        return
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    with _llm_lock:
        if _model is not None:
            return
        tok = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
        mdl = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            dtype=torch.float32,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        mdl = mdl.to(torch.device("cpu"))
        mdl.eval()
        _tokenizer = tok
        _model = mdl

# --- YARDIMCI FONKSİYONLAR ---

def calculate_hybrid_match(question: str, text: str) -> float:
    words = [w for w in re.findall(r"\b\w{3,}\b", question.lower()) if w not in TURKISH_STOPS]
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

# --- RETRIEVAL ---

def retrieve_globally_relevant_chunks(
    question: str,
    documents: List[DocumentObject],
    k_per_doc: int = 5,
    max_chunks: int = 5,
    threshold: float = 0.25, # Eşiği 0.35'ten 0.25'e çektim (Türkçe için daha esnek)
    vec_weight: float = 0.65
) -> List[dict]:
    all_candidates = []
    for doc in documents:
        search_results = doc.embedding_store.search(question, k=k_per_doc)
        for res in search_results:
            all_candidates.append({"text": res["text"], "source": doc.filename})
    if not all_candidates: return []
    seen_texts = set()
    unique_candidates = []
    for cand in all_candidates:
        if cand["text"] not in seen_texts:
            seen_texts.add(cand["text"])
            unique_candidates.append(cand)
    emb_model = documents[0].embedding_store.model
    candidate_texts = [c["text"] for c in unique_candidates]
    q_vec = emb_model.encode([question], convert_to_numpy=True)
    c_vecs = emb_model.encode(candidate_texts, convert_to_numpy=True)
    v_scores = (c_vecs @ q_vec.T).squeeze() / (np.linalg.norm(c_vecs, axis=1) * np.linalg.norm(q_vec))
    if v_scores.ndim == 0: v_scores = [v_scores]
    final_results = []
    for i, (cand, v_score) in enumerate(zip(unique_candidates, v_scores)):
        k_score = calculate_hybrid_match(question, cand["text"])
        h_score = (v_score * vec_weight) + (k_score * (1 - vec_weight))
        if h_score >= threshold:
            final_results.append({"score": h_score, "text": cand["text"], "source": cand["source"]})
    sorted_results = sorted(final_results, key=lambda x: x["score"], reverse=True)[:max_chunks]
    return [{"text": res["text"], "source": res["source"]} for res in sorted_results]

# --- GENERATION ---

def generate_answer_from_contexts(question: str, contexts: List[str]) -> str:
    if not contexts: return NO_ANSWER_MSG
    context_text = "\n\n".join(contexts)
    system_prompt = (
        "Sen yardımcı bir yapay zeka asistanısın. Görevin, kullanıcının sorusunu sadece sağlanan bağlama (context) dayanarak cevaplamaktır.\n"
        "İzlenecek adımlar:\n"
        "1. Bağlamı dikkatlice oku.\n"
        "2. Soruyu cevaplayan spesifik cümleleri bul.\n"
        "3. Cevabı açık ve okunabilir bir formatta sentezle.\n"
        "4. Cevabı dökümanın dili ne olursa olsun Türkçe olarak ver.\n"
        f"Eğer bağlam cevabı içermiyorsa, tam olarak şu yanıtı ver: '{NO_ANSWER_MSG}'"
    )
    user_prompt = f"Bağlam:\n{context_text}\n\nSoru:\n{question}"

    if _groq_client:
        try:
            completion = _groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=GROQ_MODEL,
                temperature=0.0,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Groq Hatası: {e}. Yerel modele geçiliyor...")

    # Fallback to Local LLM
    _ensure_local_llm_loaded()
    tokenizer, model = _tokenizer, _model
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    text_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text_prompt, return_tensors="pt", truncation=True, max_length=2048).to(model.device)
    import torch
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=512, do_sample=False, temperature=0.0, repetition_penalty=1.1)
    generated_ids = outputs[0][inputs.input_ids.shape[1]:]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

def summarize_text(contexts: List[str]) -> str:
    if not contexts: return "Özetlenecek içerik bulunamadı."
    context_text = "\n\n".join(contexts)
    system_prompt = (
        "Sen profesyonel bir metin özetleme asistanısın. Görevin, sana verilen metin parçalarını "
        "okumak ve içeriğin ana hatlarını kapsayan, kısa ve öz bir Türkçe özet oluşturmaktır.\n"
        "Özet, dökümanın en önemli noktalarını içermeli ve madde işaretleri kullanılarak sunulmalıdır."
    )
    user_prompt = f"Özetlenecek Metin:\n{context_text}"

    if _groq_client:
        try:
            completion = _groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=GROQ_MODEL,
                temperature=0.0,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Groq Hatası: {e}. Yerel modele geçiliyor...")

    # Fallback to Local LLM
    _ensure_local_llm_loaded()
    tokenizer, model = _tokenizer, _model
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    text_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text_prompt, return_tensors="pt", truncation=True, max_length=2048).to(model.device)
    import torch
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=512, do_sample=False, temperature=0.0, repetition_penalty=1.1)
    generated_ids = outputs[0][inputs.input_ids.shape[1]:]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
