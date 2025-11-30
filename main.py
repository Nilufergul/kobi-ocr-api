# main.py
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import Any, Dict

from table import extract_all_tables_from_ocr_text

app = FastAPI()


class OCRTextRequest(BaseModel):
    text: str


def normalize_text(text: str) -> str:
    """
    Eğer metinde '\\n' karakteri çok geçiyor ama gerçek newline az ise,
    '\\n' dizilerini gerçek satır sonuna çevir.
    (Mistral çıktısında bazen böyle geliyor.)
    """
    if "\\n" in text and text.count("\n") < 10:
        text = text.replace("\\n", "\n")
    return text


def run_tables_pipeline(text: str) -> Dict[str, Any]:
    """
    Ortak tablo çıkarma fonksiyonu:
    - metni normalize et
    - tabloları title/columns/rows formatında çıkar
    """
    text = normalize_text(text)
    tables = extract_all_tables_from_ocr_text(text)

    # Artık DataFrame yok, direkt JSON objeleri dönüyoruz
    return {"tables": tables}


# 1) n8n için kullanılacak endpoint: JSON body ile text alıyor
@app.post("/ocr")
async def ocr_text(request: OCRTextRequest):
    """
    Body: { "text": "<OCR'den gelen markdown/text>" }
    """
    return run_tables_pipeline(request.text)


# 2) İstersen lokal test için dosya upload endpoint'i de dursun
@app.post("/ocr-file")
async def ocr_file(file: UploadFile = File(...)):
    """
    Multipart ile text dosyası upload etmek için.
    Örn: curl ile:
      curl -X POST "http://127.0.0.1:8000/ocr-file" \
           -F "file=@ocr.txt;type=text/plain"
    """
    content = await file.read()
    text = content.decode("utf-8")
    return run_tables_pipeline(text)
