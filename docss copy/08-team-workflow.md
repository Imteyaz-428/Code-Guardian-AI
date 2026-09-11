# Team Workflow

## Branches

```text
main       → stable/demo-ready
feature/*  → feature development
research/* → experiments that may change architecture
```

## Commit examples

```text
feat: add repository file discovery
feat: add python ast parser
test: add ast parser tests
feat: calculate cyclomatic complexity
docs: update analyzer architecture
fix: handle syntax errors during parsing
```

## Pull requests

Every significant feature should include:
- what changed
- why
- how it was tested
- known limitations
- documentation updates when architecture changes

## Team split

Possible workstreams:

- Developer A: backend/repository/static analysis
- Developer B: ML/data/graph experiments
- Shared: architecture, integration, testing, documentation, demo

The exact split should be agreed by the team.

## Rule

Major architecture decisions must be recorded instead of silently diverging between implementations.
