import json
import os
import re
import uuid # To generate listing IDs if missing
from typing import List, Dict, Any, Optional

# --- Configuration ---
DATA_FOLDER = "data"
# Input file can contain mixed data now
RAW_LISTINGS_FILE = os.path.join(DATA_FOLDER, "product_scraped.json") # Or your combined raw data file
CLEANED_LISTINGS_FILE = os.path.join(DATA_FOLDER, "cleaned_listings.json") # Output file

# --- MODIFIED: Condition Score Mapping ---
# Added full description phrases from VC examples (lowercase)
CONDITION_RATING_TO_SCORE = {
    # Fashionphile terms (example)
    "new": 5, "excellent": 4, "very good": 3, "good": 2, "fair": 1, "shows wear": 1,
    # Vestiaire terms (using description text)
    "never worn": 5,
    "excellent condition": 4, # Added
    "very good condition": 3, # Added
    "good condition": 2,      # Added
    "fair condition": 1,      # Added
    # Add other VC description terms and map them appropriately
    "unknown": 2 # Default
}
DEFAULT_CONDITION_SCORE = 2

# --- Keywords for Extraction ---
COMMON_MATERIALS = [
    "canvas", "caviar leather", "lambskin leather", "calfskin", "exotic skin", "wicker",
    "python", "crocodile", "alligator", "ostrich", "lizard", "suede",
    "velvet", "nylon", "denim", "togo leather", "epsom leather",
    "clemence leather", "monogram", "damier ebene", "damier azur", "vachetta",
    "leather"
]
COMMON_COLORS = [
    "black", "white", "brown", "beige", "tan", "red", "blue", "green",
    "pink", "purple", "yellow", "orange", "grey", "gray",
    "silver", "gold", "multicolor", "multi color", "multi-color",
    "etoupe", "etain", "noir", "craie", "monogram", "damier ebene", "damier azur",
    "ivory", "cream", "camel"
]
BAG_TYPES = [
    "tote bag", "tote", "shoulder bag", "crossbody bag", "cross body bag",
    "hobo", "satchel", "clutch", "backpack", "bucket bag", "top handle bag",
    "waist bag", "belt bag", "pouch", "camera bag", "flap bag", "baguette", "vanity"
]
STANDARD_SIZES_GENERIC = [
    "nano", "mini", "small", "medium", "large", "jumbo", "maxi"
]
STANDARD_SIZES_LV = ["pm", "mm", "gm"]
STANDARD_SIZES_HERMES = ["19", "20", "25", "28", "30", "31", "32", "35", "40"]

# --- Currency Conversion ---
CHF_TO_USD_RATE = 1.10 # Example rate

# --- Helper Functions ---

def load_json_data(filepath: str) -> Optional[List[Dict[str, Any]]]:
    """Loads list data from a JSON file."""
    # (Keep the robust load_json_data function)
    if not os.path.exists(filepath):
        print(f"Error: File not found at {filepath}")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alt_filepath = os.path.join(script_dir, filepath)
        if not os.path.exists(alt_filepath): return None
        filepath = alt_filepath
    try:
        with open(filepath, 'r', encoding='utf-8') as f: data = json.load(f)
        return data if isinstance(data, list) else None
    except Exception as e: print(f"Error loading {filepath}: {e}"); return None

def save_json_data(data: List[Dict[str, Any]], filepath: str):
    """Saves data to a JSON file."""
    # (Keep the save_json_data function)
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
        print(f"Successfully saved cleaned data to {filepath}")
    except Exception as e: print(f"Error saving data to {filepath}: {e}")

def clean_price(price_input: Any, currency: Optional[str]) -> Optional[float]:
    """Removes currency symbols, commas, converts to float, and handles currency conversion."""
    # (Keep the clean_price function)
    price_str = str(price_input)
    try:
        cleaned = re.sub(r"[$,€£CHF\s]", "", price_str)
        price_float = float(cleaned)
        if currency and currency.upper() == "CHF":
            price_float *= CHF_TO_USD_RATE
            # print(f"Converted CHF {cleaned} to USD {price_float:.2f}") # Optional log
        return price_float
    except (ValueError, TypeError):
        print(f"Warning: Could not convert price '{price_input}' to float.")
        return None

