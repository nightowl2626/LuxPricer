#!/usr/bin/env python3

"""
LLM Interaction Service
Handles communication with the chosen LLM (GPT-4o via OpenAI API).
"""
import json
import asyncio
import re
import os
from typing import Dict, Any, List, Optional

# Import crewAI components
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tasks.task_output import TaskOutput

# Import configuration and logging
from config.settings import settings
from config.logging import get_logger

# Configure logging
logger = get_logger(__name__)

def get_agent_with_llm(role: str, goal: str, backstory: str, provider: str = None, model: Optional[str] = None) -> Agent:
    """
    Create an Agent with the specified LLM configuration
    
    Args:
        role: Agent role
        goal: Agent goal
        backstory: Agent backstory
        provider: LLM provider (openai, anthropic, azure, ollama)
        model: Model name, uses default if None
        
    Returns:
        Configured Agent instance
    """
    # Use the configured default provider if none specified
    provider = provider or settings.llm.default_provider
    
    # Create model name
    if provider.lower() == "openai":
        model_name = model or settings.llm.openai_model
    elif provider.lower() == "anthropic":
        model_name = model or settings.llm.anthropic_model
    elif provider.lower() == "azure":
        model_name = model or settings.llm.azure_openai_deployment
    elif provider.lower() == "ollama":
        model_name = model or settings.llm.ollama_model
    else:
        logger.warning(f"Unknown provider: {provider}, falling back to OpenAI")
        provider = "openai"
        model_name = model or settings.llm.openai_model
    
    # 针对不同的提供商构建不同的配置
    if provider.lower() == "openai":
        # OpenAI不接受provider参数
        config = {
            "model": model_name
        }
        
        # 添加API密钥
        if settings.llm.openai_api_key:
            config["api_key"] = settings.llm.openai_api_key
        elif os.environ.get("OPENAI_API_KEY"):
            config["api_key"] = os.environ.get("OPENAI_API_KEY")
            
        llm = LLM(**config)
    elif provider.lower() == "anthropic":
        config = {
            "provider": provider,
            "model": model_name
        }
        
        if settings.llm.anthropic_api_key:
            config["api_key"] = settings.llm.anthropic_api_key
        elif os.environ.get("ANTHROPIC_API_KEY"):
            config["api_key"] = os.environ.get("ANTHROPIC_API_KEY")
            
        llm = LLM(**config)
    elif provider.lower() == "azure":
        config = {
            "provider": provider,
            "model": model_name
        }
        
        if settings.llm.azure_openai_api_key:
            config["api_key"] = settings.llm.azure_openai_api_key
            config["azure_endpoint"] = settings.llm.azure_openai_api_base
            
        llm = LLM(**config)
    else:
        # 其他提供商
        config = {
            "provider": provider,
            "model": model_name
        }
        llm = LLM(**config)
    
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        llm=llm,
        verbose=settings.debug
    )

