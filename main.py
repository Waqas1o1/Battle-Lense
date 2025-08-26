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
)
from dotenv import load_dotenv
from tools_agents import (
    military_data_Agent,
    economic_data_Agent,
    sentiment_data_Agent,
    ReflectionAgent,
    CitationsAgent,
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
  Country1: 10%
  Country2: 90%


Your goal is to provide the User with a clear, well-structured, and properly sourced prediction report.
"""
#   2. **Strengths & Weaknesses**: Key comparative insights.  
#   3. **Reasoning**: Explanation of how evidence supports the outcome.  
#   4. **Citations**: Reliable sources provided by the Citations Agent.  
prediction_agent = Agent(
    model=gpt_llm,
    name="Prediction Agent",
    instructions=instructions,
    tools=[
        military_data_Agent,
        economic_data_Agent,
        sentiment_data_Agent,
        CitationsAgent,
        ReflectionAgent,
    ],
    model_settings=ModelSettings(temperature=0.2),
)
instructions = """
You are the Planning Agent.  
Your job is to receive the countries and share the following research plan for Predicting the outcome of a potential conflict between these two countries.  
**important** After making plan → handoff to Prediction Agent

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
# Requment gatyhering Agent
instructions = """
You are the Requirement Gathering Agent.  
Your job is to interact with the user and collect the names of two countries that they want to compare in a conflict scenario.  

Instructions:  
- Ask the user for two country names if they are not provided. 
- Once you have both names, structure them into JSON format:  
  {"country1": "CountryA", "country2": "CountryB"}  
- Do not proceed with analysis.  
- HandOff the collected information to the Planning Agent.
"""


class RequirementInput(BaseModel):
    country1: str = Field(default=None, description="Name of the first country")
    country2: str = Field(default=None, description="Name of the second country")


RequirementGatheringAgent = Agent(
    model=gimini_llm,
    name="Requirement Gathering Agent",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
                {instructions}
                """,
    model_settings=ModelSettings(temperature=0.2),
    # output_type=RequirementInput,
    handoffs=[handoff(planning_agent)],
)


async def main():

    # Pass JSON to Military Data Agent
    user_input = "India and Pakistan"

    # Pass JSON to Military Data Agent
    response = await Runner.run(RequirementGatheringAgent, user_input)
    print(response.final_output)


if __name__ == "__main__":
    asyncio.run(main())
