"""
RAG Query Module
Processes user queries and retrieves relevant luxury item information
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
import re
import time
import numpy as np
import hashlib
from concurrent.futures import ThreadPoolExecutor

from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain_core.documents import Document
import operator

from services.rag.vector_store import VectorStore, load_vector_store
from services.rag.text_embedder import TextEmbedder, get_embedder
from services.rag.reranker import Reranker, get_reranker

# Setup logging
logger = logging.getLogger(__name__)

class LuxuryItemsRetriever:
    """Luxury items information retriever"""
    
    def __init__(self, 
                 vector_store: Optional[VectorStore] = None,
                 vector_store_path: str = "vector_store/luxury_items_store",
                 embedder: Optional[TextEmbedder] = None,
                 reranker: Optional[Reranker] = None):
        """
        Initialize the retriever
        
        Args:
            vector_store: Vector store instance, if None attempts to load
            vector_store_path: Path to vector store
            embedder: Text embedder
            reranker: Reranker for post-processing results
        """
        self.vector_store_path = vector_store_path
        
        # Initialize vector store
        if vector_store:
            self.vector_store = vector_store
            logger.info("Using provided vector store")
        else:
            self.vector_store = load_vector_store(vector_store_path)
            if not self.vector_store:
                logger.warning(f"Failed to load vector store from {vector_store_path}, initializing empty store")
                self.vector_store = VectorStore()
        
        # Initialize embedder
        self.embedder = embedder or get_embedder()
        
        # Initialize reranker
        self.reranker = reranker or get_reranker("ensemble")
        
        logger.info("Initialized LuxuryItemsRetriever")
    
    def search(self, 
               query: str, 
               top_k: int = 5, 
               brand_filter: Optional[str] = None,
               category_filter: Optional[str] = None,
               price_range: Optional[Tuple[float, float]] = None,
               use_hybrid_search: bool = True,
               use_reranker: bool = True) -> List[Dict[str, Any]]:
        """
        Search for relevant luxury items
        
        Args:
            query: User query
            top_k: Number of results to return
            brand_filter: Brand filter
            category_filter: Category filter
            price_range: Price range (min, max)
            use_hybrid_search: Whether to use hybrid search (vector + BM25)
            use_reranker: Whether to use reranker for result refinement
            
        Returns:
            List of matching luxury items
        """
        start_time = time.time()
        
        # Choose search method
        if use_hybrid_search:
            try:
                results = self._hybrid_search(query, top_k=min(top_k * 3, 20))
            except Exception as e:
                logger.warning(f"Hybrid search failed, falling back to vector search: {str(e)}")
                results = self._vector_search(query, top_k=min(top_k * 3, 20))
        else:
            results = self._vector_search(query, top_k=min(top_k * 3, 20))
        
        if not results:
            logger.warning(f"No results found for query: {query}")
            return []
        
        # Apply filters
        filtered_results = self._apply_filters(
            results, 
            brand_filter=brand_filter,
            category_filter=category_filter,
            price_range=price_range
        )
        
        # Apply reranker if enabled
        if use_reranker and self.reranker and filtered_results:
            try:
                reranked_results = self.reranker.rerank(query, filtered_results)
                
                # Log reranking impact
                logger.debug(f"Reranking changed order for query: {query}")
                filtered_results = reranked_results
            except Exception as e:
                logger.error(f"Reranking failed: {str(e)}", exc_info=True)
                # Continue with filtered results if reranking fails
        
        # Take top_k results
        final_results = filtered_results[:top_k]
        
        # Log search performance
        search_time = time.time() - start_time
        logger.info(f"Search completed in {search_time:.3f}s, found {len(final_results)} results for query: {query}")
        
        return final_results
    
    def _vector_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Basic vector search"""
        return self.vector_store.search(query, k=top_k)
    
    def _hybrid_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Hybrid search using both vector search and BM25"""
        # Get all items for BM25
        all_items = self.vector_store.get_all_items()
        
        if not all_items:
            logger.warning("No items in vector store for hybrid search")
            return []
        
        # Prepare documents for BM25
        texts = [self.vector_store._get_item_text(item) for item in all_items]
        metadatas = [{"index": i} for i in range(len(all_items))]
        
        # Initialize BM25 retriever
        bm25_retriever = BM25Retriever.from_texts(texts=texts, metadatas=metadatas)
        bm25_retriever.k = top_k
        
        # Create vector search retriever
        vector_search_results = self.vector_store.search(query, k=top_k)
        
        # Combine results from both retrievers
        bm25_results_raw = bm25_retriever.get_relevant_documents(query)
        bm25_results = []
        
        # Convert BM25 results to same format as vector results
        for doc in bm25_results_raw:
            idx = doc.metadata.get("index")
            if idx is not None and 0 <= idx < len(all_items):
                item = all_items[idx].copy()
                # Add BM25 score
                item['score'] = 0.5  # Default score for BM25
                bm25_results.append(item)
        
        # Merge results
        return self._merge_search_results(vector_search_results, bm25_results, top_k)
    
    def _merge_search_results(self, 
                              vector_results: List[Dict[str, Any]], 
                              bm25_results: List[Dict[str, Any]],
                              top_k: int) -> List[Dict[str, Any]]:
        """Merge and deduplicate results from different search methods"""
        # Initialize dictionary to store combined results
        combined = {}  
        
        # Process vector results
        for item in vector_results:
            if "id" in item:
                item_id = str(item["id"])
                if item_id not in combined:
                    combined[item_id] = item
                else:
                    # If item exists, take the higher score
                    if item.get("score", 0) > combined[item_id].get("score", 0):
                        combined[item_id] = item
        
        # Process BM25 results
        for item in bm25_results:
            if "id" in item:
                item_id = str(item["id"])
                if item_id not in combined:
                    combined[item_id] = item
                else:
                    # Boost score for items found by both methods
                    combined[item_id]["score"] = combined[item_id].get("score", 0) * 1.2
        
        # Convert to list and sort by score
        results = list(combined.values())
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return results[:top_k]
    
    def _apply_filters(self, 
                      results: List[Dict[str, Any]], 
                      brand_filter: Optional[str] = None,
                      category_filter: Optional[str] = None,
                      price_range: Optional[Tuple[float, float]] = None) -> List[Dict[str, Any]]:
        """
        Apply filter conditions
        
        Args:
            results: Initial search results
            brand_filter: Brand filter
            category_filter: Category filter
            price_range: Price range (min, max)
            
        Returns:
            Filtered results
        """
        filtered = results.copy()
        
        # Apply brand filter
        if brand_filter:
            brand_filter = brand_filter.lower()
            filtered = [item for item in filtered if item.get("brand", "").lower() == brand_filter]
        
        # Apply category filter
        if category_filter:
            category_filter = category_filter.lower()
            filtered = [item for item in filtered if item.get("category", "").lower() == category_filter]
        
        # Apply price range filter
        if price_range and len(price_range) == 2:
            min_price, max_price = price_range
            filtered = [
                item for item in filtered 
                if "price" in item and isinstance(item["price"], (int, float)) and
                min_price <= item["price"] <= max_price
            ]
        
        return filtered
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze user query, extract key information
        
        Args:
            query: User query
            
        Returns:
            Query analysis result
        """
        # Identify brands
        brands = self._extract_brands(query)
        
        # Identify categories
        categories = self._extract_categories(query)
        
        # Identify price range
        price_range = self._extract_price_range(query)
        
        return {
            "original_query": query,
            "brands": brands,
            "categories": categories,
            "price_range": price_range,
            "has_brand_filter": len(brands) > 0,
            "has_category_filter": len(categories) > 0,
            "has_price_filter": price_range is not None
        }
    
    def _extract_brands(self, query: str) -> List[str]:
        """Extract brands from query"""
        # Common luxury brands list
        luxury_brands = [
            "Chanel", "Louis Vuitton", "Gucci", "Hermes", "Hermès", "Prada", "Dior", 
            "Balenciaga", "Fendi", "Celine", "Céline", "Burberry", "Valentino",
            "Bottega Veneta", "Saint Laurent", "Yves Saint Laurent", "YSL",
            "Givenchy", "Versace", "Jimmy Choo", "Alexander McQueen",
            "Loewe", "Christian Louboutin", "Miu Miu", "Tiffany", "Cartier",
            "Rolex", "Omega", "Patek Philippe", "Audemars Piguet", "TAG Heuer",
            "Breitling", "Hublot", "IWC", "Jaeger-LeCoultre", "Longines",
            "Montblanc", "Bvlgari", "Bulgari", "Van Cleef & Arpels", "Chopard"
        ]
        
        found_brands = []
        query_lower = query.lower()
        
        for brand in luxury_brands:
            if brand.lower() in query_lower:
                found_brands.append(brand)
        
        return found_brands
    
    def _extract_categories(self, query: str) -> List[str]:
        """Extract categories from query"""
        # Common luxury item categories
        categories = {
            "bag": ["bag", "handbag", "purse", "tote", "clutch", "backpack", "satchel", "crossbody"],
            "wallet": ["wallet", "cardholder", "card case", "coin purse"],
            "watch": ["watch", "timepiece", "chronograph", "wristwatch"],
            "jewelry": ["jewelry", "jewellery", "necklace", "bracelet", "ring", "earring", "brooch"],
            "shoes": ["shoes", "sneakers", "heels", "boots", "sandals", "loafers", "pumps"],
            "clothing": ["clothing", "dress", "jacket", "coat", "shirt", "blouse", "sweater", "t-shirt", "jeans", "pants", "skirt"],
            "accessory": ["accessory", "scarf", "belt", "sunglasses", "glasses", "hat", "gloves", "keychain"]
        }
        
        found_categories = []
        query_lower = query.lower()
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in query_lower:
                    found_categories.append(category)
                    break
        
        return list(set(found_categories))  # Remove duplicates
    
    def _extract_price_range(self, query: str) -> Optional[Tuple[float, float]]:
        """Extract price range from query"""
        # Try to extract price range
        # Examples: "$1000-2000", "1000 to 2000 dollars", "under $500", "over $1000", etc.
        
        # Match range (e.g., "$1000-2000", "1000-2000", "1000 to 2000")
        range_pattern = r'(\$?\d+[\.,]?\d*)\s*-|to\s*(\$?\d+[\.,]?\d*)'
        range_matches = re.findall(range_pattern, query)
        if range_matches and len(range_matches) >= 2:
            try:
                # Extract two numbers
                num1 = float(re.sub(r'[^\d.]', '', range_matches[0][0] or range_matches[0][1]))
                num2 = float(re.sub(r'[^\d.]', '', range_matches[1][0] or range_matches[1][1]))
                return (min(num1, num2), max(num1, num2))
            except:
                pass
        
        # Match "under/below X" (e.g., "under $500", "below 1000")
        under_pattern = r'under|below\s+\$?(\d+[\.,]?\d*)'
        under_matches = re.findall(under_pattern, query)
        if under_matches:
            try:
                max_price = float(re.sub(r'[^\d.]', '', under_matches[0]))
                return (0, max_price)
            except:
                pass
        
        # Match "over/above X" (e.g., "over $1000", "above 2000")
        over_pattern = r'over|above\s+\$?(\d+[\.,]?\d*)'
        over_matches = re.findall(over_pattern, query)
        if over_matches:
            try:
                min_price = float(re.sub(r'[^\d.]', '', over_matches[0]))
                return (min_price, float('inf'))
            except:
                pass
        
        return None
    
    def get_similar_items(self, item_id: str, top_k: int = 5, use_reranker: bool = True) -> List[Dict[str, Any]]:
        """
        Get similar items to a specified item
        
        Args:
            item_id: Item ID
            top_k: Number of results to return
            use_reranker: Whether to use reranker for result refinement
            
        Returns:
            List of similar items
        """
        # Try to find the item in the vector store
        items = self.vector_store.get_all_items()
        target_item = None
        
        for item in items:
            if str(item.get("id", "")) == item_id:
                target_item = item
                break
        
        if not target_item:
            logger.warning(f"Item with ID {item_id} not found")
            return []
        
        # Build query
        query_parts = []
        if "brand" in target_item:
            query_parts.append(target_item["brand"])
        if "model" in target_item:
            query_parts.append(target_item["model"])
        if "category" in target_item:
            query_parts.append(target_item["category"])
        
        query = " ".join(query_parts)
        if not query:
            # If not enough information, use description
            query = target_item.get("description", "")
            
        if not query:
            logger.warning(f"Could not construct query for item {item_id}")
            return []
        
        # Search for similar items using both vector and hybrid search
        try:
            results = self._hybrid_search(query, k=top_k + 5)  # Get more results for filtering
        except Exception as e:
            logger.warning(f"Hybrid search failed, falling back to vector search: {str(e)}")
            results = self._vector_search(query, k=top_k + 5)
        
        # Remove original item
        filtered_results = [item for item in results if str(item.get("id", "")) != item_id]
        
        # Apply reranker if enabled
        if use_reranker and self.reranker and filtered_results:
            try:
                reranked_results = self.reranker.rerank(query, filtered_results, top_k=top_k)
                return reranked_results
            except Exception as e:
                logger.error(f"Reranking failed: {str(e)}", exc_info=True)
                # Continue with filtered results
        
        return filtered_results[:top_k]


