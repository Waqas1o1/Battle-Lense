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
    ItemHelpers,
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
from reports import generate_report, save_report
from datetime import datetime
from pathlib import Path


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
gpt_llm = OpenAIChatCompletionsModel(model="gpt-4.1", openai_client=external_client)


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
  Country1: 90%
  Country2: 10%

Your goal is to provide the User with a clear, well-structured, and properly sourced prediction report.
"""

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

**important** After making plan → handoff to 'Prediction Agent'

Plan:
1. Military Data → Collects Global Firepower data.
2. Economy Data → GDP + defense spending comparison.
3. Sentiment Data → Collects recent news articles, protests, morale analysis.
4. Reflection → Notes both countries have nukes, so a “decisive victory” is unlikely.

Do Prediction → Outputs.
Now handoff plan to 'Prediction Agent'

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
    return {"country1": input_data.country1, "country2": input_data.country2}


RequirementGatheringAgent = Agent(
    model=gpt_llm,
    name="Requirement Gathering Agent",
    instructions=instructions,
    model_settings=ModelSettings(temperature=0.2),
    handoffs=[
        handoff(planning_agent, input_type=RequirementInput, on_handoff=on_handoff)
    ],
)

PROGRESS_STEPS = {
    "RequirementGatheringAgent": {
        "description": "Collecting the two countries for comparison...",
        "value": 10,
    },
    "PlanningAgent": {
        "description": "Designing the research plan...",
        "value": 20,
    },
    "Prediction Agent": {
        "description": "Starting the prediction process...",
        "value": 30,
    },
    "military_data_agent": {
        "description": "Gathering military strength and weapons data...",
        "value": 45,
    },
    "economic_data_agent": {
        "description": "Collecting economic and resource information...",
        "value": 60,
    },
    "sentiment_data_agent": {
        "description": "Analyzing public opinion and morale...",
        "value": 75,
    },
    "ReflectionAgent": {
        "description": "Checking consistency and refining reasoning...",
        "value": 80,
    },
    "CitationsAgent": {
        "description": "Compiling and verifying sources...",
        "value": 90,
    },
}


def calculate_progress(
    agent_name: str, last_progress: float = 0.0, _print: bool = True
) -> float:
    """
    Given the agent/tool name and last progress,
    return the updated progress percentage.
    """
    progress = last_progress
    if agent_name in PROGRESS_STEPS:
        step_info = PROGRESS_STEPS[agent_name]
        progress = step_info["value"]
        description = step_info["description"]

    # Reflection and Citations can be called multiple times
    # so just bump progress slightly without exceeding 95
    if agent_name in ["ReflectionAgent", "CitationsAgent"]:
        progress = min(progress + 2, 95)
    if _print:
        sys.stdout.flush()
        sys.stdout.write(
            f"\r📊 Progress: {progress:.1f}% - {description or f'Running {agent_name}...'}"
        )
    return progress


async def main():
    session = SQLiteSession("conversations.db")
    print("👋 Welcome! Which two countries do you want to compare?")
    progress = 0
    _break = False
    while True:
        user_input = input("You: ")
        async for event in Runner.run_streamed(
            RequirementGatheringAgent, user_input, session=session
        ).stream_events():
            if event.type == "agent_updated_stream_event":
                calculate_progress(event.new_agent.name, progress, False)
            elif event.type == "run_item_stream_event":
                if event.item.type == "tool_call_item":
                    tool_name = event.item.raw_item.name
                    print(event.item.agent.name, flush=True)
                    calculate_progress(tool_name, progress)
                elif (
                    event.item.type == "message_output_item"
                    and event.item.agent.name == "Prediction Agent"
                ):
                    final_result = ItemHelpers.text_message_output(event.item)
                    _break = True
                    break
                elif (
                    event.item.type == "message_output_item"
                    and event.item.agent.name == "Requirement Gathering Agent"
                ):
                    print(ItemHelpers.text_message_output(event.item))

        if _break:
            break

    if final_result:
        print("\n🔄 Generating report...")

        try:
            report = await generate_report(session, final_result, user_input)
            json_file, txt_file = save_report(report)

            print(f"✅ Report generated successfully!")
            print(f"📄 Text report saved: {txt_file}")
            print(f"📊 JSON report saved: {json_file}")

            # Optionally display a summary
            print(f"\n📋 Report Summary:")
            print(f"   - Generated at: {report['metadata']['timestamp']}")
            print(f"   - Query analyzed: {report['metadata']['user_query']}")
            print(f"   - Report files created in: reports/")

        except Exception as e:
            print(f"❌ Error generating report: {e}")
            # Fallback: save just the result
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                fallback_file = Path("reports") / f"analysis_result_{timestamp}.txt"
                Path("reports").mkdir(exist_ok=True)

                with open(fallback_file, "w", encoding="utf-8") as f:
                    f.write(
                        f"Analysis Result - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                    f.write("=" * 50 + "\n\n")
                    f.write(f"User Query: {user_input}\n\n")
                    f.write(f"Result:\n{final_result}")

                print(f"📄 Fallback report saved: {fallback_file}")
            except Exception as fallback_error:
                print(f"❌ Failed to save fallback report: {fallback_error}")

    print("\n👋 Thank you for using the country comparison tool!")


import asyncio

if __name__ == "__main__":
    asyncio.run(main())
