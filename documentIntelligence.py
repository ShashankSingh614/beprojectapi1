import platform
from pathlib import Path
import pytesseract
try:
    import fitz 
except ImportError:
    print("PyMuPDF not found. Install it with: pip install PyMuPDF")
    exit(1)
from PIL import Image
import io
import requests
import tempfile
import logging
from typing import Optional
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
API_KEY = "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"  # Hardcoded API key
API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
OUT_DIRECTORY = Path(os.getenv("OUTPUT_DIR", "~/Nyaya/logs")).expanduser()
TEXT_FILE = OUT_DIRECTORY / Path("pdfTextExtractor.txt")

# Ensure output directory exists
OUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

# Configure Tesseract path for Windows
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

def pdfUsingOCR(pdf_content: bytes) -> Optional[str]:
    """
    Extract text from a PDF using OCR and summarize it.
    
    Args:
        pdf_content: Bytes content of the PDF file.
    
    Returns:
        Summarized text or None if an error occurs.
    """
    try:
        # Create a temporary file for the PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(pdf_content)
            temp_pdf_path = Path(temp_pdf.name)
        
        # Open PDF with PyMuPDF
        try:
            pdf_document = fitz.open(temp_pdf_path)
        except Exception as e:
            logger.error(f"Error opening PDF: {e}")
            return None
        
        page_count = len(pdf_document)
        logger.info(f"Converting {page_count} pages...")
        
        # Process each page and extract text using OCR
        with open(TEXT_FILE, "w", encoding='utf-8') as output_file:
            for page_num in range(page_count):
                logger.info(f"Processing page {page_num + 1}/{page_count}")
                
                page = pdf_document[page_num]
                mat = fitz.Matrix(2.0, 2.0)  # Zoom for better OCR quality
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                image = Image.open(io.BytesIO(img_data))
                
                # Run OCR
                text = pytesseract.image_to_string(image)
                text = text.replace("-\n", "")
                
                # Write to file
                output_file.write(f"--- Page {page_num + 1} ---\n")
                output_file.write(text + "\n\n")
        
        pdf_document.close()
        
        # Clean up temporary file
        temp_pdf_path.unlink()
        
        # Summarize the extracted text
        summary = pdfSummarize(TEXT_FILE)
        return summary
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return None

def call_groq_summary(prompt: str) -> str:
    """
    Call Groq API to summarize text.
    
    Args:
        prompt: Text to summarize.
    
    Returns:
        Summarized text or error message.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    data = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Read the following legal case document and summarize it in clear, factual bullet points. "
                    "Use plain language that can be understood by a common person. "
                    "Do not include legal jargon, interpretations, or formatting like asterisks or emojis. "
                    "Give final output no prompt from your side. Just provide the facts clearly, section by section:\n\n"
                    f"{prompt}"
                )
            }
        ]
    }
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        else:
            logger.error(f"Groq API error: {response.status_code} {response.text}")
            return f"Error summarizing text: {response.text}"
    except Exception as e:
        logger.error(f"Error calling Groq API: {e}")
        return f"Error summarizing text: {str(e)}"

def pdfSummarize(file_path: Path) -> Optional[str]:
    """
    Read extracted text and generate a summary using Groq API.
    
    Args:
        file_path: Path to the text file containing extracted text.
    
    Returns:
        Summarized text or None if an error occurs.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        if not text.strip():
            logger.error("Extracted text is empty")
            return None
        
        summary = call_groq_summary(text)
        summary_final = summary.replace("*", "")  # Remove any asterisks
        return summary_final
    
    except FileNotFoundError:
        logger.error(f"Text file not found: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Error summarizing text: {e}")
        return None