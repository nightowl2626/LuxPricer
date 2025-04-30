# 💡Project Description & Problem Solved

Navigating the world of luxury resale can feel like trying to hit a moving target in the dark! With literally millions of different handbag models out there, each with its own history, condition, and desirability, figuring out a fair price is a real headache. Add constantly shifting fashion trends and a fragmented online market, and it's no wonder even seasoned sellers often feel like they're flying blind, potentially undervaluing precious items or leaving money on the table. There's simply no easy "one size fits all" manual approach.

That's where LuxPricer comes in! Think of it as your friendly, expert AI guide designed to cut through the confusion. We've built an intelligent agent that takes the guesswork out of valuation. Just chat with LuxPricer, tell it about the handbag you're curious about (the brand, model, condition), and let it work its magic. Behind the scenes, LuxPricer orchestrates a sophisticated process, using advanced AI to understand your request, analyse current market data and trends, and apply smart calculation logic. In moments, you get a clear, fair market value estimate, complete with a straightforward explanation of why your bag is worth that much. LuxPricer empowers business owners with the knowledge to buy or sell confidently.

# ⚙Solution & Technical Implementation
The luxury item appraisal system employs a sequential multi-agent workflow powered by CrewAI to produce professional appraisals. Each specialized agent contributes unique expertise to the process, creating a comprehensive evaluation pipeline.
## 🤖The Agent Workflow in Detail
1. Extraction Agent 🏗
Role: Luxury Item Information Extraction Specialist
Goal: Extract detailed information from user queries about luxury items.
Process:
Receives the raw user query text (e.g., "I have a Chanel Classic Flap bag in excellent condition")
Uses natural language processing to identify key product attributes
Extracts brand, model, materials, condition, color, and other relevant details
Structures this information for subsequent agents
Tools Used: None (relies on language processing capabilities)
Output: A structured summary of item details with confidence levels for each attribute identified.
2. Research Agent 🔍
Role: Luxury Market Research Analyst
Goal: Research market trends, pricing data, and brand positioning.
Process:
Takes the structured item information from the Extraction Agent
Researches current market positioning of the brand/designer
Analyzes pricing trends for the specific model
Investigates limited edition status and special collection details
Evaluates popularity and demand factors
Determines investment potential
Tools Used:
get_perplexity_trends: Gathers comprehensive trend information
get_price_estimation: Collects general price data (although final pricing is done by the Valuation Agent)
Output: A detailed market research report with pricing history, market positioning, and a calculated trend score (0-1) that will influence final valuation.
3. Evaluation Agent 🔂
Role: Luxury Research Quality Evaluator
Goal: Evaluate research quality and provide feedback for improvement.
Process:
Reviews the market research report from the Research Agent
Assesses comprehensiveness, specificity, recency, depth, and accuracy
Identifies gaps or issues in the research
Provides constructive feedback if improvements are needed
May trigger a feedback loop with the Research Agent (up to 5 iterations)
Tools Used: None (relies on analytical capabilities)
Output: An evaluation report that either approves the research or provides specific feedback for improvements.
4. Valuation Agent 🔢
Role: Luxury Item Valuation Expert
Goal: Provide accurate valuations and authenticity assessments.
Process:
Integrates the item details from Extraction Agent
Incorporates market research from Research Agent
Performs the core RAG-based pricing estimation:
Constructs a semantic search query
Retrieves semantically similar items from vector database
Calculates price statistics from similar items
Applies condition rating adjustments
Applies trend score adjustments from Research Agent
Analyzes authenticity indicators
Assesses investment outlook
Tools Used:
get_price_estimation: Core RAG pricing tool that performs vector retrieval
analyze_luxury_item_image: For condition and authenticity assessment (if images provided)
handle_price_estimation_error: Handles cases where price estimation fails
Output: A comprehensive valuation with price range, confidence level, key valuation factors, and authenticity assessment.
5. Report Agent 📝
Role: Luxury Appraisal Report Specialist
Goal: Create professional, comprehensive appraisal reports.
Process:
Collects outputs from all previous agents
Organizes information into a structured report format
Ensures professional presentation and logical flow
Adds executive summary and recommendations
Formats the report according to industry standards
Tools Used: None (focuses on information synthesis and presentation)
Output: A complete, professional appraisal report with executive summary, item details, valuation analysis, market analysis, investment outlook, authenticity assessment, and recommendations.

## 🔎RAG System Implementation
The Retrieval-Augmented Generation (RAG) system operates within the get_price_estimation tool and follows these steps:
Query Formation: Converts item details into a search query.
Vector Retrieval: Uses FAISS to find semantically similar luxury items.
Result Filtering: Ensures retrieved items are relevant to the query.
Price Analysis: Calculates median, mean, range, and other statistics from similar items.
Price Adjustment: Applies condition rating factor (0.7-1.2) and trend score factor (0.85-1.15).
Confidence Calculation: Determines confidence level based on the number of matching items.
The system leverages a vector database built from cleaned_listings.json, containing detailed information about luxury items including designer, model, condition, and price.
This comprehensive workflow ensures accurate, market-informed appraisals that consider both the item's specific characteristics and current market conditions.
## ✨UI
User opens the LuxPricer chat interface.
User types their request, describing the bag and its condition, into the input bar.
(Optional) User clicks the upload icon to add photos of the bag.
User sends the message.
The agent provides the final valuation estimate and explanation within the chat.
The user clicks the "Export PDF" button in the agent's final message to save a formal record of the valuation.
# 🚀Future Development
Future development envisions expanding LuxPricer into a comprehensive resale intelligence platform. This includes integrating business-specific components such as connections to historical price databases for deeper trend analysis, APIs for wholesalers or private seller platforms to broaden market scope, and implementing more elaborated trend analysis techniques (e.g., incorporating social media velocity or broader fashion category movements). We also plan to explore machine learning regression models for price estimation as more historical data becomes available, further enhancing accuracy. Incorporating additional data sources, as well as region-specific insights is also essential. The goal is to evolve LuxPricer into an indispensable tool for anyone navigating the complexities of the luxury resale ecosystem.


