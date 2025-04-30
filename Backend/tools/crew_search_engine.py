#!/usr/bin/env python3

import argparse
import sys
import time
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

def load_environment():
    """Load environment variables from .env files in order of precedence"""
    env_files = ['.env.local', '.env', '.env.example']
    for env_file in env_files:
        env_path = Path('.') / env_file
        if env_path.exists():
            logger.info(f"Loading environment from {env_file}")
            load_dotenv(dotenv_path=env_path)
            return
    logger.warning("No .env files found. Using system environment variables only.")

# Load environment variables
load_environment()

def get_api_key(provider="openai"):
    """Get API key for the specified provider."""
    if provider == "openai":
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        return api_key
    elif provider == "anthropic":
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        return api_key
    else:
        raise ValueError(f"Unsupported provider: {provider}")

class SearchTools:
    @tool("Search the web")
    def search_web(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """
        Search the web using DuckDuckGo and return results.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of search results with URL, title, and snippet
        """
        from duckduckgo_search import DDGS
        
        try:
            logger.info(f"Searching for: {query}")
            results = []
            
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(query, max_results=max_results))
                
                if not ddg_results:
                    logger.warning("No results found")
                    return []
                
                for r in ddg_results:
                    results.append({
                        "url": r.get("href", ""),
                        "title": r.get("title", ""),
                        "snippet": r.get("body", "")
                    })
                    
                logger.info(f"Found {len(results)} results")
                return results
                
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
    
    @tool("Fetch news articles")
    def search_news(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Search for news articles using DuckDuckGo News and return results.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of news article results with URL, title, and snippet
        """
        from duckduckgo_search import DDGS
        
        try:
            logger.info(f"Searching news for: {query}")
            results = []
            
            with DDGS() as ddgs:
                news_results = list(ddgs.news(query, max_results=max_results))
                
                if not news_results:
                    logger.warning("No news results found")
                    return []
                
                for r in news_results:
                    results.append({
                        "url": r.get("url", ""),
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "source": r.get("source", ""),
                        "date": r.get("date", "")
                    })
                    
                logger.info(f"Found {len(results)} news results")
                return results
                
        except Exception as e:
            logger.error(f"News search failed: {str(e)}")
            return []

def search(query: str, max_results: int = 10, provider: str = "openai", model: Optional[str] = None) -> str:
    """
    Search the web using CrewAI.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        provider: LLM provider to use
        model: Model name to use (optional)
    
    Returns:
        Formatted search results
    """
    try:
        # Get API key and configure LLM
        api_key = get_api_key(provider)
        
        if not model:
            if provider == "openai":
                model = "gpt-4o"
            elif provider == "anthropic":
                model = "claude-3-7-sonnet-20250219"
            else:
                raise ValueError(f"No default model for provider: {provider}")
        
        # Create tools instance
        search_tools = SearchTools()
        
        # Create search agent
        search_agent = Agent(
            role="Web Researcher",
            goal="Find the most relevant and accurate information from the web",
            backstory="You are a specialized researcher who can find and organize information from the web.",
            verbose=True,
            allow_delegation=False,
            tools=[search_tools.search_web, search_tools.search_news],
            llm_config={
                "api_key": api_key,
                "model": model
            },
            provider=provider
        )
        
        # Create task for the search
        task = Task(
            description=f"""
            Research the following query and provide well-organized results: "{query}"
            
            1. First, search the web for general information
            2. Then, search for recent news articles on the topic
            3. Organize the results in a clear format with URLs, titles, and snippets
            4. Highlight the most relevant information
            """,
            agent=search_agent,
            expected_output="Well-formatted search results with URLs, titles, and snippets organized by relevance."
        )
        
        # Create and run the crew
        crew = Crew(
            agents=[search_agent],
            tasks=[task],
            verbose=1,
            process=Process.sequential
        )
        
        # Start the process
        result = crew.kickoff()
        
        return result
    
    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        return f"Search failed: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="Search using CrewAI")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--max-results", type=int, default=10,
                      help="Maximum number of results (default: 10)")
    parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai",
                      help="LLM provider to use (default: openai)")
    parser.add_argument("--model", type=str, help="Model name (default depends on provider)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    start_time = time.time()
    
    result = search(args.query, args.max_results, args.provider, args.model)
    
    # Print results
    print(result)
    
    logger.info(f"Total search time: {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    main() 