def query_luxury_items(query: str, 
                        top_k: int = 5, 
                        brand_filter: Optional[str] = None,
                        category_filter: Optional[str] = None,
                        price_range: Optional[Tuple[float, float]] = None,
                        vector_store_path: str = "vector_store/luxury_items_store",
                        use_hybrid_search: bool = True,
                        use_reranker: bool = True,
                        reranker_type: str = "ensemble") -> Dict[str, Any]:
    """
    Query luxury items information
    
    Args:
        query: User query
        top_k: Number of results to return
        brand_filter: Brand filter
        category_filter: Category filter
        price_range: Price range (min, max)
        vector_store_path: Path to vector store
        use_hybrid_search: Whether to use hybrid search
        use_reranker: Whether to use reranker
        reranker_type: Type of reranker to use (keyword, semantic, ensemble)
        
    Returns:
        Query results
    """
    start_time = time.time()
    
    # Initialize reranker if needed
    reranker = get_reranker(reranker_type) if use_reranker else None
    
    # Initialize retriever
    retriever = LuxuryItemsRetriever(
        vector_store_path=vector_store_path,
        reranker=reranker
    )
    
    # Analyze query
    query_analysis = retriever.analyze_query(query)
    
    # Apply filters
    if not brand_filter and query_analysis["has_brand_filter"]:
        brand_filter = query_analysis["brands"][0]
    
    if not category_filter and query_analysis["has_category_filter"]:
        category_filter = query_analysis["categories"][0]
    
    if not price_range and query_analysis["has_price_filter"]:
        price_range = query_analysis["price_range"]
    
    # Execute retrieval
    results = retriever.search(
        query=query,
        top_k=top_k,
        brand_filter=brand_filter,
        category_filter=category_filter,
        price_range=price_range,
        use_hybrid_search=use_hybrid_search,
        use_reranker=use_reranker
    )
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    return {
        "query": query,
        "results": results,
        "query_analysis": query_analysis,
        "applied_filters": {
            "brand": brand_filter,
            "category": category_filter,
            "price_range": price_range,
            "hybrid_search": use_hybrid_search,
            "reranker": reranker_type if use_reranker else None
        },
        "metadata": {
            "total_results": len(results),
            "elapsed_time": elapsed_time
        }
    }


