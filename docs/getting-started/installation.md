# Installation

Python 3.10+ required.

## Basic install

```bash
pip install -e .
```

## With LLM agent support

```bash
pip install -e ".[langchain]"
```

This adds `langchain-core` and `langchain-openai` for `LangChainNegotiationAgent`.

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
