from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from documentIntelligence import pdfUsingOCR
import os
from typing import Dict

app = FastAPI(
    title="Nyaya Document Intelligence API",
    description="API for extracting and summarizing text from PDF legal documents using OCR and Groq API.",
    version="1.0.0"
)

# Configure CORS (restrict origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),  # e.g., ["https://your-frontend-domain.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post(
    "/extract-text/",
    summary="Extract and summarize text from a PDF",
    description="Receives a PDF file, extracts text using OCR, and returns a summarized version using the Groq API."
)
async def extract_text(file: UploadFile = File(...)) -> Dict:
    try:
        # Validate file type
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        result = pdfUsingOCR(content)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to process PDF")
        
        return {"text": result}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get(
    "/",
    summary="Check API status",
    description="Returns a message indicating that the Nyaya Document Intelligence API is running."
)
def root() -> Dict:
    return {"message": "Nyaya Document Intelligence API is running."}