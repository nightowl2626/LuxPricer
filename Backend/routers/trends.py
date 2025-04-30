"""
Router for trend analysis endpoints.

Provides endpoints to get mock trend analysis for:
- Search Trends
- Social Media Mentions
- News Coverage
- Resale Market Trends (different from price estimation)
"""
import datetime
import random
import math
from typing import Dict, List, Tuple

from fastapi import APIRouter, HTTPException, Query

# Note: Assuming models are moved to a shared location, e.g., `app/models.py`
from app.models import (
    SearchTrendsResult, SocialMediaResult, NewsAnalysisResult, ResaleMarketResult,
    TimeSeries, TimeSeriesPoint, SocialMediaMention, NewsArticle, ResaleItem
)

router = APIRouter()

# === Mock Search Trends Analysis ===

@router.get("/trends/search", response_model=SearchTrendsResult, tags=["Trends"])
async def analyze_search_trends_endpoint(
    brand: str = Query(..., description="Luxury brand name"),
    model: str = Query(..., description="Specific product model"),
    timeframe: str = Query("90d", description="Timeframe (e.g., '30d', '90d')")
) -> SearchTrendsResult:
    """
    Mock endpoint to analyze search trends for a luxury brand and model.
    In a real implementation, this would call Google Trends or similar.
    """
    try:
        days = int(timeframe.replace('d', ''))
        if days <= 0 or days > 3650:
            raise ValueError("Invalid timeframe")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timeframe format (e.g., '90d')")

    today = datetime.datetime.now()
    query_data = []
    brand_data = []

    for i in range(days):
        date = (today - datetime.timedelta(days=days-i)).strftime('%Y-%m-%d')
        brand_value = 50 + 30 * random.random() + 10 * math.sin(i/10)
        query_value = brand_value * (0.4 + 0.3 * random.random()) + 5 * math.sin(i/5)
        brand_data.append(TimeSeriesPoint(date=date, value=brand_value))
        query_data.append(TimeSeriesPoint(date=date, value=query_value))

    interest_over_time = [
        TimeSeries(data=query_data, label=f"{brand} {model}"),
        TimeSeries(data=brand_data, label=brand)
    ]

    related_queries = {
        "rising": [
            f"{brand} {model} price", f"{brand} {model} review",
            f"{brand} {model} vs {random.choice(['Chanel', 'LV', 'Gucci'])}",
            f"{brand} {model} authentication", f"how to style {brand} {model}"
        ],
        "top": [
            f"{brand} {model}", f"{brand} {model} price", f"{model} {brand}",
            f"buy {brand} {model}", f"{brand} official"
        ]
    }

    regions = ["US", "CN", "JP", "FR", "UK", "IT", "DE", "KR", "AU", "CA"]
    interest_by_region = {region: round(20 + 80 * random.random(), 1) for region in regions}

    return SearchTrendsResult(
        interest_over_time=interest_over_time,
        related_queries=related_queries,
        interest_by_region=interest_by_region
    )

# === Mock Social Media Analysis ===

@router.get("/trends/social", response_model=SocialMediaResult, tags=["Trends"])
async def analyze_social_media_endpoint(
    brand: str = Query(..., description="Luxury brand name"),
    model: str = Query(..., description="Specific product model"),
    timeframe: str = Query("90d", description="Timeframe (e.g., '30d', '90d')")
) -> SocialMediaResult:
    """
    Mock endpoint to analyze social media trends.
    In a real implementation, this would use social media APIs.
    """
    try:
        days = int(timeframe.replace('d', ''))
        if days <= 0 or days > 3650:
            raise ValueError("Invalid timeframe")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timeframe format (e.g., '90d')")

    today = datetime.datetime.now()
    mention_data = []
    sentiment_data = []

    for i in range(days):
        date = (today - datetime.timedelta(days=days-i)).strftime('%Y-%m-%d')
        mention_value = 100 + 50 * random.random() + 40 * math.sin(i/15)
        sentiment_value = 0.3 + 0.4 * random.random() + 0.2 * math.sin(i/20)
        mention_data.append(TimeSeriesPoint(date=date, value=round(mention_value,1)))
        sentiment_data.append(TimeSeriesPoint(date=date, value=round(sentiment_value, 3)))

    mention_volume_over_time = TimeSeries(data=mention_data, label=f"{brand} {model} mentions")
    sentiment_over_time = TimeSeries(data=sentiment_data, label=f"{brand} {model} sentiment")

    platforms = ["Instagram", "Twitter", "TikTok", "Facebook", "Reddit", "Weibo", "YouTube"]
    top_mentions = []
    snippets = [
        f"Just got my new {brand} {model}! #luxury #fashion",
        f"Is the {brand} {model} worth the hype?",
        f"Comparing the {brand} {model} to competitors.",
        f"Vintage {brand} {model} hunting!",
        f"Disappointed with my {brand} {model}.",
        f"Celebrity spotting: carrying the new {brand} {model}!"
    ]

    for i in range(10):
        platform = random.choice(platforms)
        date = (today - datetime.timedelta(days=random.randint(0, days))).strftime('%Y-%m-%d')
        sentiment = random.uniform(-0.5, 1.0)
        reach = random.randint(100, 10000)
        top_mentions.append(SocialMediaMention(
            platform=platform, date=date, sentiment=round(sentiment, 3),
            reach=reach, content_snippet=random.choice(snippets)
        ))

    top_mentions.sort(key=lambda x: x.reach if x.reach else 0, reverse=True)
    platform_distribution = {platform: random.randint(50, 1000) for platform in platforms}

    return SocialMediaResult(
        mention_volume_over_time=mention_volume_over_time,
        sentiment_over_time=sentiment_over_time,
        top_mentions=top_mentions,
        platform_distribution=platform_distribution
    )

