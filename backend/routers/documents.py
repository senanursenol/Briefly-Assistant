from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict
import uuid

from services.document_service import extract_text_from_file
from services.documents import DocumentObject
from services.documents import split_into_chunks

router = APIRouter(prefix="/documents", tags=["documents"])

# Dokümanları bellekte tutmak için store
DOCUMENT_STORE: Dict[str, DocumentObject] = {}

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Tek bir dosya yükler (PDF/DOC/DOCX/TXT), metni ayıklar ve store'a kaydeder.
    """
    filename = file.filename or "document"
    
    # Dosya uzantısını güvenli şekilde kontrol et
    parts = filename.split(".")
    ext = parts[-1].lower() if len(parts) > 1 else ""

    if ext not in ["pdf", "doc", "docx", "txt"]:
        raise HTTPException(status_code=400, detail="Sadece PDF, DOC, DOCX ve TXT dosyaları destekleniyor.")

    try:
        content = await file.read()
        
        # 1. Metni ayıkla
        text = extract_text_from_file(content, ext)

        # 2. Metni parçalara böl
        chunks = split_into_chunks(text)
        
        # 3. DocumentObject oluştur
        doc_obj = DocumentObject(chunks=chunks, filename=filename)

        # 4. ID oluştur ve sakla
        doc_id = str(uuid.uuid4())
        DOCUMENT_STORE[doc_id] = doc_obj
        
        return {
            "doc_id": doc_id,
            "filename": filename,
            "num_chars": len(chunks)
        }

    except Exception as e:
        # Hata detayını kullanıcıya/frontend'e dön
        raise HTTPException(status_code=500, detail=f"Dosya işlenirken hata oluştu: {str(e)}")