"""
Pricing estimation logic for luxury goods.
Contains functions for estimating the price of luxury items.
"""

import logging
import statistics
from typing import Dict, Any, List, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def estimate_price(item: Dict[str, Any], trend_score: Optional[float] = None) -> Dict[str, Any]:
    """
    Estimate the price of a luxury item based on brand, model, and other factors
    
    Args:
        item: Dictionary containing item details (brand, model, condition, etc.)
        trend_score: Optional market trend score (0-1)
        
    Returns:
        Dictionary with price estimation results
    """
    logger.info(f"Estimating price for item: {item.get('brand', '')} {item.get('model', '')}")
    
    try:
        # Extract brand/designer
        brand = item.get('brand', '')
        if not brand:
            brand = item.get('designer', '')
            
        # Extract model/style
        model = item.get('model', '')
        if not model:
            model = item.get('style', '')
            
        if not brand or not model:
            return {
                "error": "Missing brand or model information",
                "estimated_price": 0,
                "confidence": "none"
            }
        
        # Mock data - in a real system, this would be a database lookup
        # based on the brand and model
        base_prices = {
            "chanel": {
                "classic flap": 8800,
                "boy bag": 5200,
                "2.55": 7000,
                "gabrielle": 4200,
                "wallet on chain": 2750,
            },
            "louis vuitton": {
                "neverfull": 1540,
                "speedy": 1200,
                "pochette metis": 2030,
                "alma": 1620,
                "keepall": 1990,
            },
            "hermes": {
                "birkin": 12000,
                "kelly": 10000,
                "constance": 7800,
                "garden party": 3700,
                "lindy": 7800,
            },
            "gucci": {
                "marmont": 2300,
                "dionysus": 2150,
                "ophidia": 1200,
                "bamboo": 2800,
                "jackie": 1980,
            },
            "dior": {
                "lady dior": 5300,
                "saddle": 3800,
                "book tote": 3200,
                "diorama": 3400,
                "montaigne": 3500,
            },
            "prada": {
                "galleria": 2700,
                "cahier": 3100,
                "nylon backpack": 1690,
                "double bag": 3200,
                "re-edition": 1200,
            },
            "celine": {
                "luggage": 2900,
                "belt bag": 2500,
                "trio": 1150,
                "box": 4350,
                "phantom": 2200,
            },
            "bottega veneta": {
                "cassette": 3800,
                "pouch": 2800,
                "arco": 2800,
                "jodie": 2250,
                "veneta": 2100,
            },
            "fendi": {
                "baguette": 2950,
                "peekaboo": 4550,
                "by the way": 1750,
                "kan i": 2490,
                "sunshine shopper": 2290,
            },
            "balenciaga": {
                "city": 1950,
                "hourglass": 2250,
                "neo classic": 2090,
                "le cagole": 2300,
                "motorcycle": 1850,
            },
            "cartier": {
                "love bracelet": 6900,
                "juste un clou": 7250,
                "trinity ring": 1320,
                "panthere watch": 4000,
                "santos watch": 7000,
            },
            "rolex": {
                "submariner": 9150,
                "datejust": 7050,
                "daytona": 14550,
                "gmt master": 10750,
                "day date": 36550,
            },
            "omega": {
                "speedmaster": 6300,
                "seamaster": 5200,
                "constellation": 5900,
                "de ville": 4900,
                "aqua terra": 5700,
            },
            "patek philippe": {
                "nautilus": 34000,
                "calatrava": 23000,
                "aquanaut": 21000,
                "grand complications": 80000,
                "twenty~4": 13000,
            },
            "audemars piguet": {
                "royal oak": 32000,
                "royal oak offshore": 45000,
                "code 11.59": 26000,
                "millenary": 28000,
                "jules audemars": 25000,
            }
        }
        
        # Condition adjustments (default to 1.0 - no adjustment)
        condition_adjustments = {
            "new": 1.1,      # 10% premium for new
            "excellent": 1.0, # No adjustment for excellent condition
            "very good": 0.9, # 10% reduction for very good
            "good": 0.75,     # 25% reduction for good
            "fair": 0.6,      # 40% reduction for fair
            "poor": 0.4       # 60% reduction for poor
        }
        
        # Extract relevant data
        brand_lower = brand.lower()
        model_lower = model.lower()
        
        # Get condition
        condition = item.get('condition', 'excellent').lower()
        # Map various condition terms to standard ones
        condition_mapping = {
            'mint': 'new',
            'pristine': 'new',
            'brand new': 'new',
            'like new': 'excellent',
            'near mint': 'excellent',
            'very good': 'very good',
            'used': 'good',
            'normal wear': 'good',
            'worn': 'good',
            'fair': 'fair',
            'acceptable': 'fair',
            'poor': 'poor',
            'damaged': 'poor',
            'for parts': 'poor'
        }
        
        # Map condition to standard rating
        standardized_condition = 'excellent'  # Default
        for key, value in condition_mapping.items():
            if key in condition:
                standardized_condition = value
                break
        
        # Lookup base price
        base_price = None
        confidence = "low"
        price_range = {"min": 0, "max": 0}
        
        # Get basic price data from the lookup 
        if brand_lower in base_prices:
            brand_data = base_prices[brand_lower]
            
            # Exact match
            if model_lower in brand_data:
                base_price = brand_data[model_lower]
                confidence = "high"
                price_range = {
                    "min": int(base_price * 0.85),
                    "max": int(base_price * 1.15)
                }
            else:
                # Fuzzy match - if model string contains any key from the brand data
                matches = {}
                for model_key, price in brand_data.items():
                    if model_key in model_lower or model_lower in model_key:
                        matches[model_key] = price
                
                if matches:
                    # Take average if multiple matches
                    base_price = sum(matches.values()) / len(matches)
                    confidence = "medium"
                    price_range = {
                        "min": int(base_price * 0.75),
                        "max": int(base_price * 1.25)
                    }
                else:
                    # No match - use average price for the brand
                    base_price = sum(brand_data.values()) / len(brand_data)
                    confidence = "low"
                    price_range = {
                        "min": int(base_price * 0.6),
                        "max": int(base_price * 1.4)
                    }
        else:
            # Brand not found - use fallback average
            all_prices = [price for brand_dict in base_prices.values() for price in brand_dict.values()]
            base_price = sum(all_prices) / len(all_prices)
            confidence = "very low"
            price_range = {
                "min": int(base_price * 0.5),
                "max": int(base_price * 1.5)
            }
        
        # Apply condition adjustment
        condition_factor = condition_adjustments.get(standardized_condition, 1.0)
        adjusted_price = base_price * condition_factor
        
        # Apply trend adjustment if provided
        if trend_score is not None:
            # Map 0-1 trend score to factor range (0.85 to 1.15)
            trend_factor = 0.85 + (trend_score * 0.3)  # 0 -> 0.85, 1 -> 1.15
            logger.info(f"Applying trend factor: {trend_factor} (score: {trend_score})")
            adjusted_price *= trend_factor
            price_range["min"] = int(price_range["min"] * trend_factor)
            price_range["max"] = int(price_range["max"] * trend_factor)
        
        # Round to the nearest 10
        final_price = round(adjusted_price / 10) * 10
        
        # Prepare result
        result = {
            "estimated_price": final_price,
            "price_range": price_range,
            "confidence": confidence,
            "condition_adjusted": standardized_condition,
            "condition_factor": condition_factor,
            "base_price": int(base_price),
        }
        
        if trend_score is not None:
            result["trend_score"] = trend_score
            result["trend_factor"] = trend_factor
        
        logger.info(f"Estimated price: ${final_price} ({confidence} confidence)")
        return result
    
    except Exception as e:
        logger.error(f"Error in price estimation: {str(e)}")
        return {
            "error": str(e),
            "estimated_price": 0,
            "confidence": "error"
        } 