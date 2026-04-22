from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from routers.documents import DOCUMENT_STORE
from services.qa_service import generate_answer_from_contexts, retrieve_globally_relevant_chunks
from services.qa_service import summarize_documents

router = APIRouter(prefix="/qa", tags=["qa"])

class QuestionRequest(BaseModel):
    doc_ids: List[str]
    question: str

class QAResponse(BaseModel):
    answer: str
    context_chunks: List[str]

class SummarizeRequest(BaseModel):
    doc_ids: List[str]

@router.post("/summarize")
async def summarize_docs(request: SummarizeRequest):
    """
    Yüklenen dokümanların ID'lerini alıp genel bir özet döndürür.
    """
    if not request.doc_ids:
        raise HTTPException(status_code=400, detail="Özetlenecek doküman ID'si bulunamadı.")
        
    try:
        summary = summarize_documents(request.doc_ids)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    if not contexts or len(" ".join(contexts).strip()) < 50:
        return QAResponse(
            answer="I am sorry, but I could not find relevant information in the uploaded documents.",
            context_chunks=[]
        )

    # 2. LLM ile Cevap Üretme
    answer = generate_answer_from_contexts(
        question=request.question,
        contexts=contexts
    )

    return QAResponse(
        answer=answer,
        context_chunks=contexts
    )