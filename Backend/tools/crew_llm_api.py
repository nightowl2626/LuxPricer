#!/usr/bin/env python3

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any

from crewai import Agent, Task, Crew, Process
from crewai.tasks.task_output import TaskOutput

def load_environment():
    """Load environment variables from .env files in order of precedence"""
    # Order of precedence:
    # 1. System environment variables (already loaded)
    # 2. .env.local (user-specific overrides)
    # 3. .env (project defaults)
    # 4. .env.example (example configuration)
    
    env_files = ['.env.local', '.env', '.env.example']
    env_loaded = False
    
    print("Current working directory:", Path('.').absolute(), file=sys.stderr)
    print("Looking for environment files:", env_files, file=sys.stderr)
    
    for env_file in env_files:
        env_path = Path('.') / env_file
        print(f"Checking {env_path.absolute()}", file=sys.stderr)
        if env_path.exists():
            print(f"Found {env_file}, loading variables...", file=sys.stderr)
            load_dotenv(dotenv_path=env_path)
            env_loaded = True
            print(f"Loaded environment variables from {env_file}", file=sys.stderr)
            # Print loaded keys (but not values for security)
            with open(env_path) as f:
                keys = [line.split('=')[0].strip() for line in f if '=' in line and not line.startswith('#')]
                print(f"Keys loaded from {env_file}: {keys}", file=sys.stderr)
    
    if not env_loaded:
        print("Warning: No .env files found. Using system environment variables only.", file=sys.stderr)
        print("Available system environment variables:", list(os.environ.keys()), file=sys.stderr)

# Load environment variables at module import
load_environment()

def get_api_key(provider: str) -> str:
    """Get API key for the specified provider."""
    if provider == "openai":
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        return api_key
    elif provider == "azure":
        api_key = os.getenv('AZURE_OPENAI_API_KEY')
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY not found in environment variables")
        return api_key
    elif provider == "anthropic":
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        return api_key
    elif provider == "gemini":
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        return api_key
    else:
        raise ValueError(f"Unsupported provider: {provider}")

def get_model_name(provider: str, model: Optional[str] = None) -> str:
    """Get the model name based on provider and user input."""
    if model:
        return model
    
    if provider == "openai":
        return "gpt-4o"
    elif provider == "azure":
        return os.getenv('AZURE_OPENAI_MODEL_DEPLOYMENT', 'gpt-4o-ms')
    elif provider == "anthropic":
        return "claude-3-7-sonnet-20250219"
    elif provider == "gemini":
        return "gemini-2.0-flash-exp"
    else:
        raise ValueError(f"Unsupported provider: {provider}")

def query_llm(prompt: str, provider: str = "openai", model: Optional[str] = None) -> Optional[str]:
    """
    Query an LLM with a prompt using CrewAI.
    
    Args:
        prompt (str): The text prompt to send
        provider (str): The API provider to use
        model (str, optional): The model to use
        
    Returns:
        Optional[str]: The LLM's response or None if there was an error
    """
    try:
        api_key = get_api_key(provider)
        model_name = get_model_name(provider, model)
        
        # Configure the agent
        llm_config = {
            "api_key": api_key,
            "model": model_name
        }
        
        # Add provider-specific configs
        if provider == "azure":
            llm_config.update({
                "azure_endpoint": "https://msopenai.openai.azure.com",
                "api_version": "2024-08-01-preview"
            })
        
        # Create an agent with the specified LLM
        agent = Agent(
            role="Assistant",
            goal="Provide accurate and helpful responses to queries",
            backstory="You are an AI assistant tasked with answering questions accurately.",
            verbose=True,
            allow_delegation=False,
            llm_config=llm_config,
            provider=provider
        )
        
        # Create a task for the agent
        task = Task(
            description=prompt,
            agent=agent
        )
        
        # Create a crew with a single agent
        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=1,
            process=Process.sequential
        )
        
        # Execute the task
        result = crew.kickoff()
        
        return result
        
    except Exception as e:
        print(f"Error querying LLM: {e}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description='Query an LLM with a prompt using CrewAI')
    parser.add_argument('--prompt', type=str, help='The prompt to send to the LLM', required=True)
    parser.add_argument('--provider', choices=['openai','anthropic','gemini','azure'], default='openai', help='The API provider to use')
    parser.add_argument('--model', type=str, help='The model to use (default depends on provider)')
    
    args = parser.parse_args()
    
    response = query_llm(args.prompt, args.provider, args.model)
    if response:
        print(response)
    else:
        print("Failed to get response from LLM", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 