def query_luxury_items_batch(queries: List[str],
                               top_k: int = 5,
                               brand_filter: Optional[str] = None,
                               category_filter: Optional[str] = None,
                               price_range: Optional[Tuple[float, float]] = None,
                               vector_store_path: str = "vector_store/luxury_items_store",
                               use_hybrid_search: bool = True,
                               use_reranker: bool = True,
                               reranker_type: str = "ensemble") -> Dict[str, Any]:
    """
    Query luxury items with multiple queries in parallel
    
    Args:
        queries: List of user queries
        top_k: Number of results to return per query
        brand_filter: Brand filter
        category_filter: Category filter
        price_range: Price range (min, max)
        vector_store_path: Path to vector store
        use_hybrid_search: Whether to use hybrid search
        use_reranker: Whether to use reranker
        reranker_type: Type of reranker to use (keyword, semantic, ensemble)
        
    Returns:
        Combined query results
    """
    start_time = time.time()
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(
            lambda q: query_luxury_items(
                query=q,
                top_k=top_k,
                brand_filter=brand_filter,
                category_filter=category_filter,
                price_range=price_range,
                vector_store_path=vector_store_path,
                use_hybrid_search=use_hybrid_search,
                use_reranker=use_reranker,
                reranker_type=reranker_type
            ),
            queries
        ))
    
    # Merge results
    merged_results = _merge_query_results(results, top_k)
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    return {
        "queries": queries,
        "results": merged_results,
        "applied_filters": {
            "brand": brand_filter,
            "category": category_filter,
            "price_range": price_range,
            "hybrid_search": use_hybrid_search,
            "reranker": reranker_type if use_reranker else None
        },
        "metadata": {
            "total_results": len(merged_results),
            "elapsed_time": elapsed_time
        }
    }


