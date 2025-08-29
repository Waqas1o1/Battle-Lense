import os, sys
import asyncio
from agents import (
    Agent,
    Runner,
    OpenAIChatCompletionsModel,
    AsyncOpenAI,
    handoff,
    set_tracing_disabled,
    ModelSettings,
    RunContextWrapper,
    SQLiteSession,
)
from dotenv import load_dotenv
from tools_agents import (
    military_data_Agent,
    economic_data_Agent,
    sentiment_data_Agent,
    ReflectionAgent,
    CitationsAgent,
    progress_tool_fn
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from pydantic import BaseModel, Field

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
gimini_llm = OpenAIChatCompletionsModel(
    model="gemini-2.5-flash", openai_client=external_client
)
external_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY_2"))
gpt_llm = OpenAIChatCompletionsModel(
    model="gpt-4.1", openai_client=external_client
)



instructions = """
You are the Lead Prediction Agent (Orchestrator).  
Your role is to coordinate the research process and produce a fair, well-reasoned conflict outcome prediction.  

Instructions:  
- Always keep the user updated about progress using progress_tool_fn. 
- Before calling each data tool like Military, Economy, Sentiment, call `Progress Tool` with percentage and status.  
- Call every tool → military_data_agent, economic_data_agent, sentiment_data_agent Agent only one time
- Call ReflectionAgent and CitationsAgent as many time as you need.
- Accept structured input from the Planning Agent (countries + research plan).  
- Do not fetch information directly. Instead, call specialized Tool Agents when needed:  
  - Military Data Agent → for military strength comparison.  
  - Economic Data Agent → for economic and resource stats.  
  - Sentiment Analysis Agent → for public morale and support.  
  - Reflection Agent → to check for contradictions and ensure balanced reasoning.  
  - Citations Agent → to compile sources and references.  
- Call each data fetching tool oncse (like Military, Economic, Sentiment) until agent rase any error.

- Once data is collected, synthesize it using a weighted scoring model:  
  - Military Strength = 40%  
  - Economy & Resources = 30%  
  - Public Sentiment = 20%  
  - Geography/Allies (qualitative factor) = 10%  

- Output a final report in natural language with these sections:  
  1. **Prediction**: Probability percentages for each country.  
  2. Output prediction is in following formate:
  Country1: 90%
  Country2: 10%

Your goal is to provide the User with a clear, well-structured, and properly sourced prediction report.
""" 

prediction_agent = Agent(
    model=gpt_llm,
    name="Prediction Agent",
    instructions=instructions,
    tools=[
        progress_tool_fn,
        military_data_Agent,
        economic_data_Agent,
        sentiment_data_Agent,
        CitationsAgent,
        ReflectionAgent
    ],
    model_settings=ModelSettings(temperature=0.2),
)

instructions = """
You are the Planning Agent.  
Your job is to receive the countries and share the following research plan for Predicting the outcome of a potential conflict between these two countries.  

**important** After making plan → handoff to 'Prediction Agent'

Plan:
Military Data → Collects Global Firepower data.

Economy Data → GDP + defense spending comparison.

Sentiment Data → Collects recent news articles, protests, morale analysis.

Reflection → Notes both countries have nukes, so a “decisive victory” is unlikely.

Do Prediction → Outputs:

"""


planning_agent = Agent(
    model=gimini_llm,
    name="Planning Agent",
    instructions=f"""
                {RECOMMENDED_PROMPT_PREFIX}
                {instructions}
                """,
    handoffs=[handoff(prediction_agent)],
)

instructions = """
You are the Requirement Gathering Agent.  
You are a friendly agent.

Project Context:
We are building a Conflict Prediction System.  
The system will compare two countries in a hypothetical conflict scenario, 
and later other agents will analyze military strength, economy, public sentiment, 
and other resources to predict possible outcomes. 

Rules:
- If neither country is provided, ask for both.  
- If only one country is provided, ask for the missing one.  
- Once both countries are collected, handoff to Planning Agent in JSON format like this:  
{
  "country1": "CountryA",
  "country2": "CountryB"
}

- Do not include explanations or extra text.  
- When both countries are present, stop asking questions and hand off to the Planning Agent.
"""

class RequirementInput(BaseModel):
    country1: str = Field(default=None, description="Name of the first country")
    country2: str = Field(default=None, description="Name of the second country")

async def on_handoff(ctx: RunContextWrapper[None], input_data: RequirementInput):
    return {"country1":input_data.country1,"country2":input_data.country2}

RequirementGatheringAgent = Agent(
    model=gpt_llm,
    name="Requirement Gathering Agent",
    instructions=instructions,
    model_settings=ModelSettings(temperature=0.2),
    handoffs=[handoff(planning_agent,input_type=RequirementInput,on_handoff=on_handoff)],
)
async def main():
    session = SQLiteSession("conversations.db") 

    print("👋 Welcome! Which two countries do you want to compare?")
    while True:
        user_input = input("You: ")
        response = await Runner.run(
            RequirementGatheringAgent,
            user_input,
            session=session 
        )
        print("🤖 Agent:", response.final_output)
        if response.last_agent.name not in ("Requirement Gathering Agent","Planning Agent"):
            break

import asyncio
if __name__ == "__main__":
    asyncio.run(main())