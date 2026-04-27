from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from routers.documents import DOCUMENT_STORE
from services.qa_service import (
    generate_answer_from_contexts, 
    retrieve_globally_relevant_chunks,
    summarize_text
)

router = APIRouter(prefix="/qa", tags=["qa"])

class QuestionRequest(BaseModel):
    doc_ids: List[str]
    question: str

class QAResponse(BaseModel):
    answer: str
    context_chunks: List[dict] # Her biri {"text": ..., "source": ...} içerecek

@router.post("/", response_model=QAResponse)
def qa_endpoint(request: QuestionRequest):
    documents = []
    for doc_id in request.doc_ids:
        if doc_id not in DOCUMENT_STORE:
            raise HTTPException(status_code=404, detail=f"Doküman bulunamadı: {doc_id}")
        documents.append(DOCUMENT_STORE[doc_id])

    # 1. Semantik Arama (Retrieval)
    contexts = retrieve_globally_relevant_chunks(
        question=request.question,
        documents=documents,
        k_per_doc=5,
        max_chunks=5
    )

    # Bağlam yetersizse veya boşsa erken dönüş yap
    if not contexts or len(" ".join([c["text"] for c in contexts]).strip()) < 50:
        return QAResponse(
            answer="Üzgünüm, bu sorunun cevabını dökümanlarda bulamadım.",
            context_chunks=[]
        )

    # 2. LLM ile Cevap Üretme
    answer = generate_answer_from_contexts(
        question=request.question,
        contexts=[c["text"] for c in contexts]
    )

    return QAResponse(
        answer=answer,
        context_chunks=contexts
    )

class SummarizeRequest(BaseModel):
    doc_id: str

class SummarizeResponse(BaseModel):
    summary: str

@router.post("/summarize", response_model=SummarizeResponse)
def summarize_endpoint(request: SummarizeRequest):
    if request.doc_id not in DOCUMENT_STORE:
        raise HTTPException(status_code=404, detail=f"Doküman bulunamadı: {request.doc_id}")
    
    doc = DOCUMENT_STORE[request.doc_id]
    
    # Özet için dökümanın ilk 10 parçasını alıyoruz (CPU-LLM limitleri nedeniyle)
    summary_contexts = doc.chunks[:10]
    
    summary = summarize_text(summary_contexts)
    
    return SummarizeResponse(summary=summary)
