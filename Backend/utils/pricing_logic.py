"""
This script estimates the price of a luxury item using a weighted average approach.
It incorporates similarity scoring based on Brand, Model, Size, Material, Color
to handle cases where exact matches are scarce.
Easy approach to start with for when we don't have a lot of data. To experiment with ML later on.

Estimation Logic Summary:
estimated_price = base_price * condition_factor * trend_factor * variance_factor

base_price = weighted average of comparable listings (weighted by reliability * similarity)
condition_factor = target_condition_score / avg_scraped_condition_score (capped)
trend_factor = trend_score (0-1) scaled to a range (e.g., 0.85-1.15)
variance_factor = 1 - (coefficient of variation * penalty_scale) (capped)
"""

import json
import statistics
import math
import os
from typing import List, Dict, Any, Optional, Tuple

DATA_FOLDER = "data"
LISTINGS_FILE = os.path.join(DATA_FOLDER, "mock_listings.json")
TRENDS_FILE = os.path.join(DATA_FOLDER, "mock_trend_scores.json")

# Source reliability: hard coded for now, just to define the C2C vs B2C difference
SOURCE_RELIABILITY = {
    "Fashionphile": 0.95,
    "Vestiaire Collective": 0.75 # Average, could be refined by seller_status
    # Add other sources later, or some kind of dynamic lookup
}
DEFAULT_RELIABILITY = 0.6 # For sources not explicitly listed

# Condition Score Mapping (String rating to numerical score, 1=Fair, 5=New)
# Ensure keys match the *exact* lowercase output strings from your parse_input_llm
CONDITION_RATING_TO_SCORE = {
    "new": 5, "excellent": 4, "very good": 3, "good": 2, "fair": 1, "unknown": 2
}
DEFAULT_CONDITION_SCORE = 2 # Default if rating is unmappable or "unknown"

# Trend Factor Parameters: how does trend affect price? Tunable.
TREND_MIN_FACTOR = 0.85 # Corresponds to trend_score = 0 (-15% effect)
TREND_MAX_FACTOR = 1.15 # Corresponds to trend_score = 1 (+15% effect)
DEFAULT_TREND_SCORE = 0.5 # Used if no specific trend score is found

# Variance Factor Parameters: how much to penalise for variance in prices? Tunable.
VARIANCE_PENALTY_SCALE = 0.1
VARIANCE_MAX_CV = 0.75 # Cap the max coefficient of variation (avoids extreme penalties)

# Condition Factor Parameters: how much to reward/penalize for condition. Tunable.
MIN_CONDITION_FACTOR = 0.7 # Never reduce price below 70% of average, no matter how bad condition is
MAX_CONDITION_FACTOR = 1.3 # Never increase price above 130% of average, no matter how good condition is

# Similarity Match Parameters: Configurable weighting of features for matching
EXACT_MATCH_SIMILARITY_SCORE = 0.8  # Min score to count as an "exact match"
MIN_SIMILARITY_THRESHOLD = 0.15 # Min score to include in weighted avg
MIN_COMPARABLE_LISTINGS = 5 # Minimum number of listings needed for a valid estimate

# Feature weights for similarity - must sum to 1.0
SIMILARITY_WEIGHTS = {
    # Core identifier features (65% total)
    "designer": 0.35,
    "model": 0.30,
    # Secondary features (35% total)
    "size": 0.15,
    "material": 0.10,
    "color": 0.10
}

# == Helper Functions ==

def load_json_data(filepath: str) -> Optional[List[Dict[str, Any]]]:
    """Loads data from a JSON file."""
    # Check relative path first
    if not os.path.exists(filepath):
        print(f"Error: File not found at {filepath}")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alt_filepath = os.path.join(script_dir, filepath)
        if not os.path.exists(alt_filepath):
             print(f"Error: Also not found at {alt_filepath}")
             return None
        print(f"Using alternative path: {alt_filepath}")
        filepath = alt_filepath
    try:
        with open(filepath, 'r', encoding='utf-8') as f: data = json.load(f)
        if not isinstance(data, list):
            print(f"Error: Data in {filepath} is not a list.")
            return None
        return data
    except Exception as e: print(f"Error loading {filepath}: {e}"); return None

