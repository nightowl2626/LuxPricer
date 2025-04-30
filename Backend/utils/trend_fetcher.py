"""
Utility functions for fetching and calculating trend data.
This module integrates functionality from fetch_trend.py and trend_calculator.py
to provide real-time trend data for luxury items.
"""

import os
import json
import logging
import re
import math
import time
from typing import Dict, Any, List, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Cache expiration time in seconds (default: 24 hours)
CACHE_EXPIRATION = 24 * 60 * 60

def fetch_trend_data(
    brand: str, 
    model: str, 
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Fetch trend data from Perplexity API for a given brand and model.
    
    Args:
        brand: The brand name (e.g., "Louis", "Chanel")
        model: The model name (e.g., "Pochette", "Flap Bag")
        force_refresh: Whether to force a refresh of cached data
        
    Returns:
        A dictionary containing trend data
    """
    query = f"{brand} {model}".strip()
    
    # Check if we have cached data
    cache_file = os.path.join("data", "cache", "trends", f"{brand}_{model}.json".replace(" ", "_").lower())
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    
    if os.path.exists(cache_file) and not force_refresh:
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            
            # Check if cache is still valid
            cache_time = cached_data.get("cache_timestamp", 0)
            if time.time() - cache_time < CACHE_EXPIRATION:
                logger.info(f"Using cached trend data for {query}")
                return cached_data
        except Exception as e:
            logger.warning(f"Error reading cached trend data: {e}")
    
    # No valid cache, fetch new data
    logger.info(f"Fetching new trend data for {query}")
    trend_data = _fetch_from_perplexity(brand, model)
    
    # Calculate trend score using the improved method from trend_calculator
    trend_result = calculate_trend_score_from_perplexity(trend_data)
    
    # Combine the results
    trend_data.update({
        "trend_score": trend_result.get("trend_score", 0.5),
        "trend_category": trend_result.get("trend_category", "Medium"),
        "raw_score": trend_result.get("raw_score", 0),
        "calculation_inputs": trend_result.get("calculation_inputs", {}),
        "trend_factors": trend_result.get("trend_factors", [])
    })
    
    # Add cache timestamp
    trend_data["cache_timestamp"] = time.time()
    
    # Save to cache
    try:
        with open(cache_file, 'w') as f:
            json.dump(trend_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving trend data to cache: {e}")
    
    return trend_data

def _fetch_from_perplexity(brand: str, model: str) -> Dict[str, Any]:
    """
    Fetch trend data from Perplexity API.
    
    Args:
        brand: The brand name
        model: The model name
        
    Returns:
        A dictionary containing trend data
    """
    query = f"{brand} {model}".strip()
    
    # Set up OpenAI client with Perplexity API
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable not set")
        
    client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
    
    # Construct the prompt
    prompt_content = f"""
    Please analyze information available online from the **last 6 months** regarding the **{brand} {model}** handbag.

    Based *only* on the information retrieved from your search:
    1. Identify mentions of the bag appearing in recent fashion shows or runway contexts.
    2. List any high-profile celebrities or influencers recently seen carrying the bag.
    3. Extract frequently mentioned positive keywords/phrases from recent user reviews or discussions about the bag.
    4. Extract frequently mentioned negative keywords/phrases from recent user reviews or discussions about the bag.
    5. Find any notes or mentions related to its collectibility, investment value, rarity, or discontinuation status.
    6. Provide a brief overall summary of the bag's current trend status based *only* on the findings above.
    7. List up to 3 key source URLs supporting these findings.

    Present your findings **ONLY** as a single, valid JSON object with the following keys. If no information is found for a specific list, use an empty list `[]`. If no information is found for the summary string, use `null` or a short "N/A" string.

    {{
      "target_item": "{query}",
      "timeframe": "last 6 months",
      "recent_runway_mentions": [
        "string description of mention 1",
        "string description of mention 2"
      ],
      "recent_celebrity_sightings": [
        "Celebrity Name 1 (Event/Context)",
        "Celebrity Name 2"
      ],
      "recent_review_keywords_positive": [
        "keyword1", "keyword2"
      ],
      "recent_review_keywords_negative": [
        "keyword1", "keyword2"
      ],
      "collectibility_notes": [
        "Snippet about investment value...",
        "Mention of limited edition..."
      ],
      "overall_trend_summary": "Brief text summary based ONLY on the findings above.",
      "key_sources": [
        "url1", "url2", "url3"
      ]
    }}
    """
    
    # Set up the messages
    messages = [
        {
            "role": "system",
            "content": (
                "You are an AI assistant specialized in analyzing recent fashion trends "
                "for luxury items based on web search results. Your goal is to extract "
                "specific indicators of trendiness and collectibility into a structured JSON format."
            ),
        },
        {
            "role": "user",
            "content": prompt_content,
        },
    ]
    
    # Make the API call
    response = client.chat.completions.create(
        model="sonar-pro",
        messages=messages,
    )
    
    # Extract the content
    content = response.choices[0].message.content
    
    # Parse JSON response
    try:
        # Handle case where response might be wrapped in markdown code block
        cleaned_content = content
        if content.strip().startswith("```") and "```" in content:
            # Extract content between first '{' and last '}'
            start_marker = content.find("{")
            end_marker = content.rfind("}")
            if start_marker != -1 and end_marker != -1:
                cleaned_content = content[start_marker:end_marker+1]
                
        trend_data = json.loads(cleaned_content)
        logger.info(f"Successfully fetched trend data from Perplexity for {query}")
        return trend_data
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing Perplexity response: {e}")
        logger.info(f"Raw content: {content}")
        raise ValueError(f"Failed to parse Perplexity response as JSON: {e}")

def calculate_trend_score_from_perplexity(perplexity_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculates a trend score (0-1) and category based on structured output
    from Perplexity AI, using a weighted feature sum and sigmoid normalization.
    This implements the algorithm from trend_calculator.py.

    Args:
        perplexity_output: A dictionary parsed from the Perplexity JSON output.

    Returns:
        A dictionary containing the calculated trend_score, trend_category,
        raw_score, and extracted feature counts/flags.
    """
    # === 1. Extract Quantifiable Features ===
    runway_mentions = perplexity_output.get('recent_runway_mentions', [])
    celebrity_sightings = perplexity_output.get('recent_celebrity_sightings', [])
    positive_keywords = perplexity_output.get('recent_review_keywords_positive', [])
    negative_keywords = perplexity_output.get('recent_review_keywords_negative', [])
    collectibility_notes = perplexity_output.get('collectibility_notes', [])

    num_runway = len(runway_mentions) if isinstance(runway_mentions, list) else 0
    num_celebs = len(celebrity_sightings) if isinstance(celebrity_sightings, list) else 0
    num_pos_keywords = len(positive_keywords) if isinstance(positive_keywords, list) else 0
    num_neg_keywords = len(negative_keywords) if isinstance(negative_keywords, list) else 0
    num_collect_notes = len(collectibility_notes) if isinstance(collectibility_notes, list) else 0

    # Check for specific keywords in collectibility notes
    collect_text = " ".join(collectibility_notes).lower() if isinstance(collectibility_notes, list) else ""
    has_investment_mention = 1 if re.search(r'\b(investment|value increase)\b', collect_text) else 0
    has_rarity_mention = 1 if re.search(r'\b(rare|rarity|limited|discontinued)\b', collect_text) else 0

    extracted_features = {
        "num_runway": num_runway,
        "num_celebs": num_celebs,
        "num_pos_keywords": num_pos_keywords,
        "num_neg_keywords": num_neg_keywords,
        "num_collect_notes": num_collect_notes,
        "has_investment_mention": has_investment_mention,
        "has_rarity_mention": has_rarity_mention,
    }
    logger.info(f"Extracted trend features: {extracted_features}")

    # === 2. Assign Weights (Tunable Parameters) ===
    weights = {
        "w_runway": 0.10,
        "w_celeb": 0.20,
        "w_pos_kw": 0.05,
        "w_neg_kw": -0.03,
        "w_collect": 0.15,
        "w_invest": 0.20,
        "w_rare": 0.15,
        "base_offset": 0.0
    }

    # === 3. Calculate Raw Score ===
    raw_score = weights["base_offset"] + \
                (weights["w_runway"] * num_runway) + \
                (weights["w_celeb"] * num_celebs) + \
                (weights["w_pos_kw"] * num_pos_keywords) + \
                (weights["w_neg_kw"] * num_neg_keywords) + \
                (weights["w_collect"] * num_collect_notes) + \
                (weights["w_invest"] * has_investment_mention) + \
                (weights["w_rare"] * has_rarity_mention)

    logger.info(f"Calculated raw trend score: {raw_score:.4f}")

    # === 4. Normalize Score to 0-1 Range (using Sigmoid) ===
    sigmoid_k = 1.0
    sigmoid_center = 0.5

    try:
        scaled_score = sigmoid_k * (raw_score - sigmoid_center)
        trend_score = 1 / (1 + math.exp(-scaled_score))
    except OverflowError:
        trend_score = 1.0 if scaled_score > 0 else 0.0

    logger.info(f"Normalized trend score (0-1): {trend_score:.4f}")

    # === 5. Determine Category ===
    if trend_score >= 0.85:
        trend_category = "Very High"
    elif trend_score >= 0.65:
        trend_category = "High"
    elif trend_score >= 0.45:
        trend_category = "Medium"
    elif trend_score >= 0.25:
        trend_category = "Low"
    else:
        trend_category = "Very Low / Declining"

    # Prepare trend factors for detailed reporting
    trend_factors = [
        {
            "name": "Runway Presence",
            "score": weights["w_runway"] * num_runway,
            "count": num_runway,
            "weight": weights["w_runway"]
        },
        {
            "name": "Celebrity Endorsement", 
            "score": weights["w_celeb"] * num_celebs,
            "count": num_celebs,
            "weight": weights["w_celeb"]
        },
        {
            "name": "Positive Reviews",
            "score": weights["w_pos_kw"] * num_pos_keywords,
            "count": num_pos_keywords,
            "weight": weights["w_pos_kw"]
        },
        {
            "name": "Negative Reviews",
            "score": weights["w_neg_kw"] * num_neg_keywords,
            "count": num_neg_keywords,
            "weight": weights["w_neg_kw"]
        },
        {
            "name": "Collectibility Notes",
            "score": weights["w_collect"] * num_collect_notes,
            "count": num_collect_notes,
            "weight": weights["w_collect"]
        },
        {
            "name": "Investment Value",
            "score": weights["w_invest"] * has_investment_mention,
            "count": has_investment_mention,
            "weight": weights["w_invest"]
        },
        {
            "name": "Rarity Mentions",
            "score": weights["w_rare"] * has_rarity_mention,
            "count": has_rarity_mention,
            "weight": weights["w_rare"]
        }
    ]

    # === Results ===
    return {
        "trend_score": round(trend_score, 3),
        "trend_category": trend_category,
        "raw_score": round(raw_score, 3),
        "calculation_inputs": extracted_features,
        "perplexity_summary": perplexity_output.get("overall_trend_summary", "N/A"),
        "trend_factors": trend_factors
    }

# Legacy function maintained for backwards compatibility
def calculate_trend_score(trend_data: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Calculate a trend score based on trend data.
    Now uses the more advanced calculate_trend_score_from_perplexity under the hood.
    
    Args:
        trend_data: Dictionary of trend data
        
    Returns:
        A tuple containing the trend score (0-100) and a list of factors that influenced the score
    """
    # Call the new function and adapt the results to match the old return format
    result = calculate_trend_score_from_perplexity(trend_data)
    score = result["trend_score"] * 100  # Convert 0-1 to 0-100
    factors = result["trend_factors"]
    
    return score, factors

def get_real_trend_data(designer: str, model: str) -> Dict[str, Any]:
    """
    Main function to get real trend data and calculate a trend score.
    
    Args:
        designer: The luxury brand/designer name
        model: The model/style name
        
    Returns:
        A dictionary with trend data and calculated score
    """
    logger.info(f"Getting real trend data for {designer} {model}")
    
    # Fetch raw trend data from Perplexity
    trend_data = fetch_trend_data(designer, model)
    
    # Check if there was an error
    if "error" in trend_data:
        logger.error(f"Error fetching trend data: {trend_data['error']}")
        # Return a default trend score with error info
        return {
            "designer": designer,
            "model": model,
            "trend_score": 0.5,  # Default score
            "trend_category": "Medium (Default)",
            "error": trend_data.get("error", "Unknown error"),
            "perplexity_summary": trend_data.get("overall_trend_summary", "Error retrieving trend data")
        }
    
    # Ensure we have a trend score (should have been calculated in fetch_trend_data)
    if "trend_score" not in trend_data:
        # Calculate it if somehow missing
        result = calculate_trend_score_from_perplexity(trend_data)
        trend_score = result["trend_score"]
        trend_category = result["trend_category"]
        trend_factors = result["trend_factors"]
    else:
        trend_score = trend_data["trend_score"]
        trend_category = trend_data.get("trend_category", "Medium")
        trend_factors = trend_data.get("trend_factors", [])
    
    # Combine relevant data into a single result
    result = {
        "designer": designer,
        "model": model,
        "trend_score": trend_score,
        "trend_category": trend_category,
        "perplexity_data": {
            "runway_mentions": trend_data.get("recent_runway_mentions", []),
            "celebrity_sightings": trend_data.get("recent_celebrity_sightings", []),
            "positive_keywords": trend_data.get("recent_review_keywords_positive", []),
            "negative_keywords": trend_data.get("recent_review_keywords_negative", []),
            "collectibility_notes": trend_data.get("collectibility_notes", []),
            "summary": trend_data.get("overall_trend_summary", "N/A"),
            "sources": trend_data.get("key_sources", []),
            "trend_factors": trend_factors
        },
        "raw_calculation": {
            "raw_score": trend_data.get("raw_score", 0),
            "calculation_inputs": trend_data.get("calculation_inputs", {})
        }
    }
    
    return result 