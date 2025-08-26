"# Battle-Lense" 
# Conflict Outcome Prediction System

This project is an **AI-driven research and analysis framework** designed to predict the outcome of conflicts between two countries.  
It uses a team of specialized agents that gather, process, and summarize data across different domains such as military strength, economy, sentiment, and political stability.  

## 🔍 Key Features
- **Multi-Agent Architecture**: Each agent has a well-defined role (Military, Economic, Sentiment, etc.).
- **Real-World Data via Tavily**: Agents use the `tavily_search` tool to gather factual, up-to-date information from the internet.
- **Structured Outputs**: All agents return results in structured JSON, making it easy to process and feed into the Orchestrator.
- **Synthetic Data Option**: The system can also generate **fake but realistic data** for testing without hitting external APIs.
- **Prediction Orchestration**: An Orchestrator Agent coordinates data collection, compares findings, and produces a final conflict outcome prediction.

## 🧩 Agents Overview
### 1. **Sentiment Data Agent**
- Collects public morale, protests, political stability, and recent news sentiment.
- Uses one Tavily call **per country**.
- Returns concise JSON summaries.

### 2. **Economic Data Agent**
- Gathers GDP, defense spending, trade balance, resources, and wartime resilience.
- Uses one Tavily call **per country**.
- Provides a structured comparison of economic sustainability.

### 3. **Military Data Agent**
- (Planned/Implemented) Collects data on army size, airforce, navy, nuclear capability, and defense budget.
- Structured in JSON for easy comparison.

### 4. **Orchestrator Agent**
- Coordinates all sub-agents.
- Compiles results into a unified prediction of conflict outcomes.

## ⚙️ Tech Stack
- **Python 3.10+**
- **Async Agent Framework** (custom agents with cloning and tools integration)
- **Tavily API** for real-world search
- **pydantic** for structured data models
- **dotenv** for environment management

## 📂 Project Structure
