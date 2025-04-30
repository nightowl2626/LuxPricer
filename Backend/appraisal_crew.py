"""
Implementation of a luxury appraisal crew using the CrewAI framework.
This file defines the LuxuryAppraisalCrew class that orchestrates multiple specialized agents
for appraising luxury items based on user queries and optional images.
"""

import os
import json
import tempfile
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from crewai import Crew, Agent, Task, Process
from config.logging import get_logger
from services.tools import PRICING_TOOLS, TREND_TOOLS, IMAGE_TOOLS, ALL_TOOLS
from crewai.tools import tool

# Configure logging
logger = get_logger(__name__)

class LuxuryAppraisalCrew:
    """
    A crew of specialized agents for luxury item appraisal.
    
    This class creates and manages five specialized agents:
    1. Extraction Agent: Extracts item details from user queries
    2. Research Agent: Researches market trends and pricing data
    3. Evaluation Agent: Evaluates research quality and provides feedback
    4. Valuation Agent: Provides valuations and authenticity assessments
    5. Report Agent: Generates comprehensive appraisal reports
    """
    
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the luxury appraisal crew with specialized agents.
        
        Args:
            provider: Optional LLM provider to use (e.g., 'openai', 'anthropic')
            model: Optional model name to use
        """
        logger.info("Initializing LuxuryAppraisalCrew")
        
        # Store provider and model information
        self.provider = provider
        self.model = model
        
        # Create specialized agents
        self.extraction_agent = self._create_extraction_agent()
        self.research_agent = self._create_research_agent()
        self.evaluation_agent = self._create_evaluation_agent()
        self.valuation_agent = self._create_valuation_agent()
        self.report_agent = self._create_report_agent()
        
        # Store temporary image paths
        self.temp_image_paths = []
    
    def _create_extraction_agent(self) -> Agent:
        """Create an agent specialized in extracting item details from user queries."""
        return Agent(
            role="Luxury Item Information Extraction Specialist",
            goal="Extract detailed information about luxury items from user queries",
            backstory="""You are an expert in analyzing user queries about luxury items.
            You have extensive knowledge of luxury brands, models, and terminology.
            Your specialty is identifying key information from sometimes vague or incomplete descriptions.
            You're meticulous about extracting every relevant detail to ensure accurate appraisals.""",
            verbose=True,
            allow_delegation=False,
        )
    
    def _create_research_agent(self) -> Agent:
        """Create an agent specialized in market research and trends."""
        return Agent(
            role="Luxury Market Research Analyst",
            goal="Research market trends, pricing data, and brand positioning for luxury items",
            backstory="""You are a seasoned luxury market analyst with deep knowledge of historical trends.
            You track pricing fluctuations, market sentiment, and investment potential of luxury goods.
            Your research is highly valued by collectors, investors, and auction houses worldwide.
            You have access to sophisticated tools that help you analyze market dynamics.""",
            verbose=True,
            allow_delegation=False,
            tools=TREND_TOOLS + PRICING_TOOLS  # Provide trend and pricing tools
        )
    
    def _create_evaluation_agent(self) -> Agent:
        """Create an agent specialized in evaluating research quality and providing feedback."""
        return Agent(
            role="Luxury Research Quality Evaluator",
            goal="Evaluate the quality and completeness of luxury market research and provide constructive feedback",
            backstory="""You are an exacting research quality assurance specialist with decades of experience in the luxury goods market.
            Your meticulous eye for detail allows you to quickly identify gaps in market analysis or missed opportunities for deeper insights.
            You've helped major luxury brands refine their market research methodologies and have a reputation for ensuring research
            is comprehensive, accurate, and addresses all key aspects of the market.
            You're not only skilled at identifying deficiencies but also at providing constructive feedback that leads to improved research.""",
            verbose=True,
            allow_delegation=False,
        )
    
    def _create_valuation_agent(self) -> Agent:
        """Create an agent specialized in valuation and authentication."""
        
        # 创建自定义工具来处理价格估计错误
        @tool("handle_price_estimation_error")
        def handle_price_estimation_error(
            designer: str,
            model: str,
            error_message: str
        ) -> Dict[str, Any]:
            """
            Handle errors from price estimation tools by providing a generic response
            that can be used in place of specific pricing data.
            
            Args:
                designer: The designer or brand name
                model: The model or style name
                error_message: The error message returned by the price estimation tool
                
            Returns:
                A dictionary with guidance on how to handle the error in the valuation report
            """
            logger.info(f"Handling price estimation error for {designer} {model}: {error_message}")
            
            # Generic valuation guidance
            return {
                "handled_error": True,
                "original_error": error_message,
                "item": f"{designer} {model}",
                "guidance": "Limited pricing data available for this specific item",
                "recommendation": "Provide a qualitative assessment based on brand reputation, market trends, and comparative analysis of similar items",
                "confidence": "low",
                "suggested_wording": [
                    f"Our database has limited pricing data for this specific {designer} {model}.",
                    "Based on market research and analysis of similar luxury items, we can provide a general value assessment.",
                    "Note that this assessment has a lower confidence level due to limited exact matching data in our system."
                ]
            }
        
        return Agent(
            role="Luxury Item Valuation Expert",
            goal="Provide accurate valuations and authenticity assessments for luxury items",
            backstory="""You have spent decades working with prestigious auction houses and luxury retailers.
            Your expertise in valuing luxury items is unmatched, with a reputation for accuracy and fairness.
            You have authenticated and valued thousands of items, from vintage handbags to rare timepieces.
            You consider multiple factors including condition, rarity, provenance, and market demand.""",
            verbose=True,
            allow_delegation=False,
            tools=PRICING_TOOLS + IMAGE_TOOLS + [handle_price_estimation_error]  # 添加错误处理工具
        )
    
    def _create_report_agent(self) -> Agent:
        """Create an agent specialized in generating comprehensive appraisal reports."""
        return Agent(
            role="Luxury Appraisal Report Specialist",
            goal="Create comprehensive, professional appraisal reports for luxury items",
            backstory="""You are renowned for creating clear, detailed appraisal reports for luxury items.
            Your reports are used by insurance companies, private collectors, and investment funds.
            You excel at presenting complex information in a structured, digestible format.
            You ensure that your reports are thorough, accurate, and tailored to the client's needs.""",
            verbose=True,
            allow_delegation=False
        )
    
    def generate_appraisal(
        self, 
        query: str, 
        images: Optional[List[bytes]] = None,
        output_format: str = "json"
    ) -> Union[Dict[str, Any], str]:
        """
        Generate a comprehensive appraisal for a luxury item based on the user's query.
        
        Args:
            query: The user's appraisal request
            images: Optional list of image bytes for analysis
            output_format: Output format, either "json" or "markdown"
            
        Returns:
            Either a JSON object or Markdown report containing the appraisal
        """
        logger.info(f"Generating appraisal for query: {query}")
        
        # Save any provided images to temporary files
        self._save_temp_images(images)
        
        try:
            # Create tasks for the crew
            tasks = self._create_appraisal_tasks(query)
            
            # Create and run the crew
            crew = Crew(
                agents=[
                    self.extraction_agent,
                    self.research_agent,
                    self.evaluation_agent,
                    self.valuation_agent,
                    self.report_agent
                ],
                tasks=tasks,
                verbose=True,
                process=Process.sequential
            )
            
            # Execute the crew workflow
            result = crew.kickoff()
            
            # Process the result
            if output_format.lower() == "markdown":
                return result
            else:
                # Parse the markdown report into a structured JSON
                try:
                    # In a real implementation, you would parse the Markdown content
                    # into a structured JSON format here. For simplicity, we're returning
                    # a basic structure.
                    
                    # Example JSON structure:
                    return {
                        "status": "success",
                        "timestamp": datetime.now().isoformat(),
                        "query": query,
                        "appraisal_report": {
                            "content": result,
                            "summary": "Luxury item appraisal completed successfully",
                            "format": "markdown"
                        }
                    }
                except Exception as e:
                    logger.error(f"Error parsing appraisal result: {str(e)}")
                    return {
                        "status": "error",
                        "error": f"Failed to parse appraisal result: {str(e)}",
                        "raw_result": result
                    }
        
        except Exception as e:
            logger.error(f"Error generating appraisal: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "query": query
            }
        finally:
            # Clean up temporary image files
            self._cleanup_temp_images()
    
    def _create_appraisal_tasks(self, query: str) -> List[Task]:
        """
        Create a sequence of tasks for the luxury item appraisal process.
        
        Args:
            query: The user's appraisal request
            
        Returns:
            A list of tasks for the crew to execute
        """
        # Task 1: Extract item details from the user query
        extraction_task = Task(
            description=f"""
            Extract all relevant details about the luxury item from the user's query:
            "{query}"
            
            Details should include:
            1. Brand/Designer
            2. Item type (e.g., handbag, watch, jewelry)
            3. Model name or collection
            4. Materials
            5. Color
            6. Size or dimensions (if mentioned)
            7. Condition (if mentioned)
            8. Age or year of production (if mentioned)
            9. Any special features or characteristics
            10. Any specific concerns or questions from the user
            
            Also extract any contextual information that might be important for valuation or authentication.
            """,
            agent=self.extraction_agent,
            expected_output="""
            A structured summary of all luxury item details extracted from the query.
            Format this as a detailed list with clear labels for each attribute, 
            and note any information that is uncertain or missing.
            """
        )
        
        # Task 2: Research market context and trends
        research_task = Task(
            description="""
            Using the item details provided by the Extraction Agent, research the current
            market context and trends for this luxury item.
            
            Your research should include:
            1. Current market position of the brand/designer
            2. Pricing trends for this specific model/item over the past 1-3 years
            3. Limited edition status or special collection details (if applicable)
            4. Popularity and demand factors
            5. Key selling points emphasized by the brand and by resellers
            6. Competitor comparisons and market positioning
            7. Investment potential and projected value trends
            8. Any recent news, fashion shows, or celebrity endorsements affecting value
            
            Use the get_perplexity_trends tool to gather comprehensive trend information.
            """,
            agent=self.research_agent,
            expected_output="""
            A detailed market research report covering current trends, pricing history,
            market positioning, and investment outlook for the specified luxury item.
            Include specific data points and references where possible.
            """
        )
        
        # Task 3: Evaluate research quality and provide feedback if needed
        evaluation_task = Task(
            description="""
            Evaluate the quality and completeness of the research provided by the Research Agent.
            
            Assess the following aspects:
            1. Comprehensiveness - Does the research cover all key areas needed for a proper appraisal?
            2. Specificity - Is the information specific to the exact item rather than generic?
            3. Recency - Is the market data current and relevant?
            4. Depth - Is there sufficient detail on pricing trends and market positioning?
            5. Accuracy - Does the information align with known facts about the luxury market?
            6. Usefulness - Will this information effectively support a valuation assessment?
            
            If you identify significant gaps or issues:
            - Clearly articulate what's missing or problematic
            - Provide specific feedback on how to improve the research
            - Suggest specific additional areas to investigate
            
            You will determine if the research meets the quality threshold needed for an accurate appraisal.
            """,
            agent=self.evaluation_agent,
            context=[extraction_task, research_task],
            expected_output="""
            A detailed evaluation of the research quality with either:
            1. Approval - Confirming the research is complete and sufficient for valuation
            OR
            2. Feedback - Clear identification of gaps and specific instructions for improvements needed
            
            If feedback is provided, include a "NEEDS_REVISION" marker at the beginning of your response.
            """
        )
        
        # Task 4: Research revision based on evaluation feedback (initial slot, may be repeated)
        research_revision_task = Task(
            description="""
            IMPORTANT: This task is a research revision based on evaluation feedback.
            
            Review the original extraction information and your previous research, along with
            the evaluation feedback provided. Address ALL issues identified by the evaluator.
            
            Make sure to:
            1. Fill in ALL gaps identified in the evaluation
            2. Provide MORE SPECIFIC information where requested
            3. Ensure data is CURRENT and RELEVANT
            4. Add the requested DEPTH to pricing trends and market positioning
            5. Correct any inaccuracies noted in the evaluation
            6. Focus on making your research DIRECTLY USEFUL for valuation
            
            Use the get_perplexity_trends tool with MODIFIED QUERIES based on the feedback
            to gather the missing or more specific information.
            
            DO NOT simply repeat your previous research - this must be a substantively
            improved and expanded version addressing all feedback points.
            """,
            agent=self.research_agent,
            context=[extraction_task, research_task, evaluation_task],
            expected_output="""
            A REVISED and IMPROVED market research report that fully addresses all feedback
            from the evaluator. This should be MORE COMPREHENSIVE, MORE SPECIFIC, and
            MORE USEFUL than the original research.
            
            Clearly indicate what has been added or improved in response to the feedback.
            """
        )
        
        # Task 5: Re-evaluate revised research (initial slot, may be repeated)
        re_evaluation_task = Task(
            description="""
            Re-evaluate the REVISED research provided by the Research Agent after your feedback.
            
            Focus on whether the specific issues you previously identified have been adequately addressed:
            1. Have all gaps been filled?
            2. Is the information now sufficiently specific to the exact item?
            3. Is the market data current and relevant?
            4. Is there now adequate depth on pricing trends and market positioning?
            5. Have any inaccuracies been corrected?
            6. Is the research now substantially more useful for valuation purposes?
            
            Thoroughly assess if the research now meets the quality threshold for an accurate appraisal.
            """,
            agent=self.evaluation_agent,
            context=[extraction_task, research_task, evaluation_task, research_revision_task],
            expected_output="""
            A follow-up evaluation of the revised research with either:
            1. Approval - Confirming the research is now complete and sufficient for valuation
            OR
            2. Additional feedback - Clear identification of remaining gaps with specific instructions
            
            If additional feedback is provided, include a "NEEDS_REVISION" marker at the beginning of your response.
            If this is the final allowed iteration and issues remain, provide an "APPROVED_WITH_LIMITATIONS" 
            marker and note what limitations should be considered during valuation.
            """
        )
        
        # Create task lists - we'll build this dynamically
        all_tasks = [extraction_task]
        
        # Create research task with feedback loop
        def create_research_feedback_loop(max_iterations=1):
            """Create a research and evaluation feedback loop with a maximum number of iterations"""
            
            # First research cycle
            all_tasks.append(research_task)
            all_tasks.append(evaluation_task)
            
            # Add dynamic feedback loop
            current_research_task = research_revision_task
            current_eval_task = re_evaluation_task
            
            # Starting with revision 2 since revision 1 is already created above
            for i in range(2, max_iterations + 1):
                # Create new copies of tasks for this iteration
                next_research_task = Task(
                    description=f"""
                    IMPORTANT: This is research revision #{i} based on continued evaluation feedback.
                    
                    Review all previous research attempts and evaluation feedback, particularly
                    the most recent evaluation. Address ALL remaining issues identified by the evaluator.
                    
                    Make sure to:
                    1. Fill in ALL gaps still identified in the latest evaluation
                    2. Provide EVEN MORE SPECIFIC information where requested
                    3. Ensure data is CURRENT and RELEVANT
                    4. Add the requested DEPTH to pricing trends and market positioning
                    5. Correct any inaccuracies noted in the latest evaluation
                    6. Focus on making your research DIRECTLY USEFUL for valuation
                    
                    Use the get_perplexity_trends tool with REFINED QUERIES based on the feedback
                    to gather the missing or more specific information.
                    
                    DO NOT simply repeat your previous research - this must be a substantively
                    improved version addressing all feedback points from the latest evaluation.
                    """,
                    agent=self.research_agent,
                    context=[extraction_task, current_research_task, current_eval_task],
                    expected_output=f"""
                    REVISION #{i}: A significantly REVISED and IMPROVED market research report 
                    that fully addresses all feedback from the latest evaluation. This should
                    demonstrate substantial improvements over all previous versions.
                    
                    Clearly highlight what has been added or improved in response to the feedback.
                    """
                )
                
                next_eval_task = Task(
                    description=f"""
                    IMPORTANT: This is evaluation #{i} of the revised research.
                    
                    Re-evaluate the latest REVISED research (revision #{i}) provided by the Research Agent.
                    
                    Focus on whether the specific issues you previously identified have been adequately addressed:
                    1. Have all remaining gaps been filled?
                    2. Is the information now sufficiently specific to the exact item?
                    3. Is the market data current and relevant?
                    4. Is there now adequate depth on pricing trends and market positioning?
                    5. Have all inaccuracies been corrected?
                    6. Is the research now substantially more useful for valuation purposes?
                    
                    Consider that this is iteration #{i} - if there are only minor issues remaining,
                    you may decide to approve the research so the appraisal process can proceed.
                    
                    Thoroughly assess if the research now meets the minimum quality threshold for an accurate appraisal.
                    """,
                    agent=self.evaluation_agent,
                    context=[extraction_task, current_research_task, current_eval_task, next_research_task],
                    expected_output=f"""
                    Evaluation #{i}: A final assessment of the revised research with either:
                    1. Approval - Confirming the research is now complete and sufficient for valuation
                    OR
                    2. Additional feedback - Clear identification of remaining critical gaps with specific instructions
                    
                    If additional feedback is provided, include a "NEEDS_REVISION" marker at the beginning of your response.
                    If this is the final allowed iteration and issues remain, provide an "APPROVED_WITH_LIMITATIONS" 
                    marker and note what limitations should be considered during valuation.
                    """
                )
                
                # Add these tasks to our list
                all_tasks.append(next_research_task)
                all_tasks.append(next_eval_task)
                
                # Update current tasks for next iteration
                current_research_task = next_research_task
                current_eval_task = next_eval_task
        
        # Create the feedback loop with max 5 iterations
        create_research_feedback_loop(max_iterations=1)
        
        # Task: Perform valuation and authentication assessment
        valuation_task = Task(
            description="""
            Based on the item details from the Extraction Agent and the market research
            from the Research Agent (including any revisions), provide a detailed valuation and authentication assessment.
            
            If images were provided, use the image analysis tools to assess authenticity and condition.
            
            Your valuation should consider:
            1. Item condition (based on description or images)
            2. Rarity and exclusivity
            3. Current market demand
            4. Historical pricing trends
            5. Authentication indicators
            
            IMPORTANT: When using the price estimation tool, follow these steps:
            1. First attempt to use get_price_estimation with the details from the extraction agent
            2. Check if the response contains an "error" field
            3. If an error is present (e.g., "Insufficient comparable listings found"), use the handle_price_estimation_error tool
               with the designer, model, and error message to get appropriate guidance on how to handle the situation
            4. Use the suggested wording and recommendations from the error handler in your assessment
            5. DO NOT include raw error messages in your assessment
            
            Focus on providing the most informative valuation possible, even when exact pricing data is limited:
            - If pricing data is available, provide a specific estimated value range with high confidence
            - If pricing data is limited, provide a more general assessment based on brand, condition, market trends, and similar items
            
            This ensures the final report contains useful information even when exact pricing data is unavailable.
            
            Provide a comprehensive assessment with a confidence level.
            """,
            agent=self.valuation_agent,
            context=all_tasks,  # Use all research and evaluation tasks as context
            expected_output="""
            A comprehensive valuation and authentication assessment including:
            1. Estimated current market value (specific range or general assessment)
            2. Authentication opinion (if relevant)
            3. Value justification based on market conditions and item specifics
            4. Investment outlook
            5. Confidence level in the valuation
            """
        )
        
        # Add valuation task
        all_tasks.append(valuation_task)
        
        # Task: Generate final appraisal report
        report_task = Task(
            description="""
            Create a comprehensive, professional appraisal report for the luxury item
            based on all previous tasks. Integrate the extraction details, market research,
            and valuation assessment into a cohesive document.
            
            The report should follow this structure:
            
            # Luxury Item Appraisal Report
            ## Executive Summary
            [Brief overview of the item and key findings]
            
            ## Item Details
            [All details about the item including brand, model, specifications]
            
            ## Valuation Analysis
            [Detailed valuation with BOTH specific estimated price value AND price ranges with confidence levels.
            Make sure to clearly state both the exact estimated price (e.g., "$2,864") and the recommended price range (e.g., "$2,800-$4,200").]
            
            ## Market Analysis
            [Analysis of current market conditions and trends]
            
            ## Investment Outlook
            [Assessment of investment potential and future value trends]
            
            ## Authentication Assessment
            [If applicable, assessment of authenticity indicators]
            
            ## Conclusion and Recommendations
            [Final thoughts and recommendations for the client]
            
            IMPORTANT: Review the valuation agent's assessment carefully. If the valuation agent noted that
            pricing data was limited for this specific item:
            1. Acknowledge this limitation in the Valuation Analysis section
            2. Focus on the qualitative factors that affect the item's value
            3. Present any general value assessment or range provided by the valuation agent
            4. Emphasize other valuable insights like market trends, investment outlook, and condition assessment
            5. Maintain a confident, professional tone even when specific pricing data is limited
            
            Ensure the report is professional, well-structured, and provides clear, actionable insights.
            """,
            agent=self.report_agent,
            expected_output="""
            A complete, professional Markdown appraisal report with all sections
            properly formatted and containing comprehensive information about the luxury item,
            its value, market position, and investment potential.
            """,
            context=all_tasks  # Use all tasks as context
        )
        
        # Add report task to the final list
        all_tasks.append(report_task)
        
        return all_tasks

    def _save_temp_images(self, images: Optional[List[bytes]]) -> None:
        """
        Save provided image bytes to temporary files.
        
        Args:
            images: List of image bytes to save
        """
        if not images:
            return
        
        for i, image_bytes in enumerate(images):
            try:
                # Create a temporary file
                fd, temp_path = tempfile.mkstemp(suffix=".jpg")
                os.close(fd)
                
                # Write the image bytes to the file
                with open(temp_path, 'wb') as f:
                    f.write(image_bytes)
                
                # Store the path for later use
                self.temp_image_paths.append(temp_path)
                logger.info(f"Saved temp image {i+1} to {temp_path}")
                
            except Exception as e:
                logger.error(f"Error saving temporary image {i+1}: {str(e)}")
    
    def _cleanup_temp_images(self) -> None:
        """Remove all temporary image files."""
        for path in self.temp_image_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info(f"Removed temp image: {path}")
            except Exception as e:
                logger.error(f"Error removing temp image {path}: {str(e)}")
        
        # Clear the list
        self.temp_image_paths = []

    async def run_appraisal(self, query: str, image_path: Optional[str] = None) -> str:
        """
        Run the appraisal process asynchronously.
        
        Args:
            query: The user's appraisal request
            image_path: Optional path to an image file for analysis
            
        Returns:
            A Markdown formatted appraisal report
        """
        logger.info(f"Running appraisal for query: {query}")
        
        images = None
        if image_path:
            logger.info(f"Including image from path: {image_path}")
            # Read the image file
            try:
                with open(image_path, 'rb') as f:
                    images = [f.read()]
                logger.info(f"Successfully read image from {image_path}")
            except Exception as e:
                logger.error(f"Error reading image file: {str(e)}")
                # Continue without the image rather than failing
        
        # Call the synchronous generate_appraisal method with "markdown" output format
        result = self.generate_appraisal(query, images, output_format="markdown")
        
        # Handle CrewOutput type result (added for compatibility with newer CrewAI versions)
        if hasattr(result, 'raw'):
            logger.info("Converting CrewOutput to string")
            # Extract the raw string from CrewOutput
            result = str(result.raw)
        elif hasattr(result, '__str__'):
            # Convert any other object to string if it has a string representation
            result = str(result)
        
        # If result is a dictionary (error case), convert to string
        if isinstance(result, dict):
            # Handle error case
            error_message = f"Error: {result.get('error', 'Unknown error')}"
            logger.error(f"Appraisal failed: {error_message}")
            return f"# Appraisal Error\n\n{error_message}"
        
        # Return the markdown report
        return result 