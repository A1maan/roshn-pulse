"""
ROSHN PULSE Module 3: FastAPI Service
======================================
REST API for the Auto-Report Scribe service

Endpoints:
- POST /extract - Extract from text
- POST /upload - Upload file (txt/pdf/docx) and extract
- POST /generate-report - Generate PDF report
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import tempfile
import shutil
from datetime import datetime

from extractor import DailyLogExtractor
from report_generator import ReportGenerator
from schema import DailyLogExtraction

# Initialize FastAPI app
app = FastAPI(
    title="ROSHN PULSE - Auto-Report Scribe API",
    description="Module 3: NLP-powered extraction service for construction daily logs",
    version="1.0.0"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
extractor = DailyLogExtractor()
report_generator = ReportGenerator()

# Request/Response models
class TextExtractionRequest(BaseModel):
    """Request model for text extraction"""
    text: str
    generate_pdf: bool = False

class ExtractionResponse(BaseModel):
    """Response model for extraction"""
    success: bool
    message: str
    data: Optional[dict] = None
    pdf_url: Optional[str] = None


# Health check endpoint
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "ROSHN PULSE - Auto-Report Scribe",
        "module": "3",
        "status": "operational",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "extractor": "loaded",
        "report_generator": "ready",
        "timestamp": datetime.now().isoformat()
    }


# Main extraction endpoint
@app.post("/extract", response_model=ExtractionResponse)
async def extract_from_text(request: TextExtractionRequest):
    """
    Extract structured data from raw text

    Args:
        request: TextExtractionRequest with text and options

    Returns:
        ExtractionResponse with extracted data
    """
    try:
        # Perform extraction
        result = extractor.extract_from_text(request.text)

        # Convert to dict
        data = {
            "metadata": {
                "log_date": str(result.log_date) if result.log_date else None,
                "site_name": result.site_name,
                "submitted_by": result.submitted_by,
            },
            "statistics": {
                "total_tasks_completed": result.total_tasks_completed,
                "total_blockers": result.total_blockers,
                "total_incidents": result.total_incidents,
            },
            "completed_tasks": [
                {
                    "task_name": task.task_name,
                    "location": task.location,
                    "crew": task.crew
                }
                for task in result.completed_tasks
            ],
            "blockers": [
                {
                    "issue": blocker.issue,
                    "affected_task": blocker.affected_task,
                    "cause": blocker.cause
                }
                for blocker in result.blockers
            ],
            "incidents": [
                {
                    "incident_type": incident.incident_type,
                    "description": incident.description,
                    "severity": incident.severity,
                    "action_taken": incident.action_taken
                }
                for incident in result.incidents
            ]
        }

        # Generate PDF if requested
        pdf_url = None
        if request.generate_pdf:
            # Create reports directory
            os.makedirs("data/reports", exist_ok=True)

            # Generate PDF
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"report_{timestamp}.pdf"
            pdf_path = f"data/reports/{pdf_filename}"

            report_generator.generate_pdf(result, pdf_path)
            pdf_url = f"/reports/{pdf_filename}"

        return ExtractionResponse(
            success=True,
            message="Extraction completed successfully",
            data=data,
            pdf_url=pdf_url
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


# File upload endpoint
@app.post("/upload")
async def upload_and_extract(file: UploadFile = File(...), generate_pdf: bool = False):
    """
    Upload a file and extract structured data

    Supports: .txt, .pdf, .docx

    Args:
        file: Uploaded file
        generate_pdf: Whether to generate PDF report

    Returns:
        Extraction results
    """
    try:
        # Check file type
        filename = file.filename.lower()
        if not (filename.endswith('.txt') or filename.endswith('.pdf') or filename.endswith('.docx')):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload .txt, .pdf, or .docx files"
            )

        # Read file content
        content = await file.read()

        # Extract text based on file type
        if filename.endswith('.txt'):
            text = content.decode('utf-8')
        elif filename.endswith('.pdf'):
            text = extract_text_from_pdf(content)
        elif filename.endswith('.docx'):
            text = extract_text_from_docx(content)

        # Process extraction
        request = TextExtractionRequest(text=text, generate_pdf=generate_pdf)
        return await extract_from_text(request)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")


# PDF download endpoint
@app.get("/reports/{filename}")
async def download_report(filename: str):
    """
    Download a generated PDF report

    Args:
        filename: Report filename

    Returns:
        PDF file
    """
    file_path = f"data/reports/{filename}"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(
        file_path,
        media_type='application/pdf',
        filename=filename
    )


# Utility functions
def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF file"""
    import PyPDF2
    from io import BytesIO

    pdf_file = BytesIO(content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)

    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"

    return text


def extract_text_from_docx(content: bytes) -> str:
    """Extract text from Word document"""
    from docx import Document
    from io import BytesIO

    doc_file = BytesIO(content)
    doc = Document(doc_file)

    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"

    return text


# Main entry point
if __name__ == "__main__":
    import uvicorn

    print("=" * 80)
    print("ROSHN PULSE - Module 3: Auto-Report Scribe API")
    print("=" * 80)
    print("\nStarting FastAPI server...")
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print("\nPress CTRL+C to stop\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
