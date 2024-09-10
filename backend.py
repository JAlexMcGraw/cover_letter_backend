from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from langchain_community.document_loaders import SeleniumURLLoader
from src.backend.utils import CoverLetterGenerator
from bs4 import BeautifulSoup
from pydantic import BaseModel
from copy import deepcopy
from docx import Document
from typing import Dict
import io
import requests
from PyPDF2 import PdfReader
import PyPDF2
import logging 
import traceback
import uvicorn
import json

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Adjust this to your frontend's URL
    # allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_pdf(pdf_source, is_local_file=False):
    # Process the PDF from URL or local file
    file = io.BytesIO(requests.get(pdf_source).content) if not is_local_file else open(pdf_source, 'rb')

    # Extract text from PDF
    pdf_reader = PyPDF2.PdfFileReader(file)
    text = ""
    for page in range(pdf_reader.numPages):
        text += pdf_reader.getPage(page).extractText()
    
    if is_local_file:
        file.close()

    return {"status": "Processing completed",
            "text": text}

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        content = await file.read()
        pdf_reader = PdfReader(io.BytesIO(content))

        text = ""
        for page in range(pdf_reader.numPages):
            text += pdf_reader.getPage(page).extractText()
        
        if not text:
            raise HTTPException(status_code=422, detail="Unable to extract text from the PDF")
        
        return {"text": text}  # Return first 200 characters as preview
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Error processing PDF: {str(e)}")



###########################
@app.post("/load_job_url/")
async def process_job_url(job_posting_url: Dict[str,str]) -> Dict[str,str]:
    html = SeleniumURLLoader([job_posting_url['job_posting_url']]).load()

    soup = BeautifulSoup(html[0].page_content, 'html.parser')
    text_content = soup.get_text(separator=' ', strip=True)
    
    return {"text": text_content}


class CoverLetterData(BaseModel):
    job_post_text: str
    resume_text: str
    openai_api_key: str


@app.post("/generate_cover_letter/")
async def cover_letter_generate(data: CoverLetterData):
    try:
    #     logger.info("Received request for cover letter generation")
    #     logger.debug(f"Job post text: {data.job_post_text[:100]}...")
    #     logger.debug(f"Resume text: {data.resume_text[:100]}...")
    #     logger.debug(f"API Key (first 5 chars): {data.openai_api_key[:5]}...")

        # Here you would typically use your CoverLetterGenerator
        # For now, we'll just return a placeholder
        # cover_letter_str = f"Generated cover letter based on job post and resume."

        generator = CoverLetterGenerator(
            resume_text=data.resume_text,
            job_posting_text=data.job_post_text,
            openai_api_key=data.openai_api_key
        )
        
        logger.debug("GENERATOR INSTANCE CREATED")
        cover_letter_str = generator.generate_cover_letter()
        
        logger.info("Cover letter generated successfully")
        return {'text': cover_letter_str}
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

#########################
#########################


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)