def calculate_similarity_score(item_a: Dict[str, Any], item_b: Dict[str, Any]) -> float:
    """
    Calculate weighted semantic similarity between two item dictionaries.
    Returns a score between 0-1 where 1 is perfect match.
    
    Both inputs should have fields standardized already (lowercase, etc.)
    """
    # Unpack fields to make code more readable
    weights = SIMILARITY_WEIGHTS
    total_score = 0.0
    
    # Get brand - this is required so give a 0 if no match
    designer_a = str(item_a.get("designer", "")).lower()
    designer_b = str(item_b.get("designer", "")).lower()
    if not designer_a or not designer_b:
        return 0.0  # One or both items missing designer; can't match
    
    if (designer_a == designer_b) or (designer_a.strip() == designer_b.strip()):
        total_score += weights["designer"]
    else:
        return 0.0  # Designer (brand) is the hard filter
    
    # Get model name - require minimum of 50% similarity on words
    # This is a bit crude but works reasonably well in practice
    model_a = str(item_a.get("model", "")).lower()
    model_b = str(item_b.get("model", "")).lower()
    
    if not model_a or not model_b:
        model_score = 0.0
    else:
        # Split into words and check overlap
        words_a = set(model_a.split())
        words_b = set(model_b.split())
        
        if len(words_a) == 0 or len(words_b) == 0:
            model_score = 0.0
        else:
            # Calculate Jaccard similarity with bonus for exact match
            intersection = len(words_a.intersection(words_b))
            union = len(words_a.union(words_b))
            
            if union > 0:
                if model_a.strip() == model_b.strip():
                    model_score = 1.0  # Exact match
                else:
                    # Bonus for similar word counts (prevents long vs. short description mismatch)
                    length_ratio = min(len(words_a), len(words_b)) / max(len(words_a), len(words_b))
                    model_score = (intersection / union) * (0.5 + 0.5 * length_ratio)
            else:
                model_score = 0.0
    
    total_score += weights["model"] * model_score
    
    # Size similarity - binary match since size is often a string or list
    size_a = item_a.get("size")
    size_b = item_b.get("size")
    
    if (size_a is None or size_a == "") and (size_b is None or size_b == ""):
        size_score = 0.5  # Both missing size info, neutral
    elif size_a is None or size_b is None or size_a == "" or size_b == "":
        size_score = 0.0  # One is missing size, one has it - no match
    else:
        # Convert to lists if not already
        if not isinstance(size_a, list): size_a = [str(size_a)]
        if not isinstance(size_b, list): size_b = [str(size_b)]
        
        # Check for any overlap in size values
        size_match = any(str(s_a).lower() == str(s_b).lower() for s_a in size_a for s_b in size_b)
        size_score = 1.0 if size_match else 0.0
    
    total_score += weights["size"] * size_score
    
    # Material similarity - simple contains check
    material_a = str(item_a.get("material", "")).lower()
    material_b = str(item_b.get("material", "")).lower()
    
    if not material_a or not material_b:
        material_score = 0.5 # Neutral for missing info
    else:
        material_score = (material_a in material_b or material_b in material_a) and min(len(material_a), len(material_b)) > 3
    
    total_score += weights["material"] * (1.0 if material_score else 0.0)
    
    # Color similarity - simple contains check
    color_a = str(item_a.get("color", "")).lower()
    color_b = str(item_b.get("color", "")).lower()
    
    if not color_a or not color_b:
        color_score = 0.5 # Neutral for missing info
    else:
        # Check if colors overlap
        color_match = (color_a in color_b or color_b in color_a) and min(len(color_a), len(color_b)) > 2
        color_score = 1.0 if color_match else 0.0
    
    total_score += weights["color"] * color_score
    
    return total_score


# Trend score lookup function
def get_trend_score(
    trend_data: List[Dict[str, Any]],
    target_item: Dict[str, Any]
) -> float:
    """
    Looks up the trend score for a target item. First checks the structured trend data.
    If not found, it attempts to generate real-time trend data.
    
    Args:
        trend_data: List of trend data entries from file
        target_item: The item to get a trend score for
        
    Returns:
        A float trend score between 0 and 1
    """
    target_designer = target_item.get("designer")
    target_model = target_item.get("model")

    if not target_designer or not target_model:
        print("Warning: Cannot look up trend score without target designer and model.")
        return DEFAULT_TREND_SCORE

    # First try to find in provided trend data
    for entry in trend_data:
        if not isinstance(entry, dict): continue
        if (str(entry.get("designer", "")).lower() == str(target_designer).lower() and
            str(entry.get("model", "")).lower() == str(target_model).lower()):
            score = entry.get("trend_score")
            if isinstance(score, (int, float)): 
                print(f"Found trend score in data: {score}")
                return float(score)
    
    # If not found in the data, try to generate real-time trend data
    try:
        from utils.data_loader import get_or_generate_trend_data
        
        print(f"No trend data found for {target_designer} {target_model}, generating real-time data...")
        real_trend_data = get_or_generate_trend_data(target_designer, target_model)
        
        if real_trend_data and "trend_score" in real_trend_data:
            trend_score = real_trend_data.get("trend_score")
            print(f"Generated real-time trend score: {trend_score}")
            return float(trend_score)
        
        print(f"Could not generate trend data, using default score")
        return DEFAULT_TREND_SCORE
    
    except Exception as e:
        print(f"Error generating real-time trend data: {e}")
        return DEFAULT_TREND_SCORE

