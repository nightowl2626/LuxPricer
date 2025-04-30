"""
Tools for luxury item appraisal using the CrewAI framework.
This file defines various tool functions that can be used by the appraisal agents.
"""

import os
import json
import requests
import mimetypes
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import logging
import time
import uuid

from crewai.tools import tool
from config.logging import get_logger
from config.settings import settings

# Configure logging
logger = get_logger(__name__)

# Import unified pricing logic
from utils.pricing_logic import estimate_price
# Import RAG pricing system
from services.rag.rag_pricing import get_price_estimation_with_rag

# --------------------------------
# Pricing Tool Functions
# --------------------------------

@tool("get_price_estimation")
def get_price_estimation(item_info: Dict[str, Any], trend_score: Optional[float] = None) -> Dict[str, Any]:
    """
    Get price estimation for a luxury item using the RAG (Retrieval-Augmented Generation) system.
    
    Args:
        item_info: Dictionary containing item details like brand, model, etc.
        trend_score: Market trend score (0-1) to adjust pricing
        
    Returns:
        Dictionary with price estimation results
    """
    logger.info(f"Getting RAG-based price estimation for {item_info.get('brand', '')} {item_info.get('model', '')}")
    
    # Generate a unique request ID for tracking
    request_id = str(uuid.uuid4())[:8]
    
    start_time = time.time()
    
    try:
        # Define default condition rating from condition string if provided
        condition_rating = None
        condition_str = item_info.get('condition', '').lower()
        
        # Define vector store path - can be customized
        vector_store_path = settings.RAG_VECTOR_STORE_PATH
        
        # Map condition string to rating if provided
        if condition_str:
            condition_map = {
                'new': 10,
                'mint': 9,
                'excellent': 8,
                'very good': 7,
                'good': 6,
                'fair': 4,
                'poor': 2
            }
            
            # Find best match
            for cond_key, cond_value in condition_map.items():
                if cond_key in condition_str:
                    condition_rating = cond_value
                    break
            
            # Default to middle rating if couldn't map
            if condition_rating is None:
                condition_rating = 5
        
        # Check if we should use RAG system
        use_rag = True
        
        # Output detailed input parameters
        logger.info(f"[{request_id}] RAG price estimation - Input parameters:")
        logger.info(f"  Brand/Designer: {item_info.get('brand', '') or item_info.get('designer', '')}")
        logger.info(f"  Model/Style: {item_info.get('model', '') or item_info.get('style', '')}")
        logger.info(f"  Material: {item_info.get('material', '')}")
        logger.info(f"  Color: {item_info.get('color', '')}")
        logger.info(f"  Size: {item_info.get('size', '')}")
        logger.info(f"  Condition: {condition_str} (Rating: {condition_rating})")
        logger.info(f"  Trend Score: {trend_score}")
        logger.info(f"  Vector Store Path: {vector_store_path}")
        
        if use_rag:
            # RAG is the preferred method - always try to use it first
            logger.info(f"[{request_id}] Using RAG price estimation system from {vector_store_path}")
            
            try:
                logger.info(f"[{request_id}] Calling RAG price estimation function with parameters:")
                logger.info(f"  item_info: {json.dumps(item_info, ensure_ascii=False)}")
                logger.info(f"  trend_score: {trend_score}")
                logger.info(f"  condition_rating: {condition_rating}")
                
                price_result = get_price_estimation_with_rag(
                    item_info=item_info,
                    trend_score=trend_score,
                    condition_rating=condition_rating,
                    vector_store_path=vector_store_path
                )
                
                # Output detailed results
                logger.info(f"[{request_id}] RAG price estimation results:")
                logger.info(f"  Estimated Price: ${price_result.get('estimated_price', 0)}")
                logger.info(f"  Price Range: ${price_result.get('price_range', {}).get('min', 0)} - ${price_result.get('price_range', {}).get('max', 0)}")
                logger.info(f"  Confidence: {price_result.get('confidence', 'unknown')}")
                logger.info(f"  Matched Items Count: {price_result.get('matched_items_count', 0)}")
                logger.info(f"  Price Statistics: {json.dumps(price_result.get('price_stats', {}), ensure_ascii=False)}")
                logger.info(f"  Adjustment Factors: {json.dumps(price_result.get('adjustment_factors', {}), ensure_ascii=False)}")
                
                # Output similar items
                similar_items = price_result.get('similar_items', [])
                logger.info(f"  Similar Items Count: {len(similar_items)}")
                for i, item in enumerate(similar_items):
                    logger.info(f"    [{i+1}] {item.get('designer', '')} {item.get('model', '')} - ${item.get('price', 0)}, Similarity: {item.get('similarity', 0):.4f}")
                
                # Add method info
                price_result['pricing_method'] = 'rag'
                
                # If we have a zero or very low confidence result, fallback to traditional pricing
                if (price_result.get('estimated_price', 0) == 0 or 
                    price_result.get('confidence', '') in ['none', 'error']):
                    logger.warning(f"[{request_id}] RAG system returned low confidence result, falling back to traditional pricing system")
                    use_rag = False
            except Exception as e:
                logger.error(f"[{request_id}] RAG price estimation system error: {str(e)}", exc_info=True)
                use_rag = False
        
        # Fallback to traditional pricing system if RAG is not available or failed
        if not use_rag:
            logger.info(f"[{request_id}] Using traditional pricing system")
            price_result = estimate_price(
                item=item_info,
                trend_score=trend_score if trend_score is not None else 0.5
            )
            # Add method info
            price_result['pricing_method'] = 'fallback'
            
        # Add timing information
        elapsed_time = time.time() - start_time
        price_result['timing'] = {
            'total_seconds': round(elapsed_time, 2),
            'timestamp': datetime.now().isoformat()
        }
        
        # Add request ID
        price_result['request_id'] = request_id
        
        # Log result summary
        price = price_result.get('estimated_price', 0)
        confidence = price_result.get('confidence', 'unknown')
        method = price_result.get('pricing_method')
        logger.info(f"[{request_id}] Price estimation complete: ${price} ({confidence} confidence) using {method} method, time: {elapsed_time:.2f}s")
        
        return price_result
        
    except Exception as e:
        logger.error(f"[{request_id}] Price estimation error: {str(e)}", exc_info=True)
        
        # Return error result
        return {
            'estimated_price': 0,
            'confidence': 'error',
            'message': f"Error in price estimation: {str(e)}",
            'error': str(e),
            'pricing_method': 'error',
            'request_id': request_id,
            'timing': {
                'total_seconds': round(time.time() - start_time, 2),
                'timestamp': datetime.now().isoformat()
            }
        }