# --- MODIFIED: Condition Mapping Function ---
def map_condition_to_score(rating_input: Any) -> Optional[int]:
     """
     Maps condition string (description or rating) to numerical score.
     Uses the updated CONDITION_RATING_TO_SCORE dictionary.
     """
     if not isinstance(rating_input, str): return None
     # Convert to lowercase and strip whitespace for reliable matching
     rating_lower = rating_input.lower().strip()

     # Use .get() which handles missing keys gracefully
     score = CONDITION_RATING_TO_SCORE.get(rating_lower)

     if score is not None:
         return score
     else:
         # If no exact match, check for partial matches (less reliable)
         if "shows wear" in rating_lower: return CONDITION_RATING_TO_SCORE.get("shows wear")
         if "never worn" in rating_lower: return CONDITION_RATING_TO_SCORE.get("never worn")
         if "excellent" in rating_lower: return CONDITION_RATING_TO_SCORE.get("excellent")
         if "very good" in rating_lower: return CONDITION_RATING_TO_SCORE.get("very good")
         if "good" in rating_lower: return CONDITION_RATING_TO_SCORE.get("good")
         if "fair" in rating_lower: return CONDITION_RATING_TO_SCORE.get("fair")

         # If still no match, use default
         print(f"Warning: Unmapped condition rating/description: '{rating_input}'. Using default.")
         return DEFAULT_CONDITION_SCORE

def extract_size_string(size_data: Any, description: Optional[str] = None, designer: Optional[str] = None) -> Optional[str]:
    """Attempts to extract a standard size string."""
    # (Keep the updated extract_size_string function)
    size_found = None
    standard_sizes_to_check = STANDARD_SIZES_GENERIC
    designer_lower = str(designer).lower() if designer else ""
    if "louis vuitton" in designer_lower: standard_sizes_to_check = STANDARD_SIZES_LV + STANDARD_SIZES_GENERIC
    elif "hermes" in designer_lower: standard_sizes_to_check = STANDARD_SIZES_HERMES + STANDARD_SIZES_GENERIC
    if isinstance(size_data, str):
        size_lower = size_data.lower()
        for size_keyword in standard_sizes_to_check:
            if re.search(r'\b' + re.escape(size_keyword) + r'\b', size_lower): size_found = size_keyword; break
    elif isinstance(size_data, list):
        size_str_from_list = " ".join(filter(None, size_data)).lower()
        for size_keyword in standard_sizes_to_check:
             if re.search(r'\b' + re.escape(size_keyword) + r'\b', size_str_from_list): size_found = size_keyword; break
    if size_found is None and isinstance(description, str) and description:
        desc_lower = description.lower(); brand_specific_sizes = []
        if "louis vuitton" in designer_lower: brand_specific_sizes = STANDARD_SIZES_LV
        elif "hermes" in designer_lower: brand_specific_sizes = STANDARD_SIZES_HERMES
        for size_keyword in brand_specific_sizes:
             if re.search(r'\b' + re.escape(size_keyword) + r'\b', desc_lower): size_found = size_keyword; break
        if size_found is None:
            sorted_generic_sizes = sorted(STANDARD_SIZES_GENERIC, key=len, reverse=True)
            for size_keyword in sorted_generic_sizes:
                if re.search(r'\b' + re.escape(size_keyword) + r'\b', desc_lower): size_found = size_keyword; break
    if size_found:
        if size_found in STANDARD_SIZES_LV: return size_found.upper()
        elif size_found.isalpha(): return size_found.capitalize()
        else: return size_found
    return None

def determine_source(listing: Dict[str, Any]) -> Optional[str]:
    """Determines the source platform, handling potential key variations."""
    # (Keep the updated determine_source function)
    source = listing.get("source_platform") or listing.get("source_plateform")
    if isinstance(source, str) and source.strip():
        src_lower = source.lower().strip()
        if "vestiaire" in src_lower: return "Vestiaire Collective"
        if "fashionphile" in src_lower: return "Fashionphile"
        return source.strip()
    url = listing.get("listing_url", "")
    if "fashionphile.com" in url: return "Fashionphile"
    if "vestiairecollective.com" in url: return "Vestiaire Collective"
    return None

def extract_materials_from_desc(description: str) -> Optional[str]:
    """Extracts all matching materials, returns comma-separated string."""
    # (Keep the extract_materials_from_desc function)
    if not isinstance(description, str): return None
    desc_lower = description.lower(); found_materials = set()
    sorted_materials = sorted(COMMON_MATERIALS, key=len, reverse=True)
    for material in sorted_materials:
        if re.search(r'\b' + re.escape(material) + r'\b', desc_lower):
            is_subtype = False; material_title = material.title()
            if material == "leather":
                 for found in found_materials:
                      if "leather" in found.lower() and found.lower() != "leather": is_subtype = True; break
            if not is_subtype:
                if "leather" in material: material_title = material.replace(" leather", " Leather").title()
                elif "canvas" in material: material_title = material.replace(" canvas", " Canvas").title()
                found_materials.add(material_title)
    return ", ".join(sorted(list(found_materials))) if found_materials else None

