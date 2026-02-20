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

## With Opik tracing

```bash
pip install -e ".[opik]"
```

This adds [Opik](https://www.comet.com/site/products/opik/) for experiment tracing and analysis. Set `OPIK_API_KEY` and `OPIK_WORKSPACE` in your `.env` file, then enable tracing in your experiment config with `opik_enabled=True`.

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