# == Main Price Estimation Function ==

def estimate_price(
    target_item_input: Dict[str, Any],
    all_listings: List[Dict[str, Any]],
    trend_data: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Estimates the price using weighted average, incorporating similarity scores.
    """
    print("-" * 30)
    target_designer = target_item_input.get('designer')
    target_model = target_item_input.get('model')
    target_condition_rating_str = str(target_item_input.get("condition_rating", "unknown")).lower().strip()
    print(f"Estimating price for: {target_designer} {target_model} ({target_condition_rating_str})")

    # === Input Validation ===
    if not target_designer or not target_model: return {"error": "Target item details missing designer or model."}
    if not isinstance(all_listings, list): return {"error": f"Invalid input type for all_listings: Expected list, got {type(all_listings)}"}
    if not isinstance(trend_data, list): trend_data = [] # Use empty list to force default score lookup

    # === 1. Get Target Item Condition Score ===
    target_condition_score = CONDITION_RATING_TO_SCORE.get(target_condition_rating_str, DEFAULT_CONDITION_SCORE)
    print(f"Target Condition: '{target_condition_rating_str}' -> Score: {target_condition_score}")

    # === 2. Filter Listings by Brand & Calculate Similarity ===
    comparable_items_data = []
    target_details_for_sim = target_item_input.get("item_details", {})
    if not isinstance(target_details_for_sim, dict): target_details_for_sim = {}
    target_details_for_sim["designer"] = target_designer
    target_details_for_sim["model"] = target_model
    target_details_for_sim.setdefault("size", None); target_details_for_sim.setdefault("material", None); target_details_for_sim.setdefault("color", None)

    similarity_scores_collected = []
    exact_match_prices = []

    for listing in all_listings:
        if not isinstance(listing, dict): continue
        details = listing.get("item_details", {})
        if not isinstance(details, dict): details = {}
        listing_designer = details.get("designer", listing.get("designer"))
        if listing_designer != target_designer: continue

        price = listing.get("listing_price")
        condition_score_listing = listing.get("condition_rating")
        source = listing.get("source_platform")
        reliability = SOURCE_RELIABILITY.get(source, DEFAULT_RELIABILITY)

        try:
            if price is not None and condition_score_listing is not None:
                details["designer"] = listing_designer
                details["model"] = details.get("model", listing.get("model", listing.get("listing_name")))
                details.setdefault("size", None); details.setdefault("material", None); details.setdefault("color", None)

                similarity = calculate_similarity_score(details, target_details_for_sim)
                similarity_scores_collected.append(similarity)

                if similarity >= MIN_SIMILARITY_THRESHOLD:
                    current_price = float(price) # Convert price once
                    comparable_items_data.append({
                        "price": current_price,
                        "condition_score": int(condition_score_listing),
                        "reliability": float(reliability),
                        "similarity": float(similarity)
                    })
                    if similarity >= EXACT_MATCH_SIMILARITY_SCORE - 1e-6:
                         exact_match_prices.append(current_price)

        except (ValueError, TypeError) as e:
             print(f"Warning: Skipping listing {listing.get('listing_id', 'N/A')} due to data type error: {e}")

    print(f"Considered {len(similarity_scores_collected)} listings from brand '{target_designer}'. Kept {len(comparable_items_data)} listings with similarity >= {MIN_SIMILARITY_THRESHOLD}.")
    print(f"Found {len(exact_match_prices)} exact match listings.")

    if len(comparable_items_data) < MIN_COMPARABLE_LISTINGS:
        msg = f"Insufficient comparable listings found ({len(comparable_items_data)} found, need {MIN_COMPARABLE_LISTINGS}). Cannot estimate price."
        print(f"Error: {msg}")
        min_sim = min(similarity_scores_collected) if similarity_scores_collected else None
        max_sim = max(similarity_scores_collected) if similarity_scores_collected else None
        return {"error": msg, "listings_considered": len(similarity_scores_collected), "min_similarity_found": min_sim, "max_similarity_found": max_sim}

    # === 3. Calculate Weighted Base Price & Avg Condition ===
    total_combined_weight = 0.0; weighted_price_sum = 0.0; weighted_condition_sum = 0.0
    prices_for_variance = []; min_sim_used = 1.0; max_sim_used = 0.0
    for item in comparable_items_data:
        combined_weight = item["reliability"] * item["similarity"]
        if combined_weight > 1e-6:
             total_combined_weight += combined_weight
             weighted_price_sum += item["price"] * combined_weight
             weighted_condition_sum += item["condition_score"] * combined_weight
             prices_for_variance.append(item["price"])
             min_sim_used = min(min_sim_used, item["similarity"])
             max_sim_used = max(max_sim_used, item["similarity"])
    if total_combined_weight < 1e-6: return {"error": "Total combined weight is zero."}
    base_price = weighted_price_sum / total_combined_weight
    avg_scraped_condition_score = weighted_condition_sum / total_combined_weight

    # === 4. Calculate Condition Factor ===
    if avg_scraped_condition_score < 1e-6: condition_factor = 1.0
    else:
        condition_factor = target_condition_score / avg_scraped_condition_score
        condition_factor = max(MIN_CONDITION_FACTOR, min(MAX_CONDITION_FACTOR, condition_factor))

    # === 5. Get Trend Score & Calculate Trend Factor ===
    trend_score = get_trend_score(trend_data, target_item_input)
    trend_factor_range = TREND_MAX_FACTOR - TREND_MIN_FACTOR
    trend_factor = TREND_MIN_FACTOR + (trend_score * trend_factor_range)

    # === 6. Calculate Variance Factor ===
    variance_factor = 1.0; price_std_dev = None; coeff_variation = None
    if len(prices_for_variance) >= 2:
        try:
            price_std_dev = statistics.stdev(prices_for_variance)
            if base_price > 1e-6:
                coeff_variation = price_std_dev / base_price
                variance_penalty = min(coeff_variation, VARIANCE_MAX_CV) * VARIANCE_PENALTY_SCALE
                variance_factor = 1.0 - variance_penalty
        except statistics.StatisticsError as e: print(f"Warning: Could not calculate stdev: {e}")

    # === 7. Calculate Final Price ===
    estimated_price = base_price * condition_factor * trend_factor * variance_factor

    min_exact_match_price = min(exact_match_prices) if exact_match_prices else None
    max_exact_match_price = max(exact_match_prices) if exact_match_prices else None

    print("-" * 30)
    return {
        "estimated_price": round(estimated_price, 2),
        "base_price_weighted_avg": round(base_price, 2),
        "comparable_listings_used": len(comparable_items_data),
        "exact_match_count": len(exact_match_prices),
        "min_exact_match_price": round(min_exact_match_price, 2) if min_exact_match_price is not None else None,
        "max_exact_match_price": round(max_exact_match_price, 2) if max_exact_match_price is not None else None,
        "min_similarity_used": round(min_sim_used, 2) if comparable_items_data else None,
        "max_similarity_used": round(max_sim_used, 2) if comparable_items_data else None,
        "avg_scraped_condition_score": round(avg_scraped_condition_score, 2),
        "target_condition_score": target_condition_score,
        "condition_factor": round(condition_factor, 3),
        "trend_score_used": round(trend_score, 3),
        "trend_factor": round(trend_factor, 3),
        "price_std_dev": round(price_std_dev, 2) if price_std_dev is not None else None,
        "coeff_variation": round(coeff_variation, 3) if coeff_variation is not None else None,
        "variance_factor": round(variance_factor, 3),
        "target_item_summary": f"{target_designer} {target_model} ({target_condition_rating_str})"
    }

# Alias the unified estimate_price function to match existing API
estimate_price_basic = estimate_price
estimate_price_advanced = estimate_price

# === Example ===
if __name__ == "__main__":
    print("Starting Price Estimator (with V3 Similarity + Min/Max Exact)...")
    listings_data = load_json_data(LISTINGS_FILE)
    trends_data = load_json_data(TRENDS_FILE)
    if listings_data is None or trends_data is None:
        print("Could not load necessary data files. Exiting.")
    else:
        # Example target item
        TARGET_ITEM_FOR_TESTING = {
          "designer": "Gucci",
          "model": "Horsebit 1955",
          "condition_rating": "Excellent", # User-provided condition category
          "item_details": {                 # Details extracted from prompt
            "size": "35",
            "material": "Exotic Skin",
            "color": "Blue"
          }
          # "inclusions": ["Dust Bag", "Authenticity Card"] # Optional field
        }
        
        # Derive condition score for the test item
        TARGET_ITEM_FOR_TESTING["condition_score"] = CONDITION_RATING_TO_SCORE.get(
            str(TARGET_ITEM_FOR_TESTING.get("condition_rating", "unknown")).lower().strip(),
            DEFAULT_CONDITION_SCORE
        )
        estimation_result = estimate_price(TARGET_ITEM_FOR_TESTING, listings_data, trends_data)
        if estimation_result and "error" not in estimation_result:
            print("\n=== Estimation Result ===")
            print(json.dumps(estimation_result, indent=2))
            print("---------------")
        elif estimation_result and "error" in estimation_result:
             print(f"\nPrice estimation failed: {estimation_result['error']}")
        else:
            print("\nPrice estimation failed (unknown error).") 