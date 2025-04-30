#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAG Pricing Estimation Module

This module provides functionality for estimating luxury goods prices using vector retrieval
and statistical methods, providing more accurate and context-aware pricing estimates.
"""

import os
import json
import logging
import statistics
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import services
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(parent_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Import locally
from .vector_store import VectorStore

class RAGPricingEngine:
    """
    RAG Pricing Engine that uses vector retrieval for price estimation.
    """
    
    def __init__(self, vector_store_path: str = "data/vector_store"):
        """
        Initialize the RAG pricing engine.
        
        Args:
            vector_store_path: Path to the vector store
        """
        self.vector_store_path = vector_store_path
        self.vector_store = None
        self._load_vector_store()
    
    def _load_vector_store(self):
        """Load the vector store if it exists."""
        if os.path.exists(self.vector_store_path):
            try:
                logger.info(f"Loading vector store from {self.vector_store_path}")
                self.vector_store = VectorStore()
                self.vector_store.load(self.vector_store_path)
                logger.info(f"Vector store loaded with {len(self.vector_store.items)} items")
            except Exception as e:
                logger.error(f"Error loading vector store: {str(e)}")
                self.vector_store = None
        else:
            logger.warning(f"Vector store not found at {self.vector_store_path}")
            self.vector_store = None
    
    def _create_search_query(self, item_info: Dict[str, Any]) -> str:
        """
        Create a search query from item information.
        
        Args:
            item_info: Dictionary containing item details
            
        Returns:
            Search query string
        """
        # Extract relevant fields
        brand = item_info.get('brand', '') or item_info.get('designer', '')
        model = item_info.get('model', '') or item_info.get('style', '')
        material = item_info.get('material', '')
        color = item_info.get('color', '')
        
        # Create query parts
        query_parts = []
        
        if brand:
            query_parts.append(f"{brand}")
        
        if model:
            query_parts.append(f"{model}")
        
        if material:
            query_parts.append(f"{material}")
        
        if color:
            query_parts.append(f"{color}")
        
        # Add size if available
        size = item_info.get('size', '')
        if size:
            query_parts.append(f"size {size}")
        
        # Create the final query
        query = " ".join(query_parts)
        logger.info(f"Created search query: '{query}'")
        return query
    
    def _filter_results(self, results: List[Dict[str, Any]], item_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter search results to ensure relevance.
        
        Args:
            results: List of retrieved items
            item_info: Target item information
            
        Returns:
            Filtered list of items
        """
        if not results:
            return []
        
        filtered_results = []
        target_brand = (item_info.get('brand', '') or item_info.get('designer', '')).lower()
        target_model = (item_info.get('model', '') or item_info.get('style', '')).lower()
        
        for item in results:
            # Get brand/designer from item
            item_brand = (item.get('brand', '') or item.get('designer', '')).lower()
            
            # Skip if brand doesn't match
            if target_brand and item_brand and target_brand != item_brand:
                continue
            
            # Check model/style - more flexible matching
            item_model = (item.get('model', '') or item.get('style', '')).lower()
            
            # Include if model contains target or target contains model
            if target_model and item_model:
                if target_model in item_model or item_model in target_model:
                    filtered_results.append(item)
            else:
                # If no model specified, include brand matches
                filtered_results.append(item)
        
        logger.info(f"Filtered {len(results)} results to {len(filtered_results)} relevant items")
        return filtered_results
    
    def _calculate_price_stats(self, items: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate price statistics from a list of items.
        
        Args:
            items: List of items with price information
            
        Returns:
            Dictionary with price statistics
        """
        if not items:
            return {
                "median": 0,
                "mean": 0,
                "min": 0,
                "max": 0,
                "stddev": 0,
                "count": 0
            }
        
        # Extract prices, handling different formats
        prices = []
        for item in items:
            price = item.get('price')
            if price is None:
                price = item.get('listing_price')
            
            if price is not None:
                # Convert to float if it's a string
                if isinstance(price, str):
                    try:
                        price = float(price.replace(',', '').replace('$', ''))
                    except ValueError:
                        continue
                prices.append(float(price))
        
        if not prices:
            return {
                "median": 0,
                "mean": 0,
                "min": 0,
                "max": 0,
                "stddev": 0,
                "count": 0
            }
        
        # Calculate statistics
        try:
            return {
                "median": statistics.median(prices),
                "mean": statistics.mean(prices),
                "min": min(prices),
                "max": max(prices),
                "stddev": statistics.stdev(prices) if len(prices) > 1 else 0,
                "count": len(prices)
            }
        except Exception as e:
            logger.error(f"Error calculating price statistics: {str(e)}")
            return {
                "median": sum(prices) / len(prices),
                "mean": sum(prices) / len(prices),
                "min": min(prices),
                "max": max(prices),
                "stddev": 0,
                "count": len(prices)
            }
    
    def _apply_adjustments(self, base_price: float, trend_score: Optional[float] = None, 
                          condition_rating: Optional[int] = None) -> Dict[str, Any]:
        """
        Apply adjustments to the base price based on trend score and condition.
        
        Args:
            base_price: Base price to adjust
            trend_score: Market trend score (0-1)
            condition_rating: Condition rating (0-10)
            
        Returns:
            Dictionary with adjusted price information
        """
        # Start with base price
        adjusted_price = base_price
        adjustment_factors = {}
        
        # Apply condition adjustment
        if condition_rating is not None:
            # Map 0-10 rating to adjustment factor (0.7-1.2)
            condition_factor = 0.7 + (condition_rating / 20)  # 0 -> 0.7, 10 -> 1.2
            adjusted_price *= condition_factor
            adjustment_factors["condition"] = condition_factor
            logger.info(f"Applied condition adjustment: {condition_factor:.2f} (rating: {condition_rating})")
        
        # Apply trend adjustment
        if trend_score is not None:
            # Map 0-1 trend score to factor range (0.85-1.15)
            trend_factor = 0.85 + (trend_score * 0.3)  # 0 -> 0.85, 1 -> 1.15
            adjusted_price *= trend_factor
            adjustment_factors["trend"] = trend_factor
            logger.info(f"Applied trend adjustment: {trend_factor:.2f} (score: {trend_score})")
        
        # Calculate price range based on similar items variation
        price_range = {
            "min": int(adjusted_price * 0.85),
            "max": int(adjusted_price * 1.15)
        }
        
        # Round to nearest 10
        final_price = round(adjusted_price / 10) * 10
        
        return {
            "estimated_price": int(final_price),
            "base_price": int(base_price),
            "price_range": price_range,
            "adjustment_factors": adjustment_factors
        }
    
    def estimate_price(self, item_info: Dict[str, Any], trend_score: Optional[float] = None,
                      condition_rating: Optional[int] = None) -> Dict[str, Any]:
        """
        Estimate the price of a luxury item
        
        Args:
            item_info: Dictionary containing item details (brand, model, etc.)
            trend_score: Market trend score (0-1)
            condition_rating: Item condition rating (0-10)
            
        Returns:
            Dictionary containing estimated price and related information
        """
        if not self.vector_store:
            logger.warning("Vector store is not available. Using fallback data.")
            # Use default values
            return {
                "estimated_price": 0,
                "confidence": "none",
                "error": "Vector store not available",
                "price_range": {
                    "min": 0,
                    "max": 0
                }
            }
        
        try:
            # Build search query
            brand = item_info.get('brand', '') or item_info.get('designer', '')
            model = item_info.get('model', '') or item_info.get('style', '')
            material = item_info.get('material', '')
            color = item_info.get('color', '')
            size = item_info.get('size', '')
            
            # Create query string
            query_parts = []
            if brand:
                query_parts.append(brand)
            if model:
                query_parts.append(model)
            if material:
                query_parts.append(material)
            if color:
                query_parts.append(color)
            if size:
                query_parts.append(size)
            
            query = " ".join(query_parts)
            if not query:
                query = json.dumps(item_info)  # If no key info extracted, use the entire item_info
            
            logger.info(f"Searching for: '{query}'")
            logger.info(f"RAG query details - Brand: {brand}, Model: {model}, Material: {material}, Color: {color}, Size: {size}")
            
            # Execute vector search - use sufficiently large k to ensure enough results
            results = self.vector_store.search(query, k=10)
            
            # Output all search results in detail
            logger.info(f"RAG vector retrieval results - Found {len(results)} similar items:")
            for i, item in enumerate(results):
                listing_name = item.get("listing_name", "Unknown")
                designer = item.get("item_details", {}).get("designer", "Unknown")
                model_name = item.get("item_details", {}).get("model", "Unknown")
                price = item.get("listing_price", 0)
                score = item.get("score", 0)
                logger.info(f"  [{i+1}] {designer} {model_name} ({listing_name}) - Price: ${price:.2f}, Similarity: {score:.4f}")
            
            if not results:
                logger.warning(f"No results found for {query}")
                return {
                    "estimated_price": 0,
                    "confidence": "none",
                    "error": "No relevant items found",
                    "price_range": {
                        "min": 0,
                        "max": 0
                    }
                }
            
            # Extract prices
            prices = []
            for item in results:
                price = item.get('listing_price')
                if price is None:
                    price = item.get('price')
                
                if price is not None:
                    # Convert string prices to float
                    if isinstance(price, str):
                        try:
                            price = float(price.replace(',', '').replace('$', ''))
                        except ValueError:
                            continue
                    prices.append(float(price))
            
            # Output price list in detail
            logger.info(f"RAG price analysis - Extracted {len(prices)} valid prices:")
            for i, price in enumerate(prices):
                logger.info(f"  Price[{i+1}]: ${price:.2f}")
            
            if not prices:
                logger.warning("No valid prices found in results")
                return {
                    "estimated_price": 0,
                    "confidence": "none",
                    "error": "No valid prices found",
                    "price_range": {
                        "min": 0,
                        "max": 0
                    }
                }
            
            # Calculate price statistics
            price_stats = {
                "median": statistics.median(prices),
                "mean": statistics.mean(prices),
                "min": min(prices),
                "max": max(prices),
                "stddev": statistics.stdev(prices) if len(prices) > 1 else 0,
                "count": len(prices)
            }
            
            # Output statistics details
            logger.info(f"RAG price statistics:")
            logger.info(f"  Median: ${price_stats['median']:.2f}")
            logger.info(f"  Mean: ${price_stats['mean']:.2f}")
            logger.info(f"  Min: ${price_stats['min']:.2f}")
            logger.info(f"  Max: ${price_stats['max']:.2f}")
            logger.info(f"  StdDev: ${price_stats['stddev']:.2f}")
            
            # Use median as base price
            base_price = price_stats["median"]
            logger.info(f"RAG base price: ${base_price:.2f} (using median)")
            
            # Apply adjustments
            adjusted_price = base_price
            adjustment_factors = {}
            
            # Condition adjustment
            if condition_rating is not None:
                # Map 0-10 rating to adjustment factor (0.7-1.2)
                condition_factor = 0.7 + (condition_rating / 20)  # 0 -> 0.7, 10 -> 1.2
                adjusted_price *= condition_factor
                adjustment_factors["condition"] = condition_factor
                logger.info(f"RAG adjustment - Applied condition factor: {condition_factor:.2f} (rating: {condition_rating})")
                logger.info(f"  Adjusted price: ${adjusted_price:.2f}")
            
            # Trend score adjustment
            if trend_score is not None:
                # Map 0-1 trend score to factor range (0.85-1.15)
                trend_factor = 0.85 + (trend_score * 0.3)  # 0 -> 0.85, 1 -> 1.15
                adjusted_price *= trend_factor
                adjustment_factors["trend"] = trend_factor
                logger.info(f"RAG adjustment - Applied trend factor: {trend_factor:.2f} (trend score: {trend_score:.2f})")
                logger.info(f"  Adjusted price: ${adjusted_price:.2f}")
            
            # Calculate price range
            price_range = {
                "min": int(adjusted_price * 0.85),
                "max": int(adjusted_price * 1.15)
            }
            logger.info(f"RAG price range: ${price_range['min']} - ${price_range['max']}")
            
            # Determine confidence level
            if price_stats["count"] >= 5:
                confidence = "high"
            elif price_stats["count"] >= 2:
                confidence = "medium"
            else:
                confidence = "low"
            
            logger.info(f"RAG confidence: {confidence} (based on {price_stats['count']} price samples)")
            
            # Return result
            result = {
                "estimated_price": int(adjusted_price),
                "base_price": int(base_price),
                "confidence": confidence,
                "price_range": price_range,
                "price_stats": price_stats,
                "adjustment_factors": adjustment_factors,
                "matched_items_count": price_stats["count"],
                "similar_items": [
                    {
                        "listing_name": item.get("listing_name", ""),
                        "designer": item.get("item_details", {}).get("designer", ""),
                        "model": item.get("item_details", {}).get("model", ""), 
                        "price": item.get("listing_price", 0),
                        "similarity": item.get("score", 0)
                    } for item in results[:3]  # Only include top 3 similar items
                ]
            }
            
            logger.info(f"RAG price estimation complete: ${result['estimated_price']} (confidence: {confidence})")
            return result
            
        except Exception as e:
            logger.error(f"Error estimating price: {str(e)}", exc_info=True)
            return {
                "estimated_price": 0,
                "confidence": "none",
                "error": str(e),
                "price_range": {
                    "min": 0,
                    "max": 0
                }
            }

def get_price_estimation_with_rag(item_info: Dict[str, Any], trend_score: Optional[float] = None,
                                 condition_rating: Optional[int] = None, 
                                 vector_store_path: str = "data/vector_store") -> Dict[str, Any]:
    """
    Convenience function to estimate price using RAG system.
    
    Args:
        item_info: Dictionary containing item details
        trend_score: Market trend score (0-1)
        condition_rating: Condition rating (0-10)
        vector_store_path: Path to vector store
        
    Returns:
        Dictionary with price estimation results
    """
    engine = RAGPricingEngine(vector_store_path)
    return engine.estimate_price(item_info, trend_score, condition_rating) 