@tool("get_price_estimation_with_rag")
def get_price_estimation_rag(
    designer: str,
    model: str,
    size: Optional[str] = None,
    material: Optional[str] = None,
    color: Optional[str] = None,
    condition_rating: Optional[str] = None,
    year: Optional[int] = None,
    trend_score: Optional[float] = None
) -> Dict[str, Any]:
    """
    Get a comprehensive price estimation using RAG (Retrieval-Augmented Generation) for semantic search.
    This tool uses vector embeddings to find the most semantically relevant listings.
    
    Args:
        designer: The designer or brand name
        model: The model or style name
        size: Optional size information
        material: Optional material information
        color: Optional color information  
        condition_rating: Optional condition rating (e.g. 'Excellent', 'Good')
        year: Optional year of production
        trend_score: Optional trend score (0-1) from market analysis
        
    Returns:
        A dictionary with detailed price estimation data
    """
    logger.info(f"Getting RAG-based price estimation for {designer} {model}")
    
    try:
        # Construct item details object
        target_item = {
            "designer": designer,
            "model": model,
            "condition_rating": condition_rating,
            "item_details": {
                "size": size,
                "material": material,
                "color": color
            }
        }
        
        if year is not None:
            target_item["item_details"]["year"] = year
        
        # Call the RAG pricing function
        estimation_result = get_price_estimation_with_rag(
            target_item, 
            trend_score=trend_score
        )
        
        if estimation_result is None or "error" in estimation_result:
            error_msg = estimation_result.get("error", "Unknown estimation error") if estimation_result else "Failed to estimate price with RAG"
            logger.error(f"RAG price estimation error: {error_msg}")
            
            # Fallback to traditional method
            logger.info("Falling back to traditional price estimation method")
            return get_price_estimation(
                item_info=target_item,
                trend_score=trend_score
            )
            
        return estimation_result
        
    except Exception as e:
        logger.error(f"Error in RAG price estimation: {str(e)}")
        # Fallback to traditional method on exception
        logger.info("Falling back to traditional price estimation method due to exception")
        return get_price_estimation(
            item_info=target_item,
            trend_score=trend_score
        )

