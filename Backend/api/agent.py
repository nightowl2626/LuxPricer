from utils.pdf_generator import generate_appraisal_pdf
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, HTTPException, Body, status
import io
import os
from typing import Union, Dict, Any
from datetime import datetime
import logging
from routers.agent import AppraisalRequest, run_appraisal_agent

# Configure logging
logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(
    prefix="/agent",
    tags=["Agent PDF Generator"],
    responses={404: {"description": "Not found"}},
)

# 导入或提供appraise方法
async def appraise(request: AppraisalRequest):
    """
    包装run_appraisal_agent方法，处理appraisal请求
    
    Args:
        request: 包含查询的AppraisalRequest对象
        
    Returns:
        生成的appraisal报告结果
    """
    logger.info(f"Processing appraisal request: {request.query}")
    try:
        result = await run_appraisal_agent(request)
        # 根据run_appraisal_agent的返回格式，确保我们返回正确的报告内容
        return result.report if hasattr(result, 'report') else result
    except Exception as e:
        logger.error(f"Appraisal failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": f"Appraisal process failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@router.post("/appraise/pdf")
async def generate_appraisal_pdf_endpoint(
    request: Union[AppraisalRequest, Dict[str, Any]]
):
    """
    Generate a professional PDF version of the appraisal report for download.
    
    Supports two modes:
    1. Generate a new appraisal report and convert to PDF (when only query is provided)
    2. Convert an existing report to PDF (when report_content is provided along with query)
    """
    try:
        # Log request information
        logger.info(f"PDF Generation request received: {request}")
        
        # Handle both AppraisalRequest objects and dictionaries
        query = getattr(request, 'query', None) if hasattr(request, 'query') else request.get('query')
        report_content = request.get('report_content') if isinstance(request, dict) else None
        
        if not query:
            logger.warning("PDF Generation failed: Query parameter is required")
            return {
                "status": "error",
                "error": "Query parameter is required",
                "timestamp": datetime.now().isoformat()
            }
        
        # If report content is provided, use it directly
        if report_content:
            logger.info(f"Generating PDF for existing report with query: {query}")
            markdown_content = report_content
        else:
            # Generate a new appraisal report
            logger.info(f"Generating new appraisal report for PDF with query: {query}")
            appraisal_request = AppraisalRequest(query=query)
            appraisal_result = await appraise(appraisal_request)
            
            if isinstance(appraisal_result, dict) and appraisal_result.get("status") == "error":
                logger.error(f"PDF Generation failed: Appraisal error: {appraisal_result.get('error', 'Unknown error')}")
                return appraisal_result
            
            # Get the markdown content
            if isinstance(appraisal_result, dict) and "appraisal_report" in appraisal_result:
                # JSON response format
                markdown_content = appraisal_result["appraisal_report"]["content"]
            else:
                # Direct markdown response
                markdown_content = appraisal_result
        
        # Log the length of markdown content for debugging
        logger.info(f"Markdown content length: {len(markdown_content)} characters")
        
        # 提取物品名称用于元数据
        item_name = query
        if ":" in query:
            item_name = query.split(":", 1)[1].strip()
        elif "?" in query:
            item_name = query.replace("?", "").strip()
            
        # Get metadata from the appraisal result
        metadata = {
            "title": f"奢侈品估值报告: {item_name}",
            "author": "Luxury Expert System",
            "subject": "奢侈品估值",
            "keywords": "奢侈品,估值,报告",
            "reference": f"AP-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "item": item_name
        }
        
        # Generate PDF directly to bytes without writing to file
        logger.info("Generating PDF from markdown content...")
        pdf_bytes = generate_appraisal_pdf(markdown_content, output_path=None, metadata=metadata)
        logger.info(f"PDF generated successfully, size: {len(pdf_bytes)} bytes")
        
        # Create filename for download
        sanitized_query = ''.join(c if c.isalnum() else '_' for c in item_name[:30])
        filename = f"Luxury_Item_Appraisal_{sanitized_query}_{datetime.now().strftime('%Y-%m-%d')}.pdf"
        logger.info(f"Sending PDF response with filename: {filename}")
        
        # Return PDF as a downloadable file
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": f"Failed to generate PDF: {str(e)}",
            "timestamp": datetime.now().isoformat()
        } 