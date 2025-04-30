#!/usr/bin/env python3

"""
Image Analysis Tool for Luxury Item Identification and Authentication.
This tool uses vision-capable LLMs to analyze images of luxury items.
"""

import os
import base64
import argparse
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

# Import LLM API support
from tools.llm_api import query_llm

# Import base configs
from dotenv import load_dotenv
load_dotenv()

def encode_image_to_base64(image_path: str) -> str:
    """
    Encode an image file to base64 string.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded string
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def analyze_luxury_item(
    image_path: str,
    query: Optional[str] = None,
    provider: str = "openai"
) -> Dict[str, Any]:
    """
    Analyze a luxury item image using vision-capable LLMs.
    
    Args:
        image_path: Path to the image file
        query: Optional specific query about the item (defaults to general identification)
        provider: LLM provider to use (openai, anthropic, etc.)
        
    Returns:
        Dictionary containing the analysis results
    """
    if not Path(image_path).exists():
        return {"error": f"Image file not found: {image_path}"}
    
    # Default prompt if no specific query is provided
    if not query:
        query = """
        Please analyze this luxury item image and provide the following information:
        1. Brand identification
        2. Model/collection name (if recognizable)
        3. Key design elements
        4. Materials assessment
        5. Authenticity indicators visible in the image
        6. Condition assessment based on visible aspects
        7. Estimated production era/year
        8. Any notable features or special editions
        
        Format your response as a structured JSON with these fields.
        """
    
    try:
        # Call the vision model with the image
        response = query_llm(
            prompt=query,
            provider=provider,
            image_path=image_path
        )
        
        # Try to parse structured data if it's in JSON format
        try:
            # Look for JSON in the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                result["raw_response"] = response
                return result
            else:
                # Return unstructured response
                return {
                    "raw_response": response,
                    "structured": False
                }
        except json.JSONDecodeError:
            # Return unstructured response if JSON parsing fails
            return {
                "raw_response": response,
                "structured": False
            }
            
    except Exception as e:
        return {"error": str(e)}

def analyze_luxury_item_sync(
    image_path: str,
    query: Optional[str] = None,
    provider: str = "openai"
) -> Dict[str, Any]:
    """
    Synchronous wrapper for analyze_luxury_item.
    """
    return asyncio.run(analyze_luxury_item(image_path, query, provider))

async def compare_luxury_items(
    image_paths: List[str],
    query: Optional[str] = None,
    provider: str = "openai"
) -> Dict[str, Any]:
    """
    Compare multiple luxury item images to detect authenticity or variations.
    
    Args:
        image_paths: List of paths to image files
        query: Optional specific query about the comparison
        provider: LLM provider to use
        
    Returns:
        Dictionary containing the comparison results
    """
    # Verify all images exist
    for path in image_paths:
        if not Path(path).exists():
            return {"error": f"Image file not found: {path}"}
    
    # Default comparison query
    if not query:
        query = f"""
        Please compare these {len(image_paths)} luxury item images and provide:
        1. Whether they appear to be the same model/design
        2. Key differences between the items
        3. Indicators of authenticity or potential counterfeiting
        4. Quality and condition comparison
        5. Estimated value comparison based on visible features
        
        Format your response as a structured JSON with these fields.
        """
    
    # Analyze each image individually first
    individual_analyses = []
    for i, path in enumerate(image_paths):
        analysis = await analyze_luxury_item(path, f"Analyze luxury item in image {i+1}", provider)
        individual_analyses.append(analysis)
    
    try:
        # Use the updated query_llm function with image_paths parameter
        all_images_prompt = f"Compare these {len(image_paths)} luxury items:\n\n" + query
        response = query_llm(
            prompt=all_images_prompt,
            provider=provider,
            image_paths=image_paths
        )
            
        # Try to parse structured data if available
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                result["raw_response"] = response
                result["individual_analyses"] = individual_analyses
                return result
            else:
                # Return unstructured response
                return {
                    "raw_response": response,
                    "structured": False,
                    "individual_analyses": individual_analyses
                }
        except json.JSONDecodeError:
            # Return unstructured response if JSON parsing fails
            return {
                "raw_response": response,
                "structured": False,
                "individual_analyses": individual_analyses
            }
            
    except Exception as e:
        return {"error": str(e), "individual_analyses": individual_analyses}

def compare_luxury_items_sync(
    image_paths: List[str],
    query: Optional[str] = None,
    provider: str = "openai"
) -> Dict[str, Any]:
    """
    Synchronous wrapper for compare_luxury_items.
    """
    return asyncio.run(compare_luxury_items(image_paths, query, provider))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyze luxury item images')
    parser.add_argument('images', nargs='+', help='Paths to image files')
    parser.add_argument('--query', '-q', help='Specific query about the item(s)')
    parser.add_argument('--provider', '-p', default="openai", help='LLM provider (openai, anthropic)')
    parser.add_argument('--compare', '-c', action='store_true', help='Compare multiple images')
    
    args = parser.parse_args()
    
    if args.compare and len(args.images) > 1:
        result = compare_luxury_items_sync(args.images, args.query, args.provider)
    else:
        # Analyze just the first image if compare is not specified
        result = analyze_luxury_item_sync(args.images[0], args.query, args.provider)
    
    # Pretty print the result
    print(json.dumps(result, indent=2)) 