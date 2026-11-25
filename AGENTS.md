# Project guardrails

This project is a personal-use quantitative trading prototype. Its initial scope is research, historical backtesting, and paper trading.

## Safety and scope

- Do not connect to a live brokerage account, place live orders, or request, store, or expose brokerage credentials.
- Do not treat an agent's output as authorization to trade. No strategy result is a promise of future performance or a personalized investment recommendation.
- Keep risk limits and any future execution controls deterministic and independently testable; never rely on a prompt as the sole safety control.
- Clearly label assumptions, limitations, and unverified claims. Do not invent data, results, sources, or test outcomes.

## Research and implementation quality

- Record data sources, time ranges, transformations, and assumptions that affect a result.
- Guard against look-ahead bias, leakage between training and test periods, survivorship bias, and unrealistic fills.
- Include reasonable fees, slippage, liquidity, and turnover assumptions when assessing a strategy.
- Prefer reproducible experiments, explicit baselines, out-of-sample evaluation, and focused tests over unsupported performance claims.
- Keep research, implementation, verification, and practical trading review as distinct responsibilities.
- Never commit secrets or personal financial data. Use synthetic or public sample data in examples.

## Collaboration

- The orchestrator is the sole point of contact with the user and coordinates role handoffs.
- Agents should return concise, evidence-based deliverables with open questions and limitations, not just conclusions.
- Do not expand the prototype into live trading without an explicit change in scope and a separate, reviewed safety design.