async def generate_appraisal_plan(query: str, provider: str = None, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate an appraisal plan, determining which tools to call for the appraisal process

    Args:
        query: User query text
        provider: LLM provider
        model: LLM model name

    Returns:
        Dictionary containing the tool call plan
    """
    logger.info(f"Generating appraisal plan for query: {query}")
    
    # Create Planning Agent
    planning_agent = get_agent_with_llm(
        role="Luxury Appraisal Planning Expert",
        goal="Extract key information from user queries and plan the necessary tool calls for appraisal",
        backstory="You are an experienced luxury items appraisal expert, familiar with various luxury categories and brands. You excel at analyzing user needs, planning the appraisal process, and ensuring efficient and accurate value assessments.",
        provider=provider,
        model=model
    )
    
    # Create Planning Task
    planning_task = Task(
        description=f"""
        Analyze the following user query, extract key information, and plan the tools to call:

        User Query: {query}

        You need to extract the following information from the query:
        1. Brand name (e.g., Louis Vuitton, Chanel, Hermes, etc.)
        2. Model/Series name
        3. Item type (e.g., bag, watch, jewelry, etc.)
        4. Relevant attributes (e.g., size, material, color, year, etc.)
        5. Condition rating (1-5, default to 3 if not explicitly provided)
        
        Based on the extracted information, plan which tools need to be called. Available tools include:
        
        - get_basic_price_estimation: Provides basic price estimation
          Parameters: designer, model, condition_rating
          
        - get_advanced_price_estimation: Provides more precise price estimation
          Parameters: designer, model, size, material, color, condition_rating
          
        - get_search_trends: Analyzes search trends
          Parameters: brand, model, timeframe
          
        - get_social_media_trends: Analyzes social media trends
          Parameters: brand, model, timeframe
          
        - get_news_analysis: Analyzes related news
          Parameters: brand, model, timeframe
          
        - get_resale_market_trends: Analyzes secondhand market trends
          Parameters: brand, model, timeframe
        
        Please return the planning result in JSON format as follows:
```json
{
          "extracted_info": {
            "brand": "Extracted brand",
            "model": "Extracted model",
            "item_type": "Item type",
            "attributes": {
              "size": "Size (if any)",
              "material": "Material (if any)",
              "color": "Color (if any)",
              "year": "Year (if any)"
            },
            "condition_rating": 3
  },
  "tool_calls": [
    {
              "tool_name": "Tool name",
              "parameters": {
                "param1": "value1",
                "param2": "value2"
              }
    }
  ]
}
```

        Ensure you select appropriate tools and provide correct parameters. Don't add missing information arbitrarily; if certain information is not provided, leave the corresponding attributes empty or use default values.
        """,
        agent=planning_agent,
        expected_output="JSON containing extracted information and tool call plan"
    )
    
    # Create and execute Crew
    crew = Crew(
        agents=[planning_agent],
        tasks=[planning_task],
        verbose=settings.debug,
        process=Process.sequential
    )
    
    # We need to await the kickoff in an async environment
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, crew.kickoff)
    
    # Try to parse JSON result
    try:
        # First try to parse the entire string directly
        plan = json.loads(result)
    except json.JSONDecodeError:
        # If failed, try to extract JSON part from the text
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, result)
        if match:
            try:
                plan = json.loads(match.group(1))
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from extracted content: {match.group(1)}")
                plan = {"error": "Failed to parse result as JSON", "raw_text": result}
        else:
            # Try to match any format of braces content
            json_pattern = r'({[\s\S]*?})'
            match = re.search(json_pattern, result)
            if match:
                try:
                    plan = json.loads(match.group(1))
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON from extracted content: {match.group(1)}")
                    plan = {"error": "Failed to parse result as JSON", "raw_text": result}
            else:
                logger.error(f"No JSON-like content found in result: {result}")
                plan = {"error": "No JSON content found in result", "raw_text": result}
    
    logger.info(f"Generated plan: {json.dumps(plan, indent=2)}")
    return plan

async def synthesize_appraisal_report(item_details: Dict[str, Any], tool_results: Dict[str, Any], 
                              provider: str = None, model: Optional[str] = None) -> str:
    """
    Synthesize an appraisal report, integrating tool results into a complete appraisal report

    Args:
        item_details: Item detailed information
        tool_results: Tool call results
        provider: LLM provider
        model: LLM model name

    Returns:
        Markdown-formatted appraisal report
    """
    logger.info(f"Synthesizing appraisal report for item: {item_details.get('brand', 'Unknown')} {item_details.get('model', 'Unknown')}")
    
    # Create Synthesizer Agent
    synthesizer_agent = get_agent_with_llm(
        role="Luxury Appraisal Report Expert",
        goal="Generate detailed, professional, and easily understandable luxury appraisal reports based on tool results",
        backstory="You are a highly respected luxury appraisal report expert with over 15 years of experience, skilled at extracting key information from complex data and transforming it into professional, comprehensive, and easy-to-understand luxury appraisal reports. Your reports are widely trusted by collectors and investors worldwide.",
        provider=provider,
        model=model
    )
    
    # Convert item_details and tool_results to string format for inclusion in task description
    item_details_str = json.dumps(item_details, indent=2)
    tool_results_str = json.dumps(tool_results, indent=2)
    
    # Create Synthesis Task
    synthesis_task = Task(
        description=f"""
        Based on the following item details and tool call results, generate a comprehensive, professional, and easy-to-understand luxury appraisal report:

        ## Item Details
        ```json
        {item_details_str}
        ```

        ## Tool Call Results
        ```json
        {tool_results_str}
        ```

        Your report should be presented in Markdown format and include the following sections:

        1. **Report Summary**: Briefly overview the item and valuation results.
        
        2. **Item Details**: Include brand, model, type, material, color, size, and other basic information.
        
        3. **Valuation Analysis**:
           - Include basic price estimation and advanced price estimation (if available)
           - Explain price composition factors (base price, condition factor, trend factor, etc.)
           - Provide price range (minimum, average, maximum)
           - Analyze price volatility and reliability
        
        4. **Market Analysis**:
           - Search trend analysis (popular regions, search interest changes)
           - Social media trends (mention volume, sentiment analysis)
           - News analysis (media coverage, brand dynamics)
           - Secondhand market trends (price trends, transaction volume)
        
        5. **Investment Prospects**:
           - Analyze appreciation potential based on market data
           - Provide short-term (6 months) and long-term (3 years) investment advice
           - Assess market liquidity
        
        6. **Appraisal Conclusion**:
           - Final valuation range
           - Appraisal confidence score (1-10, based on data adequacy)
           - Purchase/investment recommendations

        Write the report based on available data. If data for certain sections is insufficient, simplify or omit that section, but please note the data limitations in the report.
        
        Maintain a professional yet clear language style, avoid excessive technical terminology, and ensure that ordinary collectors can understand it.
        """,
        agent=synthesizer_agent,
        expected_output="Markdown-formatted luxury appraisal report"
    )
    
    # Create and execute Crew
    crew = Crew(
        agents=[synthesizer_agent],
        tasks=[synthesis_task],
        verbose=settings.debug,
        process=Process.sequential
    )
    
    # We need to await the kickoff in an async environment
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, crew.kickoff)
    
    # Beautify Markdown output
    # Remove unnecessary Markdown code block markers
    clean_result = re.sub(r'^```markdown\s*', '', result)
    clean_result = re.sub(r'\s*```$', '', clean_result)
    
    logger.info("Appraisal report synthesis completed")
    return clean_result 