# --------------------------------
# Trend Analysis Tool Functions
# --------------------------------

@tool("get_perplexity_trends")
def get_perplexity_trends(
    query: str,
    timeframe: int = 180
) -> Dict[str, Any]:
    """
    Analyze trend information using Perplexity AI from the last 6 months for a luxury item.
    
    Args:
        query: The search query (typically brand + model)
        timeframe: Number of days to look back (default: 180)
        
    Returns:
        A dictionary with detailed trend analysis including runway mentions, celebrity sightings,
        review keywords, collectibility notes, and overall trend summary.
    """
    logger.info(f"Getting Perplexity trend analysis for '{query}' over {timeframe} days")
    
    try:
        # Parse brand and model from query
        query_parts = query.split()
        if len(query_parts) >= 2:
            brand = query_parts[0]
            model = " ".join(query_parts[1:])
        else:
            brand = query
            model = ""
        
        # Use our integrated data loader to get or generate trend data
        from utils.data_loader import get_or_generate_trend_data
        
        # Get trend data (will be cached if already exists)
        trend_data = get_or_generate_trend_data(brand, model)
        
        # Enhance the response with more structured information
        # Extract the perplexity data
        perplexity_data = trend_data.get("perplexity_data", {})
        
        # Format the response to be more informative for the agent
        result = {
            "brand": brand,
            "model": model,
            "trend_score": trend_data.get("trend_score", 0.5),
            "trend_category": trend_data.get("trend_category", "Medium"),
            "summary": perplexity_data.get("summary", "No trend summary available"),
            "runway_mentions": perplexity_data.get("runway_mentions", []),
            "celebrity_sightings": perplexity_data.get("celebrity_sightings", []),
            "positive_keywords": perplexity_data.get("positive_keywords", []),
            "negative_keywords": perplexity_data.get("negative_keywords", []),
            "collectibility_notes": perplexity_data.get("collectibility_notes", []),
            "sources": perplexity_data.get("sources", []),
            "trend_factors": perplexity_data.get("trend_factors", []),
            "raw_calculation": trend_data.get("raw_calculation", {}),
            "search_timeframe": f"last {timeframe} days",
        }
        
        # Add a formatted analysis text for easier reading by the agent
        result["formatted_analysis"] = f"""
# Trend Analysis for {brand} {model}

## Overall Trend Status
- **Trend Score**: {result['trend_score']} (Category: {result['trend_category']})
- **Summary**: {result['summary']}

## Trend Indicators
- **Runway Presence**: {len(result['runway_mentions'])} mentions
- **Celebrity Endorsements**: {len(result['celebrity_sightings'])} sightings
- **Market Sentiment**: {len(result['positive_keywords'])} positive vs {len(result['negative_keywords'])} negative keywords
- **Collectibility Notes**: {len(result['collectibility_notes'])} indicators

## Key Factors Affecting Score
{_format_trend_factors(result['trend_factors'])}

## Sources
{_format_sources(result['sources'])}
"""
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting Perplexity trends: {str(e)}")
        return {
            "error": str(e),
            "target_item": query,
            "timeframe": "last 6 months",
            "trend_score": 0.5,
            "trend_category": "Medium (Default, due to error)",
            "runway_mentions": [],
            "celebrity_sightings": [],
            "positive_keywords": [],
            "negative_keywords": [],
            "collectibility_notes": [],
            "summary": f"Error retrieving trend data: {str(e)}",
            "sources": []
        }

