# 🧠 DocSage: Akıllı Doküman Asistanı (.NET 8)

DocSage, yüklediğiniz PDF ve Word dokümanları ile doğal dilde sohbet etmenizi sağlayan, **RAG (Retrieval-Augmented Generation)** tabanlı yerel bir yapay zeka asistanıdır.

Dokümanlarınızdaki bilgileri analiz eder, semantik (anlamsal) ve anahtar kelime aramalarını birleştirerek (**Hybrid Search**) en doğru cevabı üretir.

## 🚀 Özellikler

- **Çoklu format desteği:** PDF, DOCX, TXT ve DOC (LibreOffice/antiword ile)
- **Gelişmiş RAG mimarisi:**
  - **Vektör arama:** ONNX + `paraphrase-multilingual-MiniLM-L12-v2` (Türkçe/İngilizce)
  - **Hibrit arama:** Vektör + anahtar kelime skorlaması
- **Yapay zeka:** Groq API (varsayılan) veya yerel GGUF model (LLamaSharp)
- **Modern arayüz:** Blazor Server
- **Geçmiş takibi:** Oturum boyunca sohbet geçmişi

## 🛠️ Teknolojiler

| Katman | Teknoloji |
|--------|-----------|
| API | ASP.NET Core 8, C# |
| UI | Blazor Server (.NET 8) |
| Embeddings | Microsoft.ML.OnnxRuntime, HuggingFace ONNX |
| Vektör arama | Bellek içi L2 (Faiss eşdeğeri) |
| LLM | Groq REST API / LLamaSharp (GGUF) |
| Doküman | PdfPig, Open XML SDK, LibreOffice |

## 📂 Proje yapısı

```text
docsage/
├── DocSage.sln
├── src/
│   ├── DocSage.Api/           # REST API (port 8000)
│   ├── DocSage.Web/           # Blazor UI (port 8080 / 8501 Docker)
│   ├── DocSage.Core/          # Modeller ve sözleşmeler
│   └── DocSage.Infrastructure/ # RAG, embedding, LLM, dosya işleme
├── docker-compose.yml
└── .env.example
```

## ⚙️ Kurulum

### Gereksinimler

- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)
- (İsteğe bağlı) Groq API anahtarı
- (İsteğe bağlı) Yerel LLM için GGUF model dosyası

### Yerel çalıştırma

```bash
# API
cd src/DocSage.Api
dotnet run

# UI (ayrı terminal)
cd src/DocSage.Web
set BACKEND_URL=http://localhost:8000
dotnet run
```

- API: http://localhost:8000
- UI: https://localhost:7xxx veya launchSettings portu

### Docker

```bash
cp .env.example .env
# .env içine GROQ_API_KEY ekleyin

docker compose up --build
```

- API: http://localhost:8000
- UI: http://localhost:8501

## 🔑 Ortam değişkenleri

| Değişken | Açıklama |
|----------|----------|
| `GROQ_API_KEY` | Groq API anahtarı (önerilen) |
| `GROQ_MODEL` | Groq model adı (varsayılan: `llama-3.3-70b-versatile`) |
| `USE_LOCAL_LLM` | `true` ise Groq yerine yerel GGUF kullanılır |
| `LOCAL_MODEL_PATH` | GGUF dosya yolu |
| `MODEL_CACHE_DIR` | Embedding model önbellek dizini |
| `Backend__Url` | Blazor → API adresi |

## 📡 API uç noktaları

| Metot | Yol | Açıklama |
|-------|-----|----------|
| GET | `/` | Sağlık kontrolü |
| POST | `/documents/upload` | Dosya yükleme |
| POST | `/qa` | Soru-cevap |
| POST | `/qa/summarize` | Doküman özeti |

## 🤖 Yerel LLM (isteğe bağlı)

1. [Qwen2.5-1.5B-Instruct GGUF](https://huggingface.co/Qwen) indirin
2. `LOCAL_MODEL_PATH` veya `%LocalAppData%/DocSage/models/llm/*.gguf` konumuna koyun
3. `USE_LOCAL_LLM=true` ayarlayın (veya `GROQ_API_KEY` boş bırakın)

## 📝 Notlar

- İlk çalıştırmada embedding modeli HuggingFace'den indirilir (~140 MB).
- `.doc` dosyaları için Docker imajında LibreOffice ve antiword kuruludur.
- Windows'ta `.doc` için LibreOffice kurulumu önerilir (`soffice` PATH'te olmalı).
