#!/usr/bin/env python3
"""
Script to import luxury item listings from cleaned_listings.json into a vector store.
This script converts the item listings to embeddings and stores them in a FAISS vector database
for efficient semantic search.
"""

import os
import json
import argparse
import logging
from typing import List, Dict, Any
import sys

# Add parent directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.rag.vector_store import VectorStore, save_vector_store
from services.rag.text_embedder import TextEmbedder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_listings(filepath: str) -> List[Dict[str, Any]]:
    """
    Load luxury item listings from a JSON file.
    
    Args:
        filepath: Path to the JSON file
    
    Returns:
        A list of luxury item dictionaries
    """
    try:
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            logger.error(f"Expected a list in {filepath}, but got {type(data).__name__}")
            return []
        
        logger.info(f"Loaded {len(data)} listings from {filepath}")
        return data
    except Exception as e:
        logger.error(f"Error loading listings from {filepath}: {e}")
        return []

def transform_listing_to_item(listing: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a listing dictionary into a format suitable for the vector store.
    
    Args:
        listing: The original listing dictionary
    
    Returns:
        A transformed item dictionary
    """
    # Extract item details
    item_details = listing.get('item_details', {})
    if not isinstance(item_details, dict):
        item_details = {}
    
    # Generate a unique ID if not present
    listing_id = listing.get('listing_id')
    if not listing_id:
        import hashlib
        # Create a hash from listing details to serve as ID
        hash_input = json.dumps(listing, sort_keys=True)
        listing_id = hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    # Extract key fields
    designer = item_details.get('designer', listing.get('designer', ''))
    model = item_details.get('model', listing.get('model', ''))
    listing_name = listing.get('listing_name', '')
    
    # If model is empty but listing_name is provided, use listing_name without designer prefix
    if not model and listing_name:
        if designer and listing_name.lower().startswith(designer.lower()):
            model = listing_name[len(designer):].strip()
        else:
            model = listing_name
    
    # Extract other details
    size = item_details.get('size', [])
    if not isinstance(size, list):
        size = [str(size)]
    
    # Build materials list
    materials = []
    if 'material' in item_details:
        material = item_details.get('material')
        if isinstance(material, list):
            materials.extend(material)
        else:
            materials.append(str(material))
    
    if 'materials' in item_details:
        material_list = item_details.get('materials')
        if isinstance(material_list, list):
            materials.extend(material_list)
        else:
            materials.append(str(material_list))
    
    # Extract color
    color = item_details.get('color', '')
    
    # Extract price and condition
    price = listing.get('listing_price')
    if isinstance(price, str) and price.startswith('$'):
        try:
            price = float(price.replace('$', '').replace(',', ''))
        except (ValueError, TypeError):
            price = None
    
    condition_rating = listing.get('condition_rating')
    condition_category = listing.get('condition_category', '')
    
    # Build keywords for better searchability
    keywords = []
    if designer:
        keywords.append(designer)
    if model:
        keywords.append(model)
    if color:
        keywords.append(color)
    for material in materials:
        keywords.append(material)
    
    # Create features list
    features = []
    for feature in item_details.get('features', []):
        if isinstance(feature, str):
            features.append(feature)
    
    # Build description
    description = item_details.get('item_description', '')
    if not description and listing_name:
        description = f"{designer} {model} {' '.join(materials)} {color}".strip()
    
    # Create transformed item
    transformed_item = {
        "id": listing_id,
        "brand": designer,
        "model": model,
        "size": size,
        "materials": materials,
        "color": color,
        "price": price,
        "condition_rating": condition_rating,
        "condition_category": condition_category,
        "description": description,
        "features": features,
        "keywords": keywords,
        "source_platform": listing.get('source_platform', ''),
        "original_data": listing  # Keep original data for reference
    }
    
    return transformed_item

def import_listings_to_vector_store(listings_file: str, output_dir: str, batch_size: int = 100) -> bool:
    """
    Import listings from JSON file to vector store.
    
    Args:
        listings_file: Path to the JSON file with listings
        output_dir: Directory to save the vector store
        batch_size: Number of items to process in each batch
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load listings
        listings = load_listings(listings_file)
        if not listings:
            logger.error("No listings to import")
            return False
        
        # Create vector store
        logger.info("Initializing vector store")
        vector_store = VectorStore()
        
        # Transform and add listings in batches
        total_items = len(listings)
        total_added = 0
        
        logger.info(f"Processing {total_items} listings in batches of {batch_size}")
        
        for i in range(0, total_items, batch_size):
            batch = listings[i:i+batch_size]
            transformed_batch = [transform_listing_to_item(listing) for listing in batch]
            
            added, total = vector_store.add_items(transformed_batch)
            total_added += added
            
            logger.info(f"Batch {i//batch_size + 1}: Added {added}/{total} items")
        
        # Save vector store
        logger.info(f"Saving vector store to {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        if save_vector_store(vector_store, output_dir):
            logger.info(f"Successfully imported {total_added}/{total_items} listings to vector store")
            return True
        else:
            logger.error("Failed to save vector store")
            return False
    
    except Exception as e:
        logger.error(f"Error importing listings to vector store: {e}", exc_info=True)
        return False

def main():
    parser = argparse.ArgumentParser(description="Import luxury item listings to vector store")
    parser.add_argument(
        "--input", 
        default="data/cleaned_listings.json",
        help="Path to the listings JSON file (default: data/cleaned_listings.json)"
    )
    parser.add_argument(
        "--output", 
        default="vector_store/luxury_items_store",
        help="Directory to save the vector store (default: vector_store/luxury_items_store)"
    )
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=100,
        help="Number of items to process in each batch (default: 100)"
    )
    
    args = parser.parse_args()
    
    success = import_listings_to_vector_store(args.input, args.output, args.batch_size)
    
    if success:
        logger.info("Import completed successfully")
        sys.exit(0)
    else:
        logger.error("Import failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 