def extract_colors_string_from_desc(description: str) -> Optional[str]:
    """Extracts all matching colors, returns comma-separated string."""
    # (Keep the extract_colors_string_from_desc function)
    if not isinstance(description, str): return None
    desc_lower = description.lower(); found_colors = set()
    sorted_colors = sorted(COMMON_COLORS, key=len, reverse=True)
    for color in sorted_colors:
        if re.search(r'\b' + re.escape(color) + r'\b', desc_lower):
            if color in ["multi color", "multi-color", "multicolor"]: found_colors.add("Multicolor")
            else: found_colors.add(color.title())
    return ", ".join(sorted(list(found_colors))) if found_colors else None

def extract_category(category_field_value: Any, description: str) -> str:
    """Determines the bag category. Checks field first, then description."""
    # (Keep the extract_category function)
    if isinstance(category_field_value, str):
        cat_lower = category_field_value.lower().strip()
        for bag_type in BAG_TYPES:
             std_bag_type = bag_type.replace(" bag", "").strip()
             cat_compare = cat_lower.replace(" bag", "").strip()
             if cat_compare == std_bag_type or cat_compare == std_bag_type + 's':
                 return bag_type.replace(" bag", " Bag").title()
        if len(category_field_value) < 30: return category_field_value
    if isinstance(description, str):
        desc_lower = description.lower()
        sorted_bag_types = sorted(BAG_TYPES, key=len, reverse=True)
        for bag_type in sorted_bag_types:
            if re.search(r'\b' + re.escape(bag_type) + r'\b', desc_lower):
                return bag_type.replace(" bag", " Bag").title()
    return "Unknown"

def clean_model_name(raw_model_name: Optional[str], category: Optional[str], size: Optional[str], material: Optional[str], color: Optional[str]) -> Optional[str]:
    """Cleans model name using context from other extracted fields."""
    # (Keep the clean_model_name function)
    if not isinstance(raw_model_name, str) or not raw_model_name.strip(): return raw_model_name
    cleaned_model = raw_model_name.strip(); descriptors_to_remove = set()
    if isinstance(category, str) and category != "Unknown": descriptors_to_remove.update(word for word in category.lower().split() if len(word) > 2)
    if isinstance(size, str): descriptors_to_remove.add(size.lower())
    if isinstance(material, str):
        descriptors_to_remove.update(mat.strip().lower() for mat in material.split(',') if mat.strip())
        if "leather" in material.lower(): descriptors_to_remove.add("leather")
        if "canvas" in material.lower(): descriptors_to_remove.add("canvas")
    if isinstance(color, str): descriptors_to_remove.update(col.strip().lower() for col in color.split(',') if col.strip())
    descriptors_to_remove.discard("bag")
    sorted_descriptors = sorted(list(d for d in descriptors_to_remove if d), key=len, reverse=True)
    for _ in range(3):
        model_before_pass = cleaned_model
        for desc in sorted_descriptors:
            pattern = r'\s+\b' + re.escape(desc) + r'\b$'
            new_model, num_subs = re.subn(pattern, '', cleaned_model, flags=re.IGNORECASE)
            if num_subs > 0:
                if new_model.strip(): cleaned_model = new_model.strip()
                else: cleaned_model = new_model.strip() # Allow empty for now
        if cleaned_model == model_before_pass: break
    cleaned_model = re.sub(r'[\s,-]+$', '', cleaned_model).strip()
    return cleaned_model if len(cleaned_model) > 2 else raw_model_name.strip()

# --- Main Cleaning Function ---

