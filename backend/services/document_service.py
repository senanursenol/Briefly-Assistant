from io import BytesIO
from pypdf import PdfReader
import docx
import pytesseract
from PIL import Image
import os
import platform

# WINDOWS KULLANICILARI İÇİN TESSERACT YOLU AYARI
if platform.system() == "Windows":
    # Tesseract'ı kurduğun yer burası değilse, aşağıdaki yolu kendi bilgisayarına göre güncelle
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_file(content: bytes, ext: str) -> str:
    """
    Verilen dosya içeriğinden (bytes) metin ayıklar.
    Desteklenen uzantılar: pdf, docx, txt, png, jpg, jpeg.
    """
    ext = ext.lower()
    
    # YÖNLENDİRİCİ - TXT ve Görseller eklendi
    if ext == "pdf":
        return extract_text_from_pdf(content)
    elif ext == "docx":
        return extract_text_from_docx(content)
    elif ext == "txt":
        return extract_text_from_txt(content)
    elif ext in ["png", "jpg", "jpeg"]:
        return extract_text_from_image(content)
    else:
        raise ValueError(f"Desteklenmeyen dosya formatı: {ext}")

def extract_text_from_pdf(content: bytes) -> str:
    text = ""
    reader = PdfReader(BytesIO(content))
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def extract_text_from_docx(content: bytes) -> str:
    file_stream = BytesIO(content)
    doc = docx.Document(file_stream)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_txt(content: bytes) -> str:
    """
    TXT dosya içeriğinden metin ayıklar.
    """
    try:
        return content.decode("utf-8", errors="ignore")
    except Exception as e:
        raise ValueError(f"TXT dosyası okunurken hata oluştu: {str(e)}")

def extract_text_from_image(content: bytes) -> str:
    """
    Görsel (PNG, JPG) içeriğinden OCR ile metin ayıklar.
    """
    try:
        image = Image.open(BytesIO(content))
        text = pytesseract.image_to_string(image)
        
        # --- CASUS KODUMUZ: Terminale ne okuduğunu yazdıracak ---
        print("\n" + "="*40)
        print("TESSERACT'IN RESİMDE GÖRDÜĞÜ METİN:")
        print(text)
        print("="*40 + "\n")
        # --------------------------------------------------------

        if not text.strip():
            return "No readable text found in this image."
            
        return text
    except Exception as e:
        raise ValueError(f"Görselden metin okunurken hata oluştu: {str(e)}. Tesseract kurulu olmayabilir.")