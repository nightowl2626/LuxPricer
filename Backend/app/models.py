from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union, Any

class AnalysisType(str, Enum):
    """Enum for supported analysis types"""
    SEARCH_TRENDS = "search_trends"
    SOCIAL_MEDIA = "social_media"
    NEWS_ANALYSIS = "news_analysis"
    RESALE_MARKET = "resale_market"
    ALL = "all"

class AnalysisRequest(BaseModel):
    """Request model for luxury brand trend analysis"""
    brand: str = Field(..., description="Luxury brand name (e.g., 'Chanel', 'Louis Vuitton')")
    model: str = Field(..., description="Specific product model (e.g., 'Classic Flap', 'Neverfull')")
    analysis_types: List[AnalysisType] = Field(
        default=[AnalysisType.ALL],
        description="Types of analysis to perform"
    )
    timeframe: str = Field(
        default="90d", 
        description="Timeframe for analysis in days (e.g., '30d', '90d', '365d')"
    )

class TimeSeriesPoint(BaseModel):
    """A single data point in a time series"""
    date: str
    value: float

class TimeSeries(BaseModel):
    """Time series data structure"""
    data: List[TimeSeriesPoint]
    label: str
    
class SearchTrendsResult(BaseModel):
    """Results from search trends analysis"""
    interest_over_time: List[TimeSeries]
    related_queries: Dict[str, List[str]]
    interest_by_region: Dict[str, float]

class SocialMediaMention(BaseModel):
    """A social media mention"""
    platform: str
    date: str
    sentiment: float
    reach: Optional[int] = None
    content_snippet: Optional[str] = None

class SocialMediaResult(BaseModel):
    """Results from social media analysis"""
    mention_volume_over_time: TimeSeries
    sentiment_over_time: TimeSeries
    top_mentions: List[SocialMediaMention]
    platform_distribution: Dict[str, int]

class NewsArticle(BaseModel):
    """A news article"""
    title: str
    source: str
    date: str
    url: str
    sentiment: float
    snippet: str

class NewsAnalysisResult(BaseModel):
    """Results from news analysis"""
    article_volume_over_time: TimeSeries
    sentiment_over_time: TimeSeries
    top_articles: List[NewsArticle]
    source_distribution: Dict[str, int]

class ResaleItem(BaseModel):
    """A resale marketplace item"""
    platform: str
    price: float
    condition: Optional[str] = None
    url: Optional[str] = None
    date_listed: Optional[str] = None

class ResaleMarketResult(BaseModel):
    """Results from resale market analysis"""
    price_over_time: TimeSeries
    volume_over_time: TimeSeries
    average_price: float
    price_range: Dict[str, float]
    sample_listings: List[ResaleItem]

class AnalysisResponse(BaseModel):
    """Complete response for trend analysis"""
    brand: str
    model: str
    timeframe: str
    search_trends: Optional[SearchTrendsResult] = None
    social_media: Optional[SocialMediaResult] = None
    news_analysis: Optional[NewsAnalysisResult] = None
    resale_market: Optional[ResaleMarketResult] = None
    summary: str 