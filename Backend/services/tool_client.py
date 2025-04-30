"""
Async HTTP Client for calling internal tool APIs (Trends and Pricing).
"""
import httpx
import asyncio
import json
import re
from typing import Dict, Any, Optional, Tuple, List
from crewai import Agent, Task, Crew, Process

# Import configuration and logging
from config.settings import settings
from config.logging import get_logger

# Configure logging
logger = get_logger(__name__)

# Get base URL from settings
BASE_URL = settings.api.base_url

# Define mapping from conceptual tool names to API endpoint paths and methods
TOOL_API_MAP = {
    # Pricing Tools
    "get_basic_price_estimation": {"method": "POST", "path": "/tools/price/basic"},
    "get_advanced_price_estimation": {"method": "POST", "path": "/tools/price/advanced"},
    # Trend Tools
    "get_search_trends": {"method": "GET", "path": "/tools/trends/search"},
    "get_social_media_trends": {"method": "GET", "path": "/tools/trends/social"},
    "get_news_analysis": {"method": "GET", "path": "/tools/trends/news"},
    "get_resale_market_trends": {"method": "GET", "path": "/tools/trends/resale"},
    # Image Analysis Tools
    "analyze_luxury_item_image": {"method": "POST", "path": "/tools/image/analyze"},
    "compare_luxury_item_images": {"method": "POST", "path": "/tools/image/compare"}
}