# === Mock News Analysis ===

@router.get("/trends/news", response_model=NewsAnalysisResult, tags=["Trends"])
async def analyze_news_endpoint(
    brand: str = Query(..., description="Luxury brand name"),
    model: str = Query(..., description="Specific product model"),
    timeframe: str = Query("90d", description="Timeframe (e.g., '30d', '90d')")
) -> NewsAnalysisResult:
    """
    Mock endpoint to analyze news coverage.
    In a real implementation, this would use NewsAPI or similar.
    """
    try:
        days = int(timeframe.replace('d', ''))
        if days <= 0 or days > 3650:
            raise ValueError("Invalid timeframe")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timeframe format (e.g., '90d')")

    today = datetime.datetime.now()
    article_data = []
    sentiment_data = []

    for i in range(days):
        date = (today - datetime.timedelta(days=days-i)).strftime('%Y-%m-%d')
        base_volume = 5 + 3 * random.random()
        if i % 30 < 3: base_volume += 15 * random.random()
        if (i % 90) < 7: base_volume += 10 * random.random()
        article_value = base_volume
        sentiment_value = 0.2 + 0.2 * random.random() + 0.3 * math.sin(i/30)
        article_data.append(TimeSeriesPoint(date=date, value=round(article_value, 1)))
        sentiment_data.append(TimeSeriesPoint(date=date, value=round(sentiment_value, 3)))

    article_volume_over_time = TimeSeries(data=article_data, label=f"{brand} {model} articles")
    sentiment_over_time = TimeSeries(data=sentiment_data, label=f"{brand} {model} sentiment")

    sources = ["Vogue", "Elle", "Harper's Bazaar", "WWD", "BoF", "NYT", "Forbes", "Reuters"]
    titles = [
        f"{brand} Introduces New {model} Collection", f"The Rise of {brand}'s {model}",
        f"Celebrity Endorsements Boost {brand} {model}", f"Is {brand}'s {model} Worth It?",
        f"Fashion Week: {brand} Reinvents the {model}", f"{brand} Reports Record Sales for {model}"
    ]
    snippets = [
        f"The luxury house {brand} unveiled its latest {model}...",
        f"Analysts are bullish on {brand} following {model} success...",
        f"The creative director discussed the inspiration behind {model}...",
        f"Influencers spark resurgence of interest in {brand}'s {model}..."
    ]
    top_articles = []

    for i in range(8):
        source = random.choice(sources)
        date = (today - datetime.timedelta(days=random.randint(0, days))).strftime('%Y-%m-%d')
        sentiment = random.uniform(-0.2, 0.8)
        top_articles.append(NewsArticle(
            title=random.choice(titles), source=source, date=date,
            url=f"https://example.com/{brand}/{model}_{i}", sentiment=round(sentiment, 3),
            snippet=random.choice(snippets)
        ))

    top_articles.sort(key=lambda x: x.sentiment, reverse=True)
    source_distribution = {source: random.randint(1, 20) for source in sources}

    return NewsAnalysisResult(
        article_volume_over_time=article_volume_over_time,
        sentiment_over_time=sentiment_over_time,
        top_articles=top_articles,
        source_distribution=source_distribution
    )

# === Mock Resale Market Analysis ===

