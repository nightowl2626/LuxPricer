#!/usr/bin/env python3

import asyncio
import argparse
import sys
import os
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv
import time
import logging
from urllib.parse import urlparse

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

def validate_url(url: str) -> bool:
    """Validate if the given string is a valid URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

class WebTools:
    @tool("Fetch webpage content")
    def fetch_webpage(self, url: str) -> str:
        """
        Fetches the content of a webpage and returns it as text.
        
        Args:
            url: The URL of the webpage to fetch
            
        Returns:
            The text content of the webpage
        """
        import requests
        from bs4 import BeautifulSoup
        
        try:
            # Check if URL is valid
            if not validate_url(url):
                return f"Invalid URL: {url}"
                
            # Send request with appropriate headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "meta", "noscript", "header", "footer", "nav"]):
                script.extract()
                
            # Get text
            text = soup.get_text(separator='\n')
            
            # Clean up text - remove excess whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Limit to a reasonable size
            if len(text) > 15000:
                text = text[:15000] + "...\n[Content truncated due to length]"
                
            return f"Content from {url}:\n\n{text}"
            
        except requests.exceptions.RequestException as e:
            return f"Error fetching {url}: {str(e)}"
        except Exception as e:
            return f"Error processing {url}: {str(e)}"

def scrape_webpages(urls: List[str], provider="openai", model=None) -> List[str]:
    """
    Scrape a list of webpages using CrewAI.
    
    Args:
        urls: List of URLs to scrape
        provider: LLM provider to use
        model: Model name to use (optional)
        
    Returns:
        List of scraped content
    """
    # Validate URLs
    valid_urls = []
    for url in urls:
        if validate_url(url):
            valid_urls.append(url)
        else:
            logger.error(f"Invalid URL: {url}")
    
    if not valid_urls:
        logger.error("No valid URLs provided")
        return []
    
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
        web_tools = WebTools()
        
        # Create web scraper agent
        scraper_agent = Agent(
            role="Web Scraper",
            goal="Extract and summarize content from webpages accurately",
            backstory="You are a specialized web scraper that can extract the most important information from websites.",
            verbose=True,
            allow_delegation=False,
            tools=[web_tools.fetch_webpage],
            llm_config={
                "api_key": api_key,
                "model": model
            },
            provider=provider
        )
        
        # Create tasks for each URL
        tasks = []
        for url in valid_urls:
            task = Task(
                description=f"Fetch and extract the main content from {url}. Focus on the most important information and remove any noise or irrelevant content.",
                agent=scraper_agent,
                expected_output="The extracted and cleaned content from the webpage, focusing on the main text and important information."
            )
            tasks.append(task)
        
        # Create and run the crew
        crew = Crew(
            agents=[scraper_agent],
            tasks=tasks,
            verbose=1,
            process=Process.sequential
        )
        
        # Start the process
        results = crew.kickoff()
        
        return results
    
    except Exception as e:
        logger.error(f"Error during web scraping: {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(description='Fetch and extract text content from webpages using CrewAI.')
    parser.add_argument('urls', nargs='+', help='URLs to process')
    parser.add_argument('--provider', choices=['openai', 'anthropic'], default='openai', 
                       help='The LLM provider to use')
    parser.add_argument('--model', type=str, help='The model to use (default depends on provider)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    start_time = time.time()
    
    results = scrape_webpages(args.urls, args.provider, args.model)
    
    # Print results
    for i, result in enumerate(results):
        print(f"\n=== Results for URL {i+1}: {args.urls[i]} ===")
        print(result)
        print("=" * 80)
    
    logger.info(f"Total processing time: {time.time() - start_time:.2f}s")

if __name__ == '__main__':
    main() 