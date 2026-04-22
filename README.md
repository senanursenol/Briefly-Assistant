# 🧠 Briefly: Akıllı Doküman Asistanı

DocSage, yüklediğiniz PDF ve Word dokümanları ile doğal dilde sohbet etmenizi sağlayan, **RAG (Retrieval-Augmented Generation)** tabanlı yerel bir yapay zeka asistanıdır.

Dokümanlarınızdaki bilgileri analiz eder, semantik (anlamsal) ve anahtar kelime aramalarını birleştirerek (**Hybrid Search**) en doğru cevabı üretir. Verileriniz yerel makinenizde işlenir, dışarıya gönderilmez.

## 🚀 Özellikler

-   **Çoklu Format Desteği:** PDF ve DOCX dosyalarını destekler.
-   **Gelişmiş RAG Mimarisi:**
    -   **Vektör Arama:** Faiss ve `all-MiniLM-L6-v2` ile anlamsal benzerlik.
    -   **Hibrit Arama:** Vektör sonuçlarını anahtar kelime eşleşmeleriyle güçlendirir.
-   **Yapay Zeka Modeli:** `Qwen/Qwen2.5-1.5B-Instruct` modeli ile CPU üzerinde bile hızlı ve tutarlı cevaplar.
-   **Kullanıcı Dostu Arayüz:** Streamlit ile geliştirilmiş modern ve temiz bir sohbet ekranı.
-   **Geçmiş Takibi:** Sohbet geçmişini (History) oturum boyunca saklar.

## 🛠️ Teknolojiler

* **Backend:** Python, FastAPI, Uvicorn
* **Frontend:** Streamlit
* **AI & ML:** PyTorch, HuggingFace Transformers, Sentence-Transformers, Faiss
* **Doküman İşleme:** PyPDF, Python-docx

## 📂 Proje Yapısı

```text
docsage/
├── backend/               # API ve Yapay Zeka Servisleri
│   ├── routers/           # Endpoint'ler (documents, qa)
│   ├── services/          # İş mantığı (embedding, llm, parsing)
│   ├── main.py            # Backend giriş noktası
│   └── requirements.txt   # Backend bağımlılıkları
├── frontend/              # Kullanıcı Arayüzü
│   ├── app.py             # Streamlit uygulaması
│   └── requirements.txt   # Frontend bağımlılıkları
└── README.md              # Proje dokümantasyonu
