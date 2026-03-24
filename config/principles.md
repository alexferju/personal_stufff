# The Agent Factory — Golden Principles

## Core Philosophy
**Agent = Model + Harness.** The model contains intelligence. The harness makes it useful.

The harness constrains what the agent can do (architectural boundaries, dependency rules),
informs it about what it *should* do (context engineering, documentation), and verifies
that it did it correctly (testing, linting, CI validation).

---

## Harness Engineering Principles

### 1. Humans Steer, Agents Execute
- Engineers design environments, specify intent, and build feedback loops
- Agents write the code — never manually write code an agent can write
- The engineer's job shifts from implementation to system design

### 2. Depth-First Decomposition
- Break large goals into atomic building blocks
- Each task must be completable by a single agent in one turn
- Complete prerequisites before unlocking complex tasks

### 3. Context Engineering
- Give agents exactly the context they need — no more, no less
- Organize information so the agent can reason over it
- Treat agents like new teammates: onboard them on principles, norms, culture

### 4. Architectural Constraints via Mechanical Enforcement
- Dependencies flow in one direction only: Types → Config → Domain → Service → API → UI
- No layer may import from a higher layer
- Structural rules are enforced by tests, not convention

### 5. Feedback Loops & Self-Repair
- When an agent struggles, identify what is missing (tools, guardrails, docs)
- Feed the gap back into the system — always via the agent itself
- Prompt agents aggressively to verify their own work by running tests

### 6. Entropy Management
- Code entropy accumulates — agents drift from golden principles over time
- Run cleanup agents regularly to scan for deviations
- Encode golden patterns as examples, not just rules

---

## Code Quality Standards
- Functions do one thing
- Names are self-documenting
- Tests accompany all non-trivial code
- No magic numbers or hardcoded values
- Errors are handled explicitly, not silently swallowed

## Security Standards
- No secrets in code — use environment variables
- Validate all external inputs
- No SQL concatenation — use parameterized queries
- No shell injection — use subprocess lists, never strings
