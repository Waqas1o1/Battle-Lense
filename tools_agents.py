import os, sys, json
import asyncio
from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    AsyncOpenAI,
    set_tracing_disabled,
    ModelSettings,
    function_tool,
)
from dotenv import load_dotenv
from tavily import TavilyClient

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# 🌿 Load environment variables
load_dotenv()
set_tracing_disabled(disabled=False)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

# 🔐 Setup Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

external_client = AsyncOpenAI(api_key=GEMINI_API_KEY, base_url=BASE_URL)
llm_model = OpenAIChatCompletionsModel(
    model="gemini-2.5-flash", openai_client=external_client
)


client: TavilyClient = TavilyClient(TAVILY_API_KEY)


@function_tool
def tavily_search(query: str) -> dict:
    """
    Perform a Tavily search on the internet and return results.
    """
    response = client.search(query)
    return response


agent = Agent(
    model=llm_model,
    name="Agent",
    instructions="",
    tools=[tavily_search],
    model_settings=ModelSettings(temperature=0.2),
)
# instructions="""
#                 You are the Military Data Agent.
#                 Your role is to gather and summarize reliable information about the military strength of two countries.

#                 Your tasks:
#                 1. Collect and compare the following data points for both countries:
#                 - Active military personnel
#                 - Reserve forces
#                 - Land power (tanks, artillery, armored vehicles)
#                 - Air power (fighters, bombers, helicopters, drones)
#                 - Naval power (aircraft carriers, destroyers, submarines)
#                 - Missile and nuclear capabilities (if available)
#                 - Annual defense budget
#                 - Notable alliances or defense treaties
#                 2. Use only credible and up-to-date sources (e.g., SIPRI, Global Firepower, government reports, reputable news).
#                 3. Present the data in a **structured comparison format**, highlighting key strengths and weaknesses for each country.
#                 4. If some data is missing, note it clearly instead of inventing.
#                 5. Return your output in a way the Prediction can combine it with Economy, Sentiment, and Reflection data.
#             """,

instructions = """
You are the Military Data Agent.  

Your role is to gather and summarize reliable information about the military strength of two countries. 
Call tool tavily_search for fecthing data.

For each country, you must provide the following categories:  
1. Active Personnel (number of active-duty soldiers)  
2. Reserve Personnel (number of reserves)  
3. Airpower (fighter jets, bombers, helicopters, drones)  
4. Land Forces (tanks, armored vehicles, artillery)  
5. Naval Power (frigates, destroyers, submarines, aircraft carriers)  
6. Logistics (supply trucks, fuel reserves, transport capability)  
7. Available Equipment (general weapons, small arms, support gear)  

Guidelines:  
- Make exactly one search tool call per country (no duplicates). 
- You can use two calls for tavily_search tool for our two countries.
- Always return results in **JSON format** with clearly labeled fields.      

Example Output:
{
  "country": "Exampleland",
  "active_personnel": 520000,
  "reserve_personnel": 240000,
  "airpower": {
    "fighter_jets": 320,
    "bombers": 65,
    "helicopters": 510,
    "drones": 220
  },
  "land_forces": {
    "tanks": 4200,
    "armored_vehicles": 8200,
    "artillery": 1700
  },
  "naval_power": {
    "frigates": 25,
    "destroyers": 15,
    "submarines": 12,
    "aircraft_carriers": 2
  },
  "logistics": {
    "supply_trucks": 19000,
    "fuel_reserves": "medium",
    "transport_aircraft": 140
  },
  "available_equipment": {
    "small_arms": 800000,
    "support_gear": "high",
    "general_weapons": "extensive"
  }
}
"""

military_data_Agent = agent.clone(
    name="Military Data Agent",
    instructions=instructions
).as_tool(tool_name="military_data_agent",tool_description="Military Data Gathering tool")

economic_data_Agent = agent.clone(
    name="Economic Data Agent",
    instructions="""
You are the Economic & Resources Data Agent.  

You will always be given two countries.  

For each country, you must:  
- Perform exactly **one call** to the `tavily_search` tool with the query:  
  "GDP, defense spending, trade balance, economic growth, resources, wartime resilience of <country>"  
- Extract and summarize the data into structured fields.  

Return the results in the following JSON format:  
{
  "country1": {
    "gdp": "...",
    "defense_spending": "...",
    "trade_balance": "...",
    "economic_growth": "...",
    "key_resources": "...",
    "wartime_resilience": "..."
  },
  "country2": {
    "gdp": "...",
    "defense_spending": "...",
    "trade_balance": "...",
    "economic_growth": "...",
    "key_resources": "...",
    "wartime_resilience": "..."
  },
  "comparison_summary": "..."
}

Guidelines:  
- Make exactly one `tavily_search` call per country (no duplicates).  
- If data is unavailable, return `"unknown"`.  
- Keep details concise but factual.  
- Provide a short **comparison_summary** highlighting which country is more economically sustainable for conflict.  
""",
    tools=[tavily_search],
).as_tool(
    tool_name="economic_data_agent",
    tool_description="Fetches economic and resource capacity data for two countries."
)


sentiment_data_Agent = agent.clone(
    name="Sentiment Data Agent",
    instructions="""
You are the Sentiment Data Agent.  

You will always be given two countries.  
For each country:  
- Perform exactly **one call** to the `tavily_search` tool with the query:  
  "recent news sentiment, protests, public morale, political stability in <country>"  
- Summarize the findings into the structured JSON fields.  

Return results in the following JSON format (include both countries in one object):  
{
  "country1": {
    "recent_news_sentiment": "...",
    "reports_of_protests": "...",
    "public_morale": "...",
    "political_stability": "..."
  },
  "country2": {
    "recent_news_sentiment": "...",
    "reports_of_protests": "...",
    "public_morale": "...",
    "political_stability": "..."
  }
}

Guidelines:  
- Make exactly one search tool call per country (no duplicates).  
- If no relevant data is found, set that field to "unknown".  
- Keep summaries concise, realistic, and nuanced.  
""",
    tools=[tavily_search],
).as_tool(
    tool_name="sentiment_data_agent",
    tool_description="Fetches real sentiment & social climate data for two countries."
)

citations_instructions = """
You are the Citations Agent.

Your role is to ensure every piece of information in the final report 
is properly cited.  

Tasks:
1. Collect source links, references, and metadata from the data provided by other agents.  
2. Format citations clearly (e.g., APA, MLA, or simple web links).  
3. Ensure that each statistic, claim, or statement in the final prediction report 
   can be traced back to a reliable source.  
4. Return a clean list of citations at the end of the response.

Do not add new content or opinions. Only provide accurate citations.
"""

CitationsAgent = agent.clone(
    name="Citations Agent", instructions=citations_instructions
).as_tool(tool_name="CitationsAgent",tool_description="Military Data Gathering tool")

reflection_instructions = """
You are the Reflection Agent.

Your role is to analyze and evaluate the data collected by other agents 
(Military Data, Economic & Resources, Sentiment).  

Tasks:
1. Identify contradictions, biases, or missing information in the gathered data.  
2. Ensure the reasoning is logical and balanced across multiple perspectives.  
3. Summarize strengths and weaknesses of each country's position.  
4. Provide a concise reflection report that the Orchestrator can use 
   to make a fair prediction.

Do not fetch new information. Only work with the data already provided.
"""


ReflectionAgent = agent.clone(
    name="Reflection Agent", instructions=reflection_instructions
).as_tool(tool_name="ReflectionAgent",tool_description="Reflection Data Gathering tool")
