"""
RAG API Module
Provides API interfaces for luxury item information retrieval
"""

from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, Query, HTTPException, Path, Body
from pydantic import BaseModel, Field
import time
import logging

from services.rag.query import query_luxury_items, get_similar_items, query_luxury_items_batch

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/rag", tags=["RAG"])

# Request models
class QueryRequest(BaseModel):
    query: str = Field(..., description="User query")
    top_k: int = Field(5, description="Number of results to return")
    brand_filter: Optional[str] = Field(None, description="Brand filter")
    category_filter: Optional[str] = Field(None, description="Category filter")
    min_price: Optional[float] = Field(None, description="Minimum price")
    max_price: Optional[float] = Field(None, description="Maximum price")
    use_hybrid_search: bool = Field(True, description="Use hybrid search (vector + BM25)")
    use_reranker: bool = Field(True, description="Use reranker for result refinement")
    reranker_type: str = Field("ensemble", description="Type of reranker (keyword, semantic, ensemble)")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "vintage Chanel bag in black leather",
                "top_k": 5,
                "brand_filter": "Chanel",
                "category_filter": "bag",
                "min_price": 1000,
                "max_price": 5000,
                "use_hybrid_search": True,
                "use_reranker": True,
                "reranker_type": "ensemble"
            }
        }

class BatchQueryRequest(BaseModel):
    queries: List[str] = Field(..., description="List of user queries")
    top_k: int = Field(5, description="Number of results to return per query")
    brand_filter: Optional[str] = Field(None, description="Brand filter")
    category_filter: Optional[str] = Field(None, description="Category filter")
    min_price: Optional[float] = Field(None, description="Minimum price")
    max_price: Optional[float] = Field(None, description="Maximum price")
    use_hybrid_search: bool = Field(True, description="Use hybrid search (vector + BM25)")
    use_reranker: bool = Field(True, description="Use reranker for result refinement")
    reranker_type: str = Field("ensemble", description="Type of reranker (keyword, semantic, ensemble)")
    
    class Config:
        schema_extra = {
            "example": {
                "queries": ["vintage Chanel bag", "Chanel flap bag black"],
                "top_k": 5,
                "brand_filter": "Chanel",
                "category_filter": "bag",
                "min_price": 1000,
                "max_price": 5000,
                "use_hybrid_search": True,
                "use_reranker": True,
                "reranker_type": "ensemble"
            }
        }

class SimilarItemsRequest(BaseModel):
    item_id: str = Field(..., description="Item ID")
    top_k: int = Field(5, description="Number of results to return")
    use_reranker: bool = Field(True, description="Use reranker for result refinement")
    reranker_type: str = Field("ensemble", description="Type of reranker (keyword, semantic, ensemble)")
    
    class Config:
        schema_extra = {
            "example": {
                "item_id": "12345",
                "top_k": 5,
                "use_reranker": True,
                "reranker_type": "ensemble"
            }
        }

# Response models
class LuxuryItem(BaseModel):
    id: Optional[str] = Field(None, description="Item ID")
    brand: Optional[str] = Field(None, description="Brand")
    model: Optional[str] = Field(None, description="Model")
    category: Optional[str] = Field(None, description="Category")
    price: Optional[Union[float, str]] = Field(None, description="Price")
    description: Optional[str] = Field(None, description="Description")
    materials: Optional[List[str]] = Field(None, description="Materials")
    features: Optional[List[str]] = Field(None, description="Features")
    image_url: Optional[str] = Field(None, description="Image URL")
    score: Optional[float] = Field(None, description="Match score")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class QueryAnalysis(BaseModel):
    original_query: str = Field(..., description="Original query")
    brands: List[str] = Field([], description="Identified brands")
    categories: List[str] = Field([], description="Identified categories")
    has_brand_filter: bool = Field(False, description="Contains brand filter")
    has_category_filter: bool = Field(False, description="Contains category filter")
    has_price_filter: bool = Field(False, description="Contains price filter")

class QueryResponse(BaseModel):
    query: str = Field(..., description="User query")
    results: List[LuxuryItem] = Field([], description="Query results")
    query_analysis: QueryAnalysis = Field(..., description="Query analysis")
    applied_filters: Dict[str, Any] = Field({}, description="Applied filters")
    metadata: Dict[str, Any] = Field({}, description="Metadata")

