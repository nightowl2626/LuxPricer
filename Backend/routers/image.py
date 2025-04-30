"""
Router for the image analysis API endpoints.
"""
from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import os
import shutil
import tempfile
import uuid
from pathlib import Path
import asyncio
import logging

# Import image analysis tools
from tools.image_analysis import analyze_luxury_item, compare_luxury_items

# Import configuration and logging
from config.settings import settings
from config.logging import get_logger

# Configure logging
logger = get_logger(__name__)

# Create router
router = APIRouter()

# Define upload directory
UPLOAD_DIR = Path("uploads/images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --- Request/Response Models --- #

class ImageAnalysisResponse(BaseModel):
    brand: Optional[str] = Field(None, description="Identified brand")
    model: Optional[str] = Field(None, description="Identified model")
    materials: Optional[List[str]] = Field(None, description="Detected materials")
    design_elements: Optional[List[str]] = Field(None, description="Key design elements")
    authenticity_indicators: Optional[List[str]] = Field(None, description="Authenticity indicators")
    condition: Optional[Dict[str, Any]] = Field(None, description="Condition assessment")
    production_era: Optional[str] = Field(None, description="Estimated production era/year")
    notable_features: Optional[List[str]] = Field(None, description="Notable features")
    raw_response: Optional[str] = Field(None, description="Raw response from the LLM")
    structured: Optional[bool] = Field(None, description="Whether the response was successfully structured")
    error: Optional[str] = Field(None, description="Error message, if any")

class ComparisonResponse(BaseModel):
    is_same_model: Optional[bool] = Field(None, description="Whether items appear to be the same model")
    key_differences: Optional[List[str]] = Field(None, description="Key differences between items")
    authenticity_indicators: Optional[Dict[str, Any]] = Field(None, description="Authenticity indicators")
    condition_comparison: Optional[Dict[str, Any]] = Field(None, description="Condition comparison")
    value_comparison: Optional[Dict[str, Any]] = Field(None, description="Value comparison")
    individual_analyses: Optional[List[Dict[str, Any]]] = Field(None, description="Individual analyses of each image")
    raw_response: Optional[str] = Field(None, description="Raw response from the LLM")
    structured: Optional[bool] = Field(None, description="Whether the response was successfully structured")
    error: Optional[str] = Field(None, description="Error message, if any")

# Function to clean up temporary files
def cleanup_temp_file(file_path: str):
    """Remove a temporary file after a delay"""
    try:
        # Delete after a delay to ensure the file is not in use
        asyncio.sleep(300)  # 5 minutes
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        logger.error(f"Error deleting temporary file {file_path}: {e}")

# --- API Endpoints --- #

@router.post("/analyze", response_model=ImageAnalysisResponse, tags=["Image Analysis"])
async def analyze_image(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    query: Optional[str] = Form(None),
    provider: str = Form("openai")
):
    """
    Analyze a luxury item image using LLM vision models.
    
    - **image**: Image file of the luxury item
    - **query**: Optional specific query about the item
    - **provider**: LLM provider to use (default: openai)
    
    Returns detailed analysis of the luxury item in the image.
    """
    logger.info(f"Image analysis request received: {image.filename}, provider: {provider}")
    
    # Create a temporary file for the uploaded image
    suffix = Path(image.filename).suffix
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file_path = temp_file.name
    temp_file.close()
    
    try:
        # Save the uploaded file to the temporary file
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        # Analyze the image
        result = await analyze_luxury_item(temp_file_path, query, provider)
        
        # Add cleanup task
        background_tasks.add_task(cleanup_temp_file, temp_file_path)
        
        # Save the image for persistence if needed
        if not result.get("error"):
            unique_id = str(uuid.uuid4())
            persistent_path = UPLOAD_DIR / f"{unique_id}{suffix}"
            shutil.copy(temp_file_path, persistent_path)
            logger.info(f"Image saved to {persistent_path}")
            
            # Add image path to result
            result["image_path"] = str(persistent_path)
        
        logger.info("Image analysis completed successfully")
        return result
    
    except Exception as e:
        logger.error(f"Error in image analysis: {str(e)}", exc_info=True)
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")

@router.post("/compare", response_model=ComparisonResponse, tags=["Image Analysis"])
async def compare_images(
    background_tasks: BackgroundTasks,
    images: List[UploadFile] = File(...),
    query: Optional[str] = Form(None),
    provider: str = Form("openai")
):
    """
    Compare multiple luxury item images for authentication, condition assessment, and value comparison.
    
    - **images**: List of image files of luxury items to compare
    - **query**: Optional specific query about the comparison
    - **provider**: LLM provider to use (default: openai)
    
    Returns detailed comparison of the luxury items in the images.
    """
    if len(images) < 2:
        raise HTTPException(status_code=400, detail="At least two images are required for comparison")
    
    logger.info(f"Image comparison request received: {len(images)} images, provider: {provider}")
    
    # Create temporary files for the uploaded images
    temp_files = []
    
    try:
        for image in images:
            suffix = Path(image.filename).suffix
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file_path = temp_file.name
            temp_file.close()
            
            # Save the uploaded file to the temporary file
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            
            temp_files.append(temp_file_path)
        
        # Compare the images
        result = await compare_luxury_items(temp_files, query, provider)
        
        # Save the images for persistence if needed
        if not result.get("error"):
            image_paths = []
            for i, temp_file_path in enumerate(temp_files):
                suffix = Path(temp_file_path).suffix
                unique_id = str(uuid.uuid4())
                persistent_path = UPLOAD_DIR / f"{unique_id}{suffix}"
                shutil.copy(temp_file_path, persistent_path)
                image_paths.append(str(persistent_path))
            
            # Add image paths to result
            result["image_paths"] = image_paths
        
        # Add cleanup tasks
        for temp_file_path in temp_files:
            background_tasks.add_task(cleanup_temp_file, temp_file_path)
        
        logger.info("Image comparison completed successfully")
        return result
    
    except Exception as e:
        logger.error(f"Error in image comparison: {str(e)}", exc_info=True)
        # Clean up the temporary files
        for temp_file_path in temp_files:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Image comparison failed: {str(e)}") 