def clean_data(raw_listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Cleans and restructures scraped data from multiple sources (Fashionphile, VC)
    into a common format.
    """
    if not raw_listings: return []
    cleaned_data = []
    skipped_count = 0

    for i, listing in enumerate(raw_listings):
        if not isinstance(listing, dict): skipped_count += 1; continue

        # 1. Determine Source Platform
        source = determine_source(listing)
        if not source: skipped_count += 1; continue # Skip if source unknown

        # 2. Extract and Clean/Map Top-Level Fields
        listing_currency = listing.get("currency")
        price = clean_price(listing.get("listing_price"), listing_currency)

        # --- Condition Mapping Logic (Uses description for VC) ---
        condition_input_str = None
        if source == "Vestiaire Collective":
            condition_input_str = listing.get("condition_description")
        else: # Assume Fashionphile uses rating field
            condition_input_str = listing.get("condition_rating")
        condition_score = map_condition_to_score(condition_input_str)
        # --- End Condition Logic ---

        details_input = listing.get("item_details", {})
        if not isinstance(details_input, dict): details_input = {}
        designer_raw = details_input.get("designer", listing.get("designer"))
        model_raw = details_input.get("model", listing.get("model", listing.get("listing_name")))

        # 3. Validate Essential Cleaned Data
        designer_cleaned = designer_raw.strip() if isinstance(designer_raw, str) else None
        if price is None or condition_score is None or not designer_cleaned or not model_raw:
            print(f"Warning: Skipping listing {listing.get('listing_url')} (Source: {source}) due to missing essential data.")
            skipped_count += 1; continue

        # 4. Extract and Structure Remaining Fields
        cleaned_listing = {}
        cleaned_listing["listing_id"] = listing.get("listing_id") or str(uuid.uuid4())
        cleaned_listing["listing_url"] = listing.get("listing_url")
        cleaned_listing["listing_name"] = listing.get("listing_name")

        # Handle VC Expert Seller Status
        final_source_platform = source
        if source == "Vestiaire Collective":
            seller_status_list = listing.get("seller_status")
            if isinstance(seller_status_list, list) and "expert-seller" in seller_status_list:
                final_source_platform = "Vestiaire Collective Expert"
        cleaned_listing["source_platform"] = final_source_platform

        cleaned_listing["listing_price"] = price # Price is now cleaned and potentially converted to USD
        cleaned_listing["currency"] = "USD" # Standardize currency to USD
        cleaned_listing["location"] = listing.get("location")
        cleaned_listing["condition_rating"] = condition_score # Use the mapped numerical score
        cleaned_listing["condition_description"] = listing.get("condition_description") # Store original description

        # Create nested item_details
        item_description = details_input.get("item_description", "")

        # Extract Material (Conditional based on source - only extract from desc for FP)
        material_str = details_input.get("material")
        if source == "Fashionphile" and (not isinstance(material_str, str) or not material_str.strip()):
             material_str = extract_materials_from_desc(item_description)
        elif isinstance(material_str, str):
             material_str = material_str.strip()

        # Extract Color (Conditional based on source - only extract from desc for FP)
        color_str = details_input.get("color")
        if source == "Fashionphile" and (not isinstance(color_str, str) or not color_str.strip()):
             color_str = extract_colors_string_from_desc(item_description)
        elif isinstance(color_str, str):
             color_str = color_str.strip()

        # Extract Category
        raw_category_value = details_input.get("category")
        final_category = extract_category(raw_category_value, item_description)

        # Extract Size
        final_size = extract_size_string(
            details_input.get("size"),
            description=item_description,
            designer=designer_cleaned
        )

        # Clean Model Name (Conditional based on source - only clean for FP)
        if source == "Fashionphile":
             final_model = clean_model_name(model_raw, final_category, final_size, material_str, color_str)
        else: # Assume VC model name is cleaner
             final_model = model_raw.strip() if isinstance(model_raw, str) else model_raw

        cleaned_listing["item_details"] = {
            "category": final_category,
            "designer": designer_cleaned,
            "model": final_model,
            "item_description": item_description,
            "size": final_size,
            "material": material_str,
            "color": color_str
        }

        # Inclusions
        inclusions = listing.get("inclusions")
        cleaned_listing["inclusions"] = inclusions if isinstance(inclusions, list) else []

        # Authenticity Notes
        auth_notes = listing.get("authenticity_notes")
        if source == "Fashionphile": cleaned_listing["authenticity_notes"] = True
        elif isinstance(auth_notes, str) and "Optional" in auth_notes: cleaned_listing["authenticity_notes"] = False
        else: cleaned_listing["authenticity_notes"] = None

        # Seller Status
        cleaned_listing["seller_status"] = listing.get("seller_status")

        # 5. Final check
        if cleaned_listing["item_details"]["designer"] is None or cleaned_listing["item_details"]["model"] is None:
             print(f"Warning: Skipping listing {cleaned_listing.get('listing_url')} due to missing designer/model after processing.")
             skipped_count += 1; continue

        # 6. Add to output list
        cleaned_data.append(cleaned_listing)

    print(f"Cleaning complete. Processed {len(raw_listings)} raw listings.")
    print(f"Kept and cleaned {len(cleaned_data)} listings.")
    print(f"Skipped {skipped_count} listings (non-Fashionphile/VC or missing/invalid essential data).")
    return cleaned_data

# --- Main Execution ---
if __name__ == "__main__":
    print(f"Loading raw data from {RAW_LISTINGS_FILE}...")
    raw_data = load_json_data(RAW_LISTINGS_FILE)
    if raw_data:
        print("Cleaning data for Fashionphile and Vestiaire Collective...")
        cleaned_listings = clean_data(raw_data)
        if cleaned_listings:
            print(f"Saving {len(cleaned_listings)} cleaned listings to {CLEANED_LISTINGS_FILE}...")
            save_json_data(cleaned_listings, CLEANED_LISTINGS_FILE)
            # Optional: Print first cleaned item for verification
            if cleaned_listings:
               print("\n--- First Cleaned Item Example ---")
               print(json.dumps(cleaned_listings[0], indent=2))
               print("--------------------------")
        else:
            print("No listings remained after cleaning and filtering.")
    else:
        print("Failed to load raw data.")
