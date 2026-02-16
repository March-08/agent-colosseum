# LLM Agents

`LangChainNegotiationAgent` is a game-agnostic LLM agent. You supply a system prompt that describes the game rules and output format; the agent receives the current game state and allowed actions from the runner.

## Installation

```bash
pip install -e ".[langchain]"
```

## Usage

```python
from dotenv import load_dotenv
from neg_env import LangChainNegotiationAgent
from neg_env.prompts import SYSTEM_PROMPT_UNFAIR

load_dotenv()  # loads OPENAI_API_KEY or OPENROUTER_API_KEY

agent = LangChainNegotiationAgent(
    agent_id="strategic",
    provider="openai",          # or "openrouter"
    model="gpt-4o-mini",
    system_prompt=SYSTEM_PROMPT_UNFAIR,
    temperature=0.7,
)
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `agent_id` | `"llm"` | Unique identifier |
| `system_prompt` | generic prompt | Game-specific prompt (rules, actions, output format) |
| `provider` | `"openai"` | `"openai"` or `"openrouter"` |
| `model` | `"gpt-4o-mini"` | Model name |
| `temperature` | `0.4` | Sampling temperature |
| `api_key` | from env | API key (falls back to `OPENAI_API_KEY` or `OPENROUTER_API_KEY`) |
| `runnable` | `None` | Custom LangChain runnable (overrides provider/model) |

## Built-in prompts

| Prompt | Game | Strategy |
|--------|------|----------|
| `SYSTEM_PROMPT_FAIR` | unfair-split | Cooperative — aims for fair split |
| `SYSTEM_PROMPT_UNFAIR` | unfair-split | Strategic — maximizes payoff |
| `SYSTEM_PROMPT_AUCTION` | first-price-auction | Strategic — chat first, bid below valuation |

```python
from neg_env.prompts import SYSTEM_PROMPT_FAIR, SYSTEM_PROMPT_UNFAIR, SYSTEM_PROMPT_AUCTION
```

## How it works

1. The agent receives a `TurnState` (game state, messages, allowed actions).
2. It serializes the state into a human-readable prompt and sends it to the LLM.
3. The LLM responds with JSON: `{"message": "...", "action": "...", "payload": {...}}`.
4. The agent parses the response and returns an `AgentResponse`.

If the LLM returns an invalid action, it falls back to the first allowed action. If the LLM call fails, the agent sends an error message and uses the fallback action.

## Custom runnable

You can pass any LangChain-compatible runnable instead of using the built-in provider:

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda

llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

def run(inp: dict[str, str]) -> str:
    out = llm.invoke([SystemMessage(content=inp["system"]), HumanMessage(content=inp["user"])])
    return out.content

agent = LangChainNegotiationAgent(
    agent_id="custom",
    runnable=RunnableLambda(run),
    system_prompt=SYSTEM_PROMPT_UNFAIR,
)
```
