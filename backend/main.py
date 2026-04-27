from fastapi import FastAPI
from routers.documents import router as documents_router
from routers.qa import router as qa_router 

app = FastAPI(title="Document QA API")

# Router'ları ana uygulamaya ekliyoruz
app.include_router(documents_router)
app.include_router(qa_router)

# Sağlık kontrolü için basit bir ana sayfa endpoint'i
@app.get("/")
def read_root():
    return {"message": "DocSage API is running correctly!"}