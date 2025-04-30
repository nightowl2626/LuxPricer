"""
RAG Service Module
Provides integration between the RAG system and the pricing logic.
This service enables retrieval of luxury items based on semantic search rather than
hardcoded similarity matching.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple

from services.rag.query import query_luxury_items
from utils.pricing_logic import estimate_price, EXACT_MATCH_SIMILARITY_SCORE

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LuxuryItemRAGService:
    """
    Service for retrieving luxury items using RAG (Retrieval-Augmented Generation).
    This service replaces the hardcoded similarity matching in pricing_logic.py with
    a more flexible semantic search using embeddings.
    """
    
    def __init__(self):
        """Initialize the service."""
        logger.info("Initializing LuxuryItemRAGService")
    
    def get_similar_items(
        self, 
        target_item: Dict[str, Any], 
        top_k: int = 20,
        use_hybrid_search: bool = True,
        use_reranker: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get items similar to the target item using RAG.
        
        Args:
            target_item: The target item to find similar items for
            top_k: Number of similar items to retrieve
            use_hybrid_search: Whether to use hybrid search
            use_reranker: Whether to use reranker
            
        Returns:
            A list of similar items
        """
        designer = target_item.get('designer')
        model = target_item.get('model')
        
        if not designer or not model:
            logger.warning("Cannot search without designer and model")
            return []
        
        # Construct query based on target item details
        query_parts = [designer, model]
        
        # Add other details if available
        item_details = target_item.get('item_details', {})
        if item_details:
            for field in ['size', 'material', 'color']:
                if field in item_details and item_details[field]:
                    value = item_details[field]
                    if isinstance(value, list):
                        value = ' '.join(map(str, value))
                    query_parts.append(str(value))
        
        query = ' '.join(query_parts)
        logger.info(f"Constructed query: {query}")
        
        # Execute query
        brand_filter = designer  # Use exact brand match
        
        try:
            results = query_luxury_items(
                query=query,
                top_k=top_k,
                brand_filter=brand_filter,
                use_hybrid_search=use_hybrid_search,
                use_reranker=use_reranker
            )
            
            if not results or "results" not in results:
                logger.warning(f"No results found for query: {query}")
                return []
            
            return results["results"]
        
        except Exception as e:
            logger.error(f"Error retrieving similar items: {e}", exc_info=True)
            return []
    
    def estimate_price_with_rag(
        self, 
        target_item: Dict[str, Any],
        trend_data: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Estimate price using items retrieved via RAG.
        
        Args:
            target_item: The target item to estimate price for
            trend_data: Trend data for price adjustments
            
        Returns:
            Price estimation result or None if estimation fails
        """
        logger.info(f"Estimating price with RAG for {target_item.get('designer')} {target_item.get('model')}")
        
        # Get similar items using RAG
        similar_items = self.get_similar_items(target_item)
        
        if not similar_items:
            error_msg = f"Insufficient comparable listings found via RAG for {target_item.get('designer')} {target_item.get('model')}"
            logger.warning(error_msg)
            return {"error": error_msg}
        
        # Transform similar items to the format expected by pricing_logic
        transformed_listings = []
        
        for item in similar_items:
            # Extract fields needed for pricing logic
            try:
                listing = {
                    "listing_id": item.get("id", ""),
                    "source_platform": item.get("source_platform", ""),
                    "item_details": {
                        "designer": item.get("brand", ""),
                        "model": item.get("model", ""),
                        "size": item.get("size", []),
                        "material": item.get("materials", []),
                        "color": item.get("color", "")
                    },
                    "listing_price": item.get("price", 0),
                    "condition_rating": item.get("condition_rating", 3),
                    "similarity": item.get("score", 0.5)  # Use RAG score
                }
                
                # If we have original_data, use it to enrich the transformed listing
                if "original_data" in item:
                    listing.update(item["original_data"])
                
                transformed_listings.append(listing)
            except Exception as e:
                logger.warning(f"Error transforming item {item.get('id', '')}: {e}")
                continue
        
        logger.info(f"Found {len(transformed_listings)} comparable listings via RAG")
        
        # Use pricing_logic to estimate price
        estimated_price = estimate_price(target_item, transformed_listings, trend_data)
        
        # Add RAG-specific information to the result
        if estimated_price and "error" not in estimated_price:
            estimated_price["retrieval_method"] = "rag"
            estimated_price["rag_items_found"] = len(similar_items)
            
            # Add items with very high similarity scores as "exact matches"
            exact_matches = []
            for item in similar_items:
                if item.get("score", 0) >= EXACT_MATCH_SIMILARITY_SCORE:
                    if "price" in item and item["price"] is not None:
                        exact_matches.append(item["price"])
            
            if exact_matches:
                estimated_price["exact_match_count"] = len(exact_matches)
                estimated_price["min_exact_match_price"] = min(exact_matches)
                estimated_price["max_exact_match_price"] = max(exact_matches)
        
        return estimated_price

# Singleton instance
rag_service = LuxuryItemRAGService()

def get_rag_service() -> LuxuryItemRAGService:
    """
    Get the RAG service instance.
    
    Returns:
        LuxuryItemRAGService instance
    """
    return rag_service 