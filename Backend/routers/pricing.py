"""
Router for pricing estimation endpoints.
Provides endpoints for basic and advanced price estimation.
"""
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

from utils.data_loader import get_listings_data, get_trend_score_data
from utils.pricing_logic import estimate_price

router = APIRouter()

# --- Request Models --- #

class PriceEstimationRequest(BaseModel):
    designer: str = Field(..., description="Brand/designer name (e.g., 'Gucci')")
    model: str = Field(..., description="Product model name (e.g., 'Horsebit 1955')")
    condition_rating: Optional[str] = Field(None, description="Condition description (e.g., 'Very Good', 'Excellent')")
    size: Optional[str] = Field(None, description="Size (e.g., 'Medium')")
    material: Optional[str] = Field(None, description="Material (e.g., 'Leather')")
    color: Optional[str] = Field(None, description="Color (e.g., 'Brown')")
    year: Optional[int] = Field(None, description="Year of production (e.g., 2020)")
    # Add other relevant fields like inclusions if needed later

# --- API Endpoints --- #

@router.post("/price/estimate", tags=["Pricing"], summary="Price Estimation")
async def get_price_estimation(
    request: PriceEstimationRequest = Body(...)
) -> Dict[str, Any]:
    """
    Provides a comprehensive price estimate using similarity-weighted average 
    of comparable listings, considering all available item details.
    Applies condition, trend, and variance factors.
    """
    target_item_raw = request.model_dump(exclude_none=True)
    print(f"Received price estimation request for: {target_item_raw}")
    
    # Construct formatted target item for pricing algorithm
    target_item = {
        "designer": target_item_raw.get("designer"),
        "model": target_item_raw.get("model"),
        "condition_rating": target_item_raw.get("condition_rating"),
        "item_details": {
            "size": target_item_raw.get("size"),
            "material": target_item_raw.get("material"),
            "color": target_item_raw.get("color")
        }
    }
    
    if "year" in target_item_raw:
        target_item["item_details"]["year"] = target_item_raw["year"]

    # Load necessary data
    listings_data = get_listings_data()
    trends_data = get_trend_score_data()

    if not listings_data:
        raise HTTPException(status_code=503, detail="Listing data unavailable. Cannot perform price estimation.")
    if not trends_data:
        print("Warning: Trend score data unavailable. Proceeding with default trend score.")

    estimation_result = estimate_price(target_item, listings_data, trends_data)

    if estimation_result is None or "error" in estimation_result:
        error_detail = estimation_result.get("error") if estimation_result else "Price estimation failed due to insufficient data or internal error."
        status_code = 404 if "Insufficient" in error_detail else 500
        print(f"Price estimation failed: {error_detail}")
        # Add extra info if available
        extra_info = {k: v for k, v in estimation_result.items() if k != 'error'} if estimation_result else {}
        raise HTTPException(status_code=status_code, detail={"message": error_detail, **extra_info})

    print(f"Price estimation successful: {estimation_result.get('estimated_price')}")
    return estimation_result

# Legacy endpoints for backward compatibility, redirecting to unified price estimation

@router.post("/price/basic", tags=["Pricing"], summary="Basic Price Estimation (Legacy)")
async def get_basic_price_estimation(
    request: PriceEstimationRequest = Body(...)
) -> Dict[str, Any]:
    """
    [LEGACY] Provides a basic price estimate. 
    This endpoint is maintained for backward compatibility and redirects to the main price estimation.
    """
    return await get_price_estimation(request)

@router.post("/price/advanced", tags=["Pricing"], summary="Advanced Price Estimation (Legacy)")
async def get_advanced_price_estimation(
    request: PriceEstimationRequest = Body(...)
) -> Dict[str, Any]:
    """
    [LEGACY] Provides an advanced price estimate.
    This endpoint is maintained for backward compatibility and redirects to the main price estimation.
    """
    return await get_price_estimation(request) 