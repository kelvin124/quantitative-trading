# Quant trading agent team

This is a prompt-first scaffold for a personal quantitative trading prototype. The custom agents live in `.github/agents/`.

## Roles

- **Orchestrator** — only user-facing role; frames work, routes handoffs, and tracks decisions.
- **Quant researcher** — develops testable hypotheses and research plans.
- **Developer** — implements approved research and supporting tools.
- **QA** — independently checks implementation, data handling, and test validity.
- **Quant trader** — reviews whether results are plausible under practical trading constraints and gives iteration feedback.

## Suggested handoff

1. Ask the orchestrator to turn an idea into a research brief.
2. Have the quant researcher define the hypothesis, data needs, methodology, baselines, and failure criteria.
3. Have the developer implement the approved experiment.
4. Have QA verify correctness and rerun the relevant tests and backtest checks.
5. Have the quant trader review the verified results for costs, slippage, liquidity, turnover, capacity, drawdowns, and operational assumptions.
6. Return feedback to the researcher for another iteration, or document why the idea should be dropped.

Keep the initial project limited to research, backtesting, and paper trading. These prompts are workflow guidance, not a substitute for deterministic safeguards or human review.
