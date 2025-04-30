import os
import json
from openai import OpenAI
from dotenv import load_dotenv 

load_dotenv()

YOUR_API_KEY = os.environ.get("PERPLEXITY_API_KEY")

# Define the target item for the prompt
TARGET_DESIGNER = "Fendi"
TARGET_MODEL = "Baguette"

# === Prompt Construction ===
prompt_content = f"""
Please analyze information available online from the **last 6 months** regarding the **{TARGET_DESIGNER} {TARGET_MODEL}** handbag.

Based *only* on the information retrieved from your search:
1. Identify mentions of the bag appearing in recent fashion shows or runway contexts.
2. List any high-profile celebrities or influencers recently seen carrying the bag.
3. Extract frequently mentioned positive keywords/phrases from recent user reviews or discussions about the bag.
4. Extract frequently mentioned negative keywords/phrases from recent user reviews or discussions about the bag.
5. Find any notes or mentions related to its collectibility, investment value, rarity, or discontinuation status.
6. Provide a brief overall summary of the bag's current trend status based *only* on the findings above.
7. List up to 3 key source URLs supporting these findings.

Present your findings **ONLY** as a single, valid JSON object with the following keys. If no information is found for a specific list, use an empty list `[]`. If no information is found for the summary string, use `null` or a short "N/A" string.

{{
  "target_item": "{TARGET_DESIGNER} {TARGET_MODEL}",
  "timeframe": "last 6 months",
  "recent_runway_mentions": [
    "string description of mention 1",
    "string description of mention 2"
  ],
  "recent_celebrity_sightings": [
    "Celebrity Name 1 (Event/Context)",
    "Celebrity Name 2"
  ],
  "recent_review_keywords_positive": [
    "keyword1", "keyword2"
  ],
  "recent_review_keywords_negative": [
    "keyword1", "keyword2"
  ],
  "collectibility_notes": [
    "Snippet about investment value...",
    "Mention of limited edition..."
  ],
  "overall_trend_summary": "Brief text summary based ONLY on the findings above.",
  "key_sources": [
    "url1", "url2", "url3"
  ]
}}
"""

# === Api call ===
messages = [
    {
        "role": "system",
        "content": (
            "You are an AI assistant specialized in analyzing recent fashion trends "
            "for luxury items based on web search results. Your goal is to extract "
            "specific indicators of trendiness and collectibility into a structured JSON format."
        ),
    },
    {
        "role": "user",
        "content": prompt_content,
    },
]


client = OpenAI(api_key=YOUR_API_KEY, base_url="https://api.perplexity.ai")


print(f"--- Sending request for {TARGET_DESIGNER} {TARGET_MODEL} ---")

try:
    response = client.chat.completions.create(
        model="sonar-pro",
        messages=messages,
        # temperature=0.3 # Optional: Lower temperature for more factual extraction
    )
    
    content = response.choices[0].message.content
    print("\n--- Non-Streaming Response ---")
    print(content)

    # Parse JSON
    try:
        parsed_json = json.loads(content)
        print("\n--- Parsed JSON ---")
        print(json.dumps(parsed_json, indent=2))

    except json.JSONDecodeError:
        print("\n--- WARNING: Could not parse the response content as JSON ---")
    except Exception as e:
        print(f"\n--- ERROR processing response: {e} ---")


except Exception as e:
    print(f"\n--- ERROR during API call: {e} ---")
