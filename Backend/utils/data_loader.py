"""
Utility functions for loading data required by pricing tools.
"""
import json
import os
from typing import List, Dict, Any, Optional

DATA_FOLDER = "data"
LISTINGS_FILE = os.path.join(DATA_FOLDER, "mock_listings.json")
REAL_LISTINGS_FILE = os.path.join(DATA_FOLDER, "product_scraped.json")
CLEANED_LISTINGS_FILE = os.path.join(DATA_FOLDER, "cleaned_listings.json")
# CLEANED_LISTINGS_FILE = os.path.join(DATA_FOLDER, "transformed_data_gemini_single_final.json")
#CLEANED_LISTINGS_FILE = os.path.join(DATA_FOLDER, "transformed_data_v2_2.json")
TRENDS_FILE = os.path.join(DATA_FOLDER, "mock_trend_scores.json")
REAL_TRENDS_FILE = os.path.join(DATA_FOLDER, "real_trend_scores.json")

def load_json_data(filepath: str) -> Optional[List[Dict[str, Any]]]:
    """Loads data from a JSON file."""
    # Ensure the data folder exists
    if not os.path.exists(DATA_FOLDER):
        print(f"Error: Data folder '{DATA_FOLDER}' not found.")
        try:
            os.makedirs(DATA_FOLDER)
            print(f"Created data folder: {DATA_FOLDER}")
        except OSError as e:
            print(f"Error creating data folder: {e}")
            return None # Cannot proceed if folder cannot be created
        # If folder was just created, file won't exist yet
        return None

    if not os.path.exists(filepath):
        print(f"Warning: File not found at {filepath}")
        return None # Return None if a specific file doesn't exist, allows caller to handle
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Basic validation: check if it's a list (as expected for our mock data)
        if not isinstance(data, list):
            print(f"Error: Expected a list of objects in {filepath}, but got {type(data).__name__}.")
            return None
        return data
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from {filepath}: {e}")
        return None
    except IOError as e:
        print(f"Error reading file {filepath}: {e}")
        return None

