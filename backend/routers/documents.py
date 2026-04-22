from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict
import uuid

from services.document_service import extract_text_from_file
from services.documents import DocumentObject, split_into_chunks

router = APIRouter(prefix="/documents", tags=["documents"])

# Dokümanları bellekte tutmak için store
DOCUMENT_STORE: Dict[str, DocumentObject] = {}

@router.post("/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Birden fazla dosyayı aynı anda yükler, metinleri ayıklar ve store'a kaydeder.
    """
    uploaded_docs = []
    
    for file in files:
        filename = file.filename or "document"
        
        parts = filename.split(".")
        ext = parts[-1].lower() if len(parts) > 1 else ""

        # GÜNCELLENEN KISIM: Kapıdaki güvenliğe resimleri içeri almasını söylüyoruz
        if ext not in ["pdf", "docx", "txt", "png", "jpg", "jpeg"]:
            continue 

        try:
            content = await file.read()
            
            # 1. Metni ayıkla
            text = extract_text_from_file(content, ext)

            # 2. Metni parçalara böl
            chunks = split_into_chunks(text)
            
            # 3. DocumentObject oluştur
            doc_obj = DocumentObject(chunks=chunks)

            # 4. ID oluştur ve sakla
            doc_id = str(uuid.uuid4())
            DOCUMENT_STORE[doc_id] = doc_obj
            
            uploaded_docs.append({
                "doc_id": doc_id,
                "filename": filename
            })

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{filename} işlenirken hata oluştu: {str(e)}")
            
    if not uploaded_docs:
        raise HTTPException(status_code=400, detail="Geçerli bir dosya bulunamadı.")

    return {"documents": uploaded_docs}