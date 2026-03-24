# Architectural Constraints

## Dependency Layers

Dependencies flow **ONLY** in this direction:

```
Types → Config → Domain → Service → API → UI
```

Lower layers MUST NOT import from higher layers.

### Layer Definitions

| Layer   | Purpose                             | May Import From               |
|---------|-------------------------------------|-------------------------------|
| types   | Pure data types, enums, dataclasses | nothing                       |
| config  | Configuration & settings            | types                         |
| domain  | Business logic & rules              | types, config                 |
| service | External services, DB access        | types, config, domain         |
| api     | HTTP handlers, routes               | types, config, domain, service|
| ui      | User interfaces                     | all layers                    |
| infra   | Infrastructure, scripts             | all layers                    |

---

## File Organization
- One class per file for non-trivial classes
- Tests live alongside source: `foo.py` → `test_foo.py`
- No circular imports
- Shared utilities go in `utils/` (types layer)

## Naming Conventions
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Files: `snake_case`

## Error Handling
- Use typed exceptions, not bare `Exception`
- Log errors with context (what was being attempted)
- Return `Result` types for expected failures; raise for unexpected ones