class BatchQueryResponse(BaseModel):
    queries: List[str] = Field(..., description="User queries")
    results: List[LuxuryItem] = Field([], description="Query results")
    applied_filters: Dict[str, Any] = Field({}, description="Applied filters")
    metadata: Dict[str, Any] = Field({}, description="Metadata")

class SimilarItemsResponse(BaseModel):
    item_id: str = Field(..., description="Item ID")
    similar_items: List[LuxuryItem] = Field([], description="Similar items")
    metadata: Dict[str, Any] = Field({}, description="Metadata")


@router.post("/query", response_model=QueryResponse, summary="Query luxury items information")
async def search_luxury_items(request: QueryRequest):
    """
    Retrieve luxury items information based on user query
    
    - **query**: User query
    - **top_k**: Number of results to return
    - **brand_filter**: Brand filter
    - **category_filter**: Category filter
    - **min_price**: Minimum price
    - **max_price**: Maximum price
    - **use_hybrid_search**: Whether to use hybrid search (vector + BM25)
    - **use_reranker**: Whether to use reranker for result refinement
    - **reranker_type**: Type of reranker (keyword, semantic, ensemble)
    """
    try:
        # Build price range
        price_range = None
        if request.min_price is not None or request.max_price is not None:
            min_price = request.min_price if request.min_price is not None else 0
            max_price = request.max_price if request.max_price is not None else float('inf')
            price_range = (min_price, max_price)
        
        # Execute query
        results = query_luxury_items(
            query=request.query,
            top_k=request.top_k,
            brand_filter=request.brand_filter,
            category_filter=request.category_filter,
            price_range=price_range,
            use_hybrid_search=request.use_hybrid_search,
            use_reranker=request.use_reranker,
            reranker_type=request.reranker_type
        )
        
        return results
    except Exception as e:
        logger.error(f"Error in search_luxury_items: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post("/batch_query", response_model=BatchQueryResponse, summary="Batch query luxury items")
async def batch_search_luxury_items(request: BatchQueryRequest):
    """
    Retrieve luxury items information based on multiple user queries
    
    - **queries**: List of user queries
    - **top_k**: Number of results to return per query
    - **brand_filter**: Brand filter
    - **category_filter**: Category filter
    - **min_price**: Minimum price
    - **max_price**: Maximum price
    - **use_hybrid_search**: Whether to use hybrid search (vector + BM25)
    - **use_reranker**: Whether to use reranker for result refinement
    - **reranker_type**: Type of reranker (keyword, semantic, ensemble)
    """
    try:
        # Build price range
        price_range = None
        if request.min_price is not None or request.max_price is not None:
            min_price = request.min_price if request.min_price is not None else 0
            max_price = request.max_price if request.max_price is not None else float('inf')
            price_range = (min_price, max_price)
        
        # Execute batch query
        results = query_luxury_items_batch(
            queries=request.queries,
            top_k=request.top_k,
            brand_filter=request.brand_filter,
            category_filter=request.category_filter,
            price_range=price_range,
            use_hybrid_search=request.use_hybrid_search,
            use_reranker=request.use_reranker,
            reranker_type=request.reranker_type
        )
        
        return results
    except Exception as e:
        logger.error(f"Error in batch_search_luxury_items: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch query failed: {str(e)}")


@router.post("/similar", response_model=SimilarItemsResponse, summary="Get similar items")
async def find_similar_items(request: SimilarItemsRequest):
    """
    Find items similar to a specified item
    
    - **item_id**: Item ID
    - **top_k**: Number of results to return
    - **use_reranker**: Whether to use reranker for result refinement
    - **reranker_type**: Type of reranker (keyword, semantic, ensemble)
    """
    try:
        # Execute similar items query
        results = get_similar_items(
            item_id=request.item_id,
            top_k=request.top_k,
            use_reranker=request.use_reranker,
            reranker_type=request.reranker_type
        )
        
        return results
    except Exception as e:
        logger.error(f"Error in find_similar_items: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Similar items query failed: {str(e)}")


@router.get("/health", summary="Health check")
async def health_check():
    """
    Check RAG system health status
    """
    return {
        "status": "healthy",
        "timestamp": time.time()
    } 