def _merge_query_results(query_results: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    """
    Merge and deduplicate results from multiple queries
    
    Args:
        query_results: List of query results
        top_k: Maximum number of results to return
        
    Returns:
        Merged results
    """
    # Use dictionary for deduplication based on item ID
    merged = {}
    
    for result in query_results:
        for item in result.get("results", []):
            if "id" in item:
                item_id = str(item["id"])
                if item_id not in merged:
                    merged[item_id] = item
                elif item.get("score", 0) > merged[item_id].get("score", 0):
                    # Keep item with higher score
                    merged[item_id] = item
    
    # Convert to list and sort by score
    results = list(merged.values())
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    return results[:top_k]


def get_similar_items(item_id: str, 
                       top_k: int = 5,
                       vector_store_path: str = "vector_store/luxury_items_store",
                       use_reranker: bool = True,
                       reranker_type: str = "ensemble") -> Dict[str, Any]:
    """
    Get items similar to a specified item
    
    Args:
        item_id: Item ID
        top_k: Number of results to return
        vector_store_path: Path to vector store
        use_reranker: Whether to use reranker
        reranker_type: Type of reranker to use (keyword, semantic, ensemble)
        
    Returns:
        Similar items results
    """
    start_time = time.time()
    
    # Initialize reranker if needed
    reranker = get_reranker(reranker_type) if use_reranker else None
    
    # Initialize retriever
    retriever = LuxuryItemsRetriever(
        vector_store_path=vector_store_path,
        reranker=reranker
    )
    
    # Get similar items
    results = retriever.get_similar_items(
        item_id=item_id, 
        top_k=top_k,
        use_reranker=use_reranker
    )
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    return {
        "item_id": item_id,
        "similar_items": results,
        "metadata": {
            "total_results": len(results),
            "elapsed_time": elapsed_time,
            "reranker": reranker_type if use_reranker else None
        }
    } 