def transform_product_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transform data from product_scraped.json format to the format expected by the pricing logic.
    """
    transformed = []
    print(f"Transforming {len(data)} items from product_scraped.json")
    
    # Create a dictionary to count items by brand
    brand_counts = {}
    
    for idx, item in enumerate(data):
        try:
            # Extract listing price and convert to float
            listing_price_str = item.get('listing_price', '')
            if isinstance(listing_price_str, str) and listing_price_str.startswith('$'):
                try:
                    # Remove currency symbol and commas, then convert to float
                    price_value = float(listing_price_str.replace('$', '').replace(',', ''))
                except ValueError:
                    print(f"Warning: Could not parse price: {listing_price_str}")
                    continue  # Skip items with unparseable prices
            else:
                # Skip items without a valid price
                continue
            
            # Map condition rating
            condition_str = item.get('condition_rating', '').lower() if item.get('condition_rating') else ""
            condition_map = {
                'new': 5, 
                'excellent': 4, 
                'very good': 3, 
                'good': 2, 
                'fair': 1,
                'shows wear': 3  # Map "shows wear" to "very good"
            }
            condition_rating = condition_map.get(condition_str, 2)  # Default to 2 if not recognized
            
            # Get item details
            item_details = item.get('item_details', {})
            if not isinstance(item_details, dict):
                item_details = {}
                
            # Extract designer/brand - use more sources for brand info
            designer = ''
            
            # Try to get from item_details first
            if isinstance(item_details, dict) and item_details.get('designer'):
                designer = item_details.get('designer', '').strip()
            
            # If not found, try from listing_name
            if not designer and item.get('listing_name'):
                listing_name = item.get('listing_name', '')
                first_word = listing_name.split(' ')[0].strip()
                if first_word:
                    designer = first_word
            
            # If still not found, look in item_description
            if not designer and isinstance(item_details, dict) and item_details.get('item_description'):
                description = item_details.get('item_description', '')
                # Look for common pattern "This is an authentic BRAND"
                if isinstance(description, str) and 'authentic' in description.lower():
                    parts = description.split('authentic', 1)
                    if len(parts) > 1 and parts[1]:
                        brand_part = parts[1].strip().split(' ')[0]
                        if brand_part:
                            designer = brand_part
            
            # Normalize brand names
            if isinstance(designer, str):
                designer = designer.replace('BURBERRY', 'Burberry')
            
            # Extract model - use multiple sources
            model = ''
            
            # Try direct model field
            if isinstance(item_details, dict) and item_details.get('model'):
                model = str(item_details.get('model', '')).strip()
            
            # If not found, use listing name without brand
            if not model and item.get('listing_name'):
                listing_name = item.get('listing_name', '')
                if designer and isinstance(listing_name, str) and listing_name.startswith(designer):
                    model = listing_name[len(designer):].strip()
                else:
                    model = listing_name
                    
            # If model is still empty, use a part of the description
            if not model and isinstance(item_details, dict) and item_details.get('item_description'):
                desc = item_details.get('item_description', '')
                if isinstance(desc, str) and len(desc) > 10:
                    # Use first 50 chars if long
                    model = desc[:50] + '...' if len(desc) > 50 else desc
            
            # For Burberry specific search
            if isinstance(designer, str) and designer.lower() == 'burberry' and isinstance(model, str) and 'belt bag' in model.lower():
                model = 'Belt Bag'
                print(f"Found a Burberry Belt Bag! Item {idx}: {listing_price_str}")
                
            # Get size info - might be a list or string
            size = []
            if isinstance(item_details, dict) and item_details.get('size'):
                raw_size = item_details.get('size')
                if isinstance(raw_size, list):
                    size = raw_size
                else:
                    size = [str(raw_size)]
            
            # Get material and color
            material = item.get('material', '')
            color = item.get('color', '')
                
            # Track brand counts
            if designer:
                brand_counts[designer] = brand_counts.get(designer, 0) + 1
                
            # Structure the transformed item
            transformed_item = {
                "listing_id": item.get('listing_id', ''),
                "source_platform": item.get('source_platform', ''),
                "item_details": {
                    "designer": designer,
                    "model": model,
                    "size": size,
                    "material": material,
                    "color": color
                },
                "listing_price": price_value,
                "condition_rating": condition_rating,
                "condition_category": item.get('condition_rating', '')
            }
            transformed.append(transformed_item)
            
            # Print some debug info for the first few items
            if idx < 5 or idx % 100 == 0:
                print(f"Transformed item {idx}: {designer} {model} - ${price_value} ({condition_str})")
        
        except Exception as e:
            print(f"Error processing item {idx}: {e}")
            continue
    
    print(f"Successfully transformed {len(transformed)} items")
    print("Brand counts in transformed data:")
    for brand, count in sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {brand}: {count} items")
    
    return transformed

def get_listings_data() -> List[Dict[str, Any]]:
    """
    Loads listing data, prioritizing cleaned data, then raw data (with transformation),
    and finally falling back to mock data.
    """
    # First try to load cleaned listings data
    data = load_json_data(CLEANED_LISTINGS_FILE)
    if data is not None:
        print(f"Loaded cleaned listings data from {CLEANED_LISTINGS_FILE}.")
        return data
    
    # If cleaned data not available, try real data (needs transformation)
    data = load_json_data(REAL_LISTINGS_FILE)
    if data is not None:
        print(f"Loaded raw listings data from {REAL_LISTINGS_FILE}. Transforming data...")
        return transform_product_data(data)
    
    # Fall back to mock data if neither cleaned nor raw data is available
    data = load_json_data(LISTINGS_FILE)
    if data is None:
        print(f"Failed to load any listings data. Returning empty list.")
        return []
    
    print(f"Using mock listings data from {LISTINGS_FILE}.")
    return data

def save_trend_data(trend_data: List[Dict[str, Any]]) -> bool:
    """
    Save trend data to a file for future use.
    
    Args:
        trend_data: The trend data to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(REAL_TRENDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(trend_data, f, indent=2)
        print(f"Saved trend data to {REAL_TRENDS_FILE}")
        return True
    except Exception as e:
        print(f"Error saving trend data: {str(e)}")
        return False

def get_trend_score_data() -> List[Dict[str, Any]]:
    """
    Loads trend score data, prioritizing real trend data file if available.
    The format of each item should be:
    {
      "designer": "Brand",
      "model": "Model",
      "trend_score": 0.75,
      "trend_category": "High",
      ...
    }
    """
    # First try to load real trend data
    data = load_json_data(REAL_TRENDS_FILE)
    if data is not None:
        print(f"Loaded real trend data from {REAL_TRENDS_FILE}.")
        return data
    
    # Fall back to mock trend data
    data = load_json_data(TRENDS_FILE)
    if data is None:
        print(f"Failed to load trend score data. Returning empty list.")
        return []
    
    print(f"Using mock trend score data from {TRENDS_FILE}.")
    return data

def get_or_generate_trend_data(target_designer: str, target_model: str) -> Dict[str, Any]:
    """
    Get trend data for a specific designer and model, either from cache or by generating it.
    
    Args:
        target_designer: The designer/brand name
        target_model: The model/style name
        
    Returns:
        A dictionary with trend data and score
    """
    # Import here to avoid circular imports
    from utils.trend_fetcher import get_real_trend_data
    
    # First check if we have it in our saved data
    trend_data = get_trend_score_data()
    
    # Try to find matching trend data
    for item in trend_data:
        if (item.get("designer", "").lower() == target_designer.lower() and 
            item.get("model", "").lower() == target_model.lower()):
            print(f"Found cached trend data for {target_designer} {target_model}")
            return item
    
    # If not found, generate new trend data
    print(f"Generating new trend data for {target_designer} {target_model}")
    new_trend_data = get_real_trend_data(target_designer, target_model)
    
    # Save the new data to our list and persist to file
    trend_data.append(new_trend_data)
    save_trend_data(trend_data)
    
    return new_trend_data 