class LuxPricerTools:
    """
    Class that provides tool implementations for luxury item appraisal.
    Each method corresponds to a tool that can be used by the agent.
    """
    
    async def get_basic_price_estimation(self, designer: str, model: str, condition_rating: Optional[int] = None) -> Dict[str, Any]:
        """
        Get basic price estimation for a luxury item
        
        Args:
            designer: The designer/brand name (e.g., 'Gucci')
            model: The model name (e.g., 'Marmont')
            condition_rating: Optional condition rating (1-5)
            
        Returns:
            Price estimation result
        """
        parameters = {
            "designer": designer,
            "model": model
        }
        if condition_rating is not None:
            parameters["condition_rating"] = condition_rating
            
        _, result = await execute_tool_call("get_basic_price_estimation", parameters)
        return result
    
    async def get_advanced_price_estimation(self, designer: str, model: str, 
                                       size: Optional[str] = None,
                                       material: Optional[str] = None,
                                       color: Optional[str] = None,
                                       condition_rating: Optional[int] = None) -> Dict[str, Any]:
        """
        Get advanced price estimation for a luxury item with more details
        
        Args:
            designer: The designer/brand name
            model: The model name
            size: Optional size information
            material: Optional material information
            color: Optional color information
            condition_rating: Optional condition rating (1-5)
            
        Returns:
            Advanced price estimation result
        """
        parameters = {
            "designer": designer,
            "model": model
        }
        if size is not None:
            parameters["size"] = size
        if material is not None:
            parameters["material"] = material
        if color is not None:
            parameters["color"] = color
        if condition_rating is not None:
            parameters["condition_rating"] = condition_rating
            
        _, result = await execute_tool_call("get_advanced_price_estimation", parameters)
        return result
    
    async def get_search_trends(self, brand: str, model: str, timeframe: str = "90d") -> Dict[str, Any]:
        """
        Get search trends for a luxury item
        
        Args:
            brand: The brand name
            model: The model name
            timeframe: Time period for analysis (e.g., '90d')
            
        Returns:
            Search trends analysis
        """
        parameters = {
            "brand": brand,
            "model": model,
            "timeframe": timeframe
        }
        
        _, result = await execute_tool_call("get_search_trends", parameters)
        return result
    
    async def get_social_media_trends(self, brand: str, model: str, timeframe: str = "90d") -> Dict[str, Any]:
        """
        Get social media trends for a luxury item
        
        Args:
            brand: The brand name
            model: The model name
            timeframe: Time period for analysis (e.g., '90d')
            
        Returns:
            Social media trends analysis
        """
        parameters = {
            "brand": brand,
            "model": model,
            "timeframe": timeframe
        }
        
        _, result = await execute_tool_call("get_social_media_trends", parameters)
        return result
    
    async def get_news_analysis(self, brand: str, model: str, timeframe: str = "90d") -> Dict[str, Any]:
        """
        Get news analysis for a luxury item
        
        Args:
            brand: The brand name
            model: The model name
            timeframe: Time period for analysis (e.g., '90d')
            
        Returns:
            News analysis results
        """
        parameters = {
            "brand": brand,
            "model": model,
            "timeframe": timeframe
        }
        
        _, result = await execute_tool_call("get_news_analysis", parameters)
        return result
    
    async def get_resale_market_trends(self, brand: str, model: str, timeframe: str = "90d") -> Dict[str, Any]:
        """
        Get resale market trends for a luxury item
        
        Args:
            brand: The brand name
            model: The model name
            timeframe: Time period for analysis (e.g., '90d')
            
        Returns:
            Resale market trend analysis
        """
        parameters = {
            "brand": brand,
            "model": model,
            "timeframe": timeframe
        }
        
        _, result = await execute_tool_call("get_resale_market_trends", parameters)
        return result
        
    async def analyze_luxury_item_image(self, image_path: str, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a luxury item image using vision-capable LLMs
        
        Args:
            image_path: Path to the image file
            query: Optional specific query about the item
            
        Returns:
            Image analysis results including brand, model, materials, etc.
        """
        import aiofiles
        import mimetypes
        from pathlib import Path
        
        # Prepare the multipart/form-data request
        parameters = {}
        if query:
            parameters["query"] = query
            
        # This is a special case that requires direct HTTP call rather than using execute_tool_call
        # because we need to handle file upload
        api_info = TOOL_API_MAP["analyze_luxury_item_image"]
        path = api_info["path"]
        url = f"{BASE_URL}{path}"
        
        logger.info(f"Executing image analysis with image: {image_path}")
        
        try:
            # Get the file mime type
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type:
                mime_type = "application/octet-stream"
                
            # Create form data manually
            form_data = {}
            # Add any text fields
            for key, value in parameters.items():
                form_data[key] = str(value)
                
            # Add provider if needed
            form_data["provider"] = "openai"  # Default to OpenAI for vision models
            
            # Add the image file
            image_filename = Path(image_path).name
            
            # Read the file and prepare it for upload
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with aiofiles.open(image_path, "rb") as f:
                    file_content = await f.read()
                    files = {"image": (image_filename, file_content, mime_type)}
                    
                    # Make the POST request with the form data and file
                    response = await client.post(url, data=form_data, files=files)
                    response.raise_for_status()
                    
                    # Parse and return the response
                    result = response.json()
                    return result
        except Exception as e:
            logger.error(f"Error in analyze_luxury_item_image: {str(e)}", exc_info=True)
            return {"error": f"Image analysis failed: {str(e)}"}
            
    async def compare_luxury_item_images(self, image_paths: List[str], query: Optional[str] = None) -> Dict[str, Any]:
        """
        Compare multiple luxury item images
        
        Args:
            image_paths: List of paths to the image files
            query: Optional specific query about the comparison
            
        Returns:
            Comparison results
        """
        import aiofiles
        import mimetypes
        from pathlib import Path
        
        # Prepare the multipart/form-data request
        parameters = {}
        if query:
            parameters["query"] = query
            
        # This is a special case that requires direct HTTP call rather than using execute_tool_call
        # because we need to handle multiple file uploads
        api_info = TOOL_API_MAP["compare_luxury_item_images"]
        path = api_info["path"]
        url = f"{BASE_URL}{path}"
        
        logger.info(f"Executing image comparison with images: {image_paths}")
        
        try:
            # Get the file mime types
            files = []
            for image_path in image_paths:
                mime_type, _ = mimetypes.guess_type(image_path)
                if not mime_type:
                    mime_type = "application/octet-stream"
                files.append((image_path, mime_type))
                
            # Create form data manually
            form_data = {}
            # Add any text fields
            for key, value in parameters.items():
                form_data[key] = str(value)
                
            # Add provider if needed
            form_data["provider"] = "openai"  # Default to OpenAI for vision models
            
            # Make the POST request with the form data and files
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Prepare the file uploads
                files_for_upload = []
                for i, (image_path, mime_type) in enumerate(files):
                    image_filename = Path(image_path).name
                    async with aiofiles.open(image_path, "rb") as f:
                        file_content = await f.read()
                        files_for_upload.append(("images", (image_filename, file_content, mime_type)))
                
                # Make the POST request with the form data and files
                response = await client.post(url, data=form_data, files=files_for_upload)
                response.raise_for_status()
                
                # Parse and return the response
                result = response.json()
                return result
        except Exception as e:
            logger.error(f"Error in compare_luxury_item_images: {str(e)}", exc_info=True)
            return {"error": f"Image comparison failed: {str(e)}"}

async def execute_tool_call(tool_name: str, parameters: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Executes a single tool call by making an HTTP request to the internal API.

    Args:
        tool_name: The name of the tool to call (must be in TOOL_API_MAP).
        parameters: The parameters for the tool call.

    Returns:
        A tuple containing: (tool_name, result_dict)
        result_dict will contain either the successful JSON response or an error structure.
    """
    if tool_name not in TOOL_API_MAP:
        logger.error(f"Unknown tool name '{tool_name}'")
        return tool_name, {"error": f"Unknown tool: {tool_name}"}

    api_info = TOOL_API_MAP[tool_name]
    method = api_info["method"]
    path = api_info["path"]
    url = f"{BASE_URL}{path}"

    logger.info(f"Executing tool: {tool_name} with params: {parameters}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                # For GET requests, parameters are query parameters
                response = await client.get(url, params=parameters)
            elif method == "POST":
                # For POST requests, parameters are the JSON body
                response = await client.post(url, json=parameters)
            else:
                return tool_name, {"error": f"Unsupported HTTP method {method} for tool {tool_name}"}

            # Check for HTTP errors
            response.raise_for_status()

            # Return the successful JSON response
            result_data = response.json()
            logger.info(f"Tool {tool_name} executed successfully.")
            return tool_name, result_data

    except httpx.RequestError as e:
        error_msg = f"Tool call '{tool_name}' failed: Could not connect to API endpoint {url}. Details: {e}"
        logger.error(f"Error: {error_msg}")
        return tool_name, {"error": error_msg, "tool_name": tool_name}
    except httpx.HTTPStatusError as e:
        error_body = e.response.text
        try:
            # Try to parse FastAPI error detail
            error_detail = e.response.json().get("detail", error_body)
        except Exception:
            error_detail = error_body
        error_msg = f"Tool call '{tool_name}' failed: API returned status {e.response.status_code}. Detail: {error_detail}"
        logger.error(f"Error: {error_msg}")
        return tool_name, {"error": error_msg, "status_code": e.response.status_code, "tool_name": tool_name}
    except Exception as e:
        error_msg = f"Tool call '{tool_name}' failed: An unexpected error occurred. Details: {e}"
        logger.error(f"Error: {error_msg}")
        return tool_name, {"error": error_msg, "tool_name": tool_name}

async def execute_tool_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the tool call plan

    Args:
        plan: Plan containing tool calls list

    Returns:
        Dictionary of tool call results
    """
    tool_results = {}
    
    # Ensure plan contains tool calls
    tool_calls = plan.get("tool_calls", [])
    if not tool_calls:
        logger.warning("No tool calls in plan")
        return {"error": "No tool calls in plan"}
    
    # Initialize the tool client
    tools = LuxPricerTools()
    
    # Create Tool Agent
    tool_agent = Agent(
        role="Luxury Appraisal Tool Expert",
        goal="Execute luxury appraisal tool calls accurately and efficiently",
        backstory="You are an expert in luxury appraisal tools, capable of seamlessly integrating various tools to provide accurate data for the appraisal process.",
        verbose=settings.debug,
        allow_delegation=False
    )
    
    # Create tasks for each tool call
    tasks = []
    
    for call in tool_calls:
        tool_name = call.get("tool_name")
        parameters = call.get("parameters", {})
        
        # Skip invalid tool names
        if not tool_name:
            continue
        
        # Create parameter string for task description
        param_str = ", ".join([f"{k}={v}" for k, v in parameters.items()])
        task_desc = f"Execute tool call: {tool_name}({param_str})"
        
        # Add specific instructions based on tool type
        tool_instructions = ""
        if tool_name == "get_basic_price_estimation":
            tool_instructions = f"""
            Use get_basic_price_estimation tool to obtain basic price estimation.
            Parameters:
            - designer: {parameters.get('designer', 'N/A')}
            - model: {parameters.get('model', 'N/A')}
            - condition_rating: {parameters.get('condition_rating', 'N/A')}
            """
        elif tool_name == "get_advanced_price_estimation":
            tool_instructions = f"""
            Use get_advanced_price_estimation tool to obtain advanced price estimation.
            Parameters:
            - designer: {parameters.get('designer', 'N/A')}
            - model: {parameters.get('model', 'N/A')}
            - size: {parameters.get('size', 'N/A')}
            - material: {parameters.get('material', 'N/A')}
            - color: {parameters.get('color', 'N/A')}
            - condition_rating: {parameters.get('condition_rating', 'N/A')}
            """
        elif tool_name == "get_search_trends":
            tool_instructions = f"""
            Use get_search_trends tool to obtain search trend analysis.
            Parameters:
            - brand: {parameters.get('brand', 'N/A')}
            - model: {parameters.get('model', 'N/A')}
            - timeframe: {parameters.get('timeframe', '90d')}
            """
        elif tool_name == "get_social_media_trends":
            tool_instructions = f"""
            Use get_social_media_trends tool to obtain social media trend analysis.
            Parameters:
            - brand: {parameters.get('brand', 'N/A')}
            - model: {parameters.get('model', 'N/A')}
            - timeframe: {parameters.get('timeframe', '90d')}
            """
        elif tool_name == "get_news_analysis":
            tool_instructions = f"""
            Use get_news_analysis tool to obtain news analysis.
            Parameters:
            - brand: {parameters.get('brand', 'N/A')}
            - model: {parameters.get('model', 'N/A')}
            - timeframe: {parameters.get('timeframe', '90d')}
            """
        elif tool_name == "get_resale_market_trends":
            tool_instructions = f"""
            Use get_resale_market_trends tool to obtain secondhand market trend analysis.
            Parameters:
            - brand: {parameters.get('brand', 'N/A')}
            - model: {parameters.get('model', 'N/A')}
            - timeframe: {parameters.get('timeframe', '90d')}
            """
        
        # Create task with direct API call instead of using CrewAI tools
        # This ensures we can make proper async HTTP requests
        tasks.append((tool_name, parameters))
    
    # Execute all tool calls concurrently
    async_tasks = []
    for tool_name, parameters in tasks:
        async_tasks.append(execute_tool_call(tool_name, parameters))
    
    if async_tasks:
        results = await asyncio.gather(*async_tasks)
        for tool_name, result in results:
            tool_results[tool_name] = result
    
    return tool_results 