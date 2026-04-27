from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

class EmbeddingStore:
    """
    Metinleri vektörlere (embedding) dönüştürür ve Faiss kullanarak
    hızlı benzerlik araması (similarity search) yapılmasını sağlar.
    """
    _shared_model = None

    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        # Çok dilli (Türkçe destekli) model kullanıyoruz
        if EmbeddingStore._shared_model is None:
            from sentence_transformers import SentenceTransformer
            EmbeddingStore._shared_model = SentenceTransformer(model_name)
        self.model = EmbeddingStore._shared_model
        self.index = None
        self.texts = []

    def build_index(self, texts: List[str]):
        """
        Verilen metin listesi için vektör indeksi oluşturur.
        """
        if not texts:
            raise ValueError("Index oluşturmak için metin yok.")

        # Metinleri vektöre çevir
        embeddings = self.model.encode(texts)

        # Hata kontrolü
        if embeddings.ndim != 2 or embeddings.shape[0] == 0:
            raise ValueError("Geçerli embedding üretilemedi.")

        dim = embeddings.shape[1]

        # Faiss L2 (Öklid mesafesi) indeksi oluştur
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(embeddings)

        # Metinleri hafızada tut (sonuçları döndürmek için)
        self.texts = texts

    def search(self, query: str, k: int = 5):
        """
        Verilen sorguya (query) en benzer 'k' adet metni döndürür.
        """
        if not self.index:
             return []
             
        q_emb = self.model.encode([query])
        distances, indices = self.index.search(q_emb, k)

        results = []
        for idx in indices[0]:
            # Geçerli bir indeks mi kontrol et
            if 0 <= idx < len(self.texts):
                results.append({
                    "text": self.texts[idx]
                })

        return results