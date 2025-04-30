"""
Router for the main Appraisal Agent endpoint.
"""
from fastapi import APIRouter, HTTPException, Body, status, UploadFile, File, Form
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import os
import json
import tempfile
import shutil
from pathlib import Path

from services.appraisal_crew import LuxuryAppraisalCrew
from config.settings import settings
from config.logging import get_logger

# Configure logging
logger = get_logger(__name__)

router = APIRouter()

# Define upload directory
UPLOAD_DIR = Path("uploads/appraisal")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --- Request/Response Models --- #

class AppraisalRequest(BaseModel):
    query: str = Field(..., description="User query about the luxury item (e.g., 'Value of my black Chanel Classic Flap?')")
    provider: Optional[str] = Field(None, description="Optional LLM provider to use (e.g., 'openai', 'anthropic')")
    model: Optional[str] = Field(None, description="Optional model name to use")

class AppraisalResponse(BaseModel):
    report: str = Field(..., description="The final appraisal report in Markdown format.")
    debug_info: Optional[Dict[str, Any]] = Field(None, description="Optional debug information (plan, tool results).")

# --- API Endpoint --- #

@router.post("/appraise", response_model=AppraisalResponse, tags=["Agent"], summary="Generate Appraisal Report")
async def run_appraisal_agent(
    request: AppraisalRequest = Body(...)
) -> AppraisalResponse:
    """
    Takes a user query about a luxury item, runs the multi-agent appraisal workflow,
    and returns a comprehensive report.

    Workflow:
    1. **Extraction Agent**: Analyzes query and extracts item details
    2. **Research Agent**: Researches market data related to the item
    3. **Valuation Agent**: Determines item value based on details and market data
    4. **Report Agent**: Compiles all information into a professional report
    """
    user_query = request.query
    provider = request.provider
    model = request.model
    
    logger.info(f"--- Starting Appraisal for Query: '{user_query}' ---")
    if provider:
        logger.info(f"Using provider: {provider}")
    if model:
        logger.info(f"Using model: {model}")

    try:
        # Create the specialized appraisal crew
        appraisal_crew = LuxuryAppraisalCrew(provider=provider, model=model)
        
        # 添加测试/演示模式检查
        # 首先确保provider不是None
        if provider and ("test" in provider.lower() or "demo" in provider.lower()) or os.environ.get("MOCK_API_RESPONSE") == "true":
            # 返回演示/测试响应
            logger.info("Using mock API response for test/demo mode")
            with open("reports/data_Chanel_Classic_Flap_20250414_232208.json", "r") as f:
                test_data = json.load(f)
            return AppraisalResponse(report=test_data.get("report", "Mock Report"))
        
        # Run the complete appraisal process
        report = await appraisal_crew.run_appraisal(user_query)
        
        logger.info("--- Appraisal Complete ---")
        
        # Return the result without debug info (debug info removed for cleaner response)
        return AppraisalResponse(report=report)
        
    except Exception as e:
        logger.error(f"Appraisal process failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete the appraisal process: {str(e)}"
        )

@router.post("/appraise/image", response_model=AppraisalResponse, tags=["Agent"], summary="Generate Appraisal Report with Image")
async def run_appraisal_agent_with_image(
    query: str = Form(...),
    image: UploadFile = File(...),
    provider: Optional[str] = Form(None),
    model: Optional[str] = Form(None)
) -> AppraisalResponse:
    """
    Takes a user query and an image of a luxury item, runs the multi-agent appraisal workflow
    including image analysis, and returns a comprehensive report.

    Workflow:
    1. **Extraction Agent**: Analyzes query and extracts item details
    2. **Image Analysis Agent**: Analyzes the uploaded image to extract additional information
    3. **Research Agent**: Researches market data related to the item
    4. **Valuation Agent**: Determines item value based on details, image analysis, and market data
    5. **Report Agent**: Compiles all information into a professional report
    
    The image analysis can provide additional insights such as:
    - Authentication indicators
    - Condition verification
    - Material identification
    - Detection of special editions or rare variants
    - Signs of wear or damage
    """
    logger.info(f"--- Starting Image-Based Appraisal for Query: '{query}' ---")
    logger.info(f"Image: {image.filename}")
    if provider:
        logger.info(f"Using provider: {provider}")
    if model:
        logger.info(f"Using model: {model}")
    
    # Create a temporary file for the uploaded image
    suffix = Path(image.filename).suffix
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file_path = temp_file.name
    temp_file.close()
    
    try:
        # Save the uploaded file to the temporary file
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        # Save the image for persistence
        unique_id = os.path.basename(temp_file_path)
        persistent_path = UPLOAD_DIR / f"{unique_id}{suffix}"
        shutil.copy(temp_file_path, persistent_path)
        logger.info(f"Image saved to {persistent_path}")
        
        # Create the specialized appraisal crew
        appraisal_crew = LuxuryAppraisalCrew(provider=provider, model=model)
        
        # 添加测试/演示模式检查
        if provider and ("test" in provider.lower() or "demo" in provider.lower()) or os.environ.get("MOCK_API_RESPONSE") == "true":
            # 返回演示/测试响应
            logger.info("Using mock API response for test/demo mode")
            with open("reports/data_Chanel_Classic_Flap_20250414_232208.json", "r") as f:
                test_data = json.load(f)
            return AppraisalResponse(report=test_data.get("report", "Mock Report with Image Analysis"))
        
        # Run the complete appraisal process with image
        report = await appraisal_crew.run_appraisal(query, str(persistent_path))
        
        logger.info("--- Image-Based Appraisal Complete ---")
        
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        
        # Return the result
        return AppraisalResponse(report=report)
        
    except Exception as e:
        logger.error(f"Image-based appraisal process failed: {str(e)}", exc_info=True)
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete the image-based appraisal process: {str(e)}"
        )

@router.post("/appraise/markdown", response_class=PlainTextResponse, tags=["Agent"], summary="Generate Appraisal Report (Raw Markdown)")
async def run_appraisal_agent_markdown(
    request: AppraisalRequest = Body(...)
) -> PlainTextResponse:
    """
    Same as /appraise, but returns the report as raw Markdown text.
    """
    response_data = await run_appraisal_agent(request)
    return PlainTextResponse(response_data.report, media_type="text/markdown; charset=utf-8") 