# Helper functions for formatting trend data
def _format_trend_factors(factors: List[Dict[str, Any]]) -> str:
    """Format trend factors into a readable bulleted list"""
    if not factors:
        return "No specific trend factors available"
        
    result = ""
    for factor in factors:
        name = factor.get("name", "Unknown factor")
        score = factor.get("score", 0)
        count = factor.get("count", 0)
        result += f"- **{name}**: Score: {score:.2f}, Count: {count}\n"
        
    return result

def _format_sources(sources: List[str]) -> str:
    """Format sources into a readable bulleted list"""
    if not sources:
        return "No sources available"
        
    result = ""
    for i, source in enumerate(sources):
        result += f"- Source {i+1}: {source}\n"
        
    return result

# --------------------------------
# Image Analysis Tool Functions
# --------------------------------

@tool("analyze_luxury_item_image")
def analyze_luxury_item_image(
    image_path: str,
    brand: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze an image of a luxury item for authentication and detail extraction. Provide the path to the image file.
    
    Args:
        image_path: Path to the image file
        brand: Optional brand name to aid analysis
        model: Optional model name to aid analysis
        
    Returns:
        A dictionary with image analysis results: identified brand/model, condition, materials, authenticity indicators.
    """
    logger.info(f"Analyzing luxury item image at {image_path}")
    
    try:
        # Check if the file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
            
        # Check if it's an image file
        mimetype, _ = mimetypes.guess_type(image_path)
        if not mimetype or not mimetype.startswith('image'):
            raise ValueError(f"File is not an image: {image_path}")
        
        # In a real implementation, this would call an image analysis API
        # For now, simulate an API call
        api_url = f"{settings.base_url}/tools/image/analyze"
        
        files = {'image': (os.path.basename(image_path), open(image_path, 'rb'), mimetype)}
        data = {}
        if brand: data['brand'] = brand
        if model: data['model'] = model

        response = requests.post(api_url, files=files, data=data)
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        logger.error(f"Error analyzing luxury item image: {str(e)}")
        return {
            "error": str(e),
            "status": "failed",
            "analysis_results": None
        }

@tool("compare_luxury_item_images")
def compare_luxury_item_images(
    image_path1: str,
    image_path2: str,
    comparison_type: str = "authenticity"
) -> Dict[str, Any]:
    """
    Compare two images of luxury items for authenticity verification or condition assessment. Provide paths to both image files.
    
    Args:
        image_path1: Path to the first image file
        image_path2: Path to the second image file
        comparison_type: Type of comparison ('authenticity' or 'condition', default: 'authenticity')
        
    Returns:
        A dictionary with comparison results: similarity score, list of differences, authenticity/condition assessment.
    """
    logger.info(f"Comparing luxury item images {image_path1} and {image_path2}")
    
    try:
        # Check if the files exist and are images
        files_to_upload = []
        for i, path in enumerate([image_path1, image_path2]):
            if not os.path.exists(path):
                raise FileNotFoundError(f"Image file {i+1} not found: {path}")
            mimetype, _ = mimetypes.guess_type(path)
            if not mimetype or not mimetype.startswith('image'):
                raise ValueError(f"File {i+1} is not an image: {path}")
            files_to_upload.append(('images', (os.path.basename(path), open(path, 'rb'), mimetype)))

        # Simulate API call
        api_url = f"{settings.base_url}/tools/image/compare"
        data = {'comparison_type': comparison_type}

        response = requests.post(api_url, files=files_to_upload, data=data)
        response.raise_for_status()

        return response.json()
        
    except Exception as e:
        logger.error(f"Error comparing luxury item images: {str(e)}")
        return {
            "error": str(e),
            "status": "failed",
            "comparison_results": None
        }

# --------------------------------
# Tool Definitions (Now using decorated functions directly)
# --------------------------------

# Tool Collections now list the decorated functions
PRICING_TOOLS = [get_price_estimation, get_price_estimation_rag]
TREND_TOOLS = [get_perplexity_trends]
IMAGE_TOOLS = [analyze_luxury_item_image, compare_luxury_item_images]
ALL_TOOLS = PRICING_TOOLS + TREND_TOOLS + IMAGE_TOOLS 