@router.get("/trends/resale", response_model=ResaleMarketResult, tags=["Trends"])
async def analyze_resale_market_endpoint(
    brand: str = Query(..., description="Luxury brand name"),
    model: str = Query(..., description="Specific product model"),
    timeframe: str = Query("90d", description="Timeframe (e.g., '30d', '90d')")
) -> ResaleMarketResult:
    """
    Mock endpoint to analyze resale market trends (price/volume over time).
    In a real implementation, this would scrape resale platforms.
    """
    try:
        days = int(timeframe.replace('d', ''))
        if days <= 0 or days > 3650:
            raise ValueError("Invalid timeframe")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timeframe format (e.g., '90d')")

    today = datetime.datetime.now()
    price_data = []
    volume_data = []

    base_price = 2000 + random.randint(0, 5000)
    price_trend = 0.001 * (-1 if random.random() < 0.3 else 1)

    for i in range(days):
        date = (today - datetime.timedelta(days=days-i)).strftime('%Y-%m-%d')
        price_value = base_price * (1 + price_trend * i) * (0.95 + 0.1 * random.random())
        volume_value = 10 + 5 * random.random() + 3 * math.sin(i/15)
        price_data.append(TimeSeriesPoint(date=date, value=round(price_value, 2)))
        volume_data.append(TimeSeriesPoint(date=date, value=round(volume_value, 1)))

    price_over_time = TimeSeries(data=price_data, label=f"{brand} {model} avg price")
    volume_over_time = TimeSeries(data=volume_data, label=f"{brand} {model} listings")

    platforms = ["Fashionphile", "Vestiaire Collective", "The RealReal", "Rebag", "StockX"]
    conditions = ["Excellent", "Very Good", "Good", "Fair", "New"]
    sample_listings = []

    for i in range(10):
        platform = random.choice(platforms)
        date = (today - datetime.timedelta(days=random.randint(0, days))).strftime('%Y-%m-%d')
        condition = random.choice(conditions)
        price = base_price * (0.7 + 0.6 * random.random())
        sample_listings.append(ResaleItem(
            platform=platform, price=round(price, 2), condition=condition,
            url=f"https://example.com/{platform}/{brand}_{model}_{i}",
            date_listed=date
        ))

    average_price = sum(item.price for item in sample_listings) / len(sample_listings)
    min_price = min(item.price for item in sample_listings)
    max_price = max(item.price for item in sample_listings)
    price_range = {"min": round(min_price, 2), "max": round(max_price, 2)}

    return ResaleMarketResult(
        price_over_time=price_over_time,
        volume_over_time=volume_over_time,
        average_price=round(average_price, 2),
        price_range=price_range,
        sample_listings=sample_listings
    )

# === Perplexity Trends Analysis ===

@router.get("/trends/perplexity", response_model=dict, tags=["Trends"])
async def analyze_perplexity_trends_endpoint(
    brand: str = Query(..., description="Luxury brand name"),
    model: str = Query(..., description="Specific product model"),
) -> dict:
    """
    Get advanced trend analysis from Perplexity AI for a luxury brand and model.
    This endpoint uses actual API calls to Perplexity to get real-time search data.
    """
    import logging
    logger = logging.getLogger("trends.perplexity")
    
    try:
        # Use our integrated trend fetcher
        from utils.trend_fetcher import fetch_trend_data
        
        # Fetch trend data
        trend_data = fetch_trend_data(brand, model)
        
        if "error" in trend_data:
            logger.error(f"Error fetching trend data: {trend_data['error']}")
            raise HTTPException(status_code=500, detail=f"Error fetching trend data: {trend_data['error']}")
        
        return trend_data
        
    except Exception as e:
        logger.error(f"Error in perplexity trend analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in perplexity trend analysis: {str(e)}")

# === Real-Time Trend Analysis ===

@router.get("/trends/realtime", response_model=dict, tags=["Trends"])
async def analyze_realtime_trends_endpoint(
    brand: str = Query(..., description="Luxury brand name"),
    model: str = Query(..., description="Specific product model"),
    force_refresh: bool = Query(False, description="Force refresh of cached data")
) -> dict:
    """
    Get comprehensive real-time trend analysis for a luxury brand and model.
    This endpoint integrates Perplexity data with trend score calculation to provide actionable insights.
    
    Data is cached to improve performance, but can be refreshed with force_refresh=true.
    """
    import logging
    logger = logging.getLogger("trends.realtime")
    
    try:
        # Use our data loader to get or generate trend data
        from utils.data_loader import get_or_generate_trend_data
        
        # Get trend data (will be cached if already exists)
        if force_refresh:
            logger.info(f"Forcing refresh of trend data for {brand} {model}")
            # Delete cached entry if it exists and generate new data
            from utils.trend_fetcher import get_real_trend_data
            trend_data = get_real_trend_data(brand, model)
            
            # Update the cache
            from utils.data_loader import save_trend_data, get_trend_score_data
            all_trend_data = get_trend_score_data()
            
            # Remove old entry if exists
            all_trend_data = [item for item in all_trend_data 
                            if not (item.get("designer", "").lower() == brand.lower() and 
                                    item.get("model", "").lower() == model.lower())]
        
            # Add new data
            all_trend_data.append(trend_data)
            save_trend_data(all_trend_data)
        else:
            trend_data = get_or_generate_trend_data(brand, model)
        
        if "error" in trend_data:
            logger.error(f"Error with trend data: {trend_data['error']}")
            error_detail = trend_data.get("error", "Unknown error")
            return {
                "status": "error",
                "error": error_detail,
                "designer": brand,
                "model": model,
                "trend_score": 0.5,  # Default value
                "trend_category": "Medium (Default)",
                "generated_at": datetime.datetime.now().isoformat()
            }
        
        # Add some extra metadata
        trend_data["status"] = "success"
        if "generated_at" not in trend_data:
            trend_data["generated_at"] = datetime.datetime.now().isoformat()
            
        return trend_data
        
    except Exception as e:
        logger.error(f"Error in realtime trend analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in realtime trend analysis: {str(e)}") 