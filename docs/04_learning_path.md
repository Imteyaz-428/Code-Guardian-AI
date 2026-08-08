# CodeGuardian AI — Master Learning Path

> Learn → Understand → Implement → Test → Document → Integrate

---

# 1. Purpose

This document defines the complete learning path for CodeGuardian AI.

The project combines several advanced areas:

- Software Engineering
- Compiler Fundamentals
- Static Code Analysis
- Graph Theory
- Graph Neural Networks
- Deep Learning
- Explainable AI
- AI Agents
- Backend Engineering
- Frontend Engineering
- Docker and Sandboxing
- MLOps
- Research Engineering

The goal is not simply to learn these technologies separately.

The goal is to understand how they work together to create CodeGuardian AI.

---

# 2. Learning Philosophy

Every topic follows this cycle:

```text
Learn Concept
     ↓
Understand Intuition
     ↓
Study Example
     ↓
Implement From Scratch
     ↓
Build Mini Project
     ↓
Test
     ↓
Document
     ↓
Integrate Into CodeGuardian
```

We should not move to the next major module simply because we watched a tutorial.

A module is considered complete only when its checkpoint is completed.

---

# 3. Complete Learning Path

```text
FOUNDATION
    ↓
PYTHON & SOFTWARE ENGINEERING
    ↓
COMPILER FUNDAMENTALS
    ↓
STATIC CODE ANALYSIS
    ↓
GRAPH THEORY
    ↓
GRAPH REPRESENTATION
    ↓
PYTORCH
    ↓
GRAPH NEURAL NETWORKS
    ↓
BUG PREDICTION
    ↓
EXPLAINABLE AI
    ↓
AI AGENTS
    ↓
AGENT MEMORY & REFLECTION
    ↓
CODE EXECUTION & SANDBOXING
    ↓
FASTAPI BACKEND
    ↓
DATABASE
    ↓
REACT FRONTEND
    ↓
SYSTEM INTEGRATION
    ↓
MLOPS
    ↓
DEPLOYMENT
    ↓
RESEARCH & OPTIMIZATION
```

---

# 4. Season 0 — Foundation

## Duration

1–2 weeks

## Goal

Understand the project and prepare the development environment.

---

## Module 0.1 — Project Vision

### Learn

- Problem definition
- Target users
- Project scope
- Functional requirements
- Non-functional requirements

### Output

`01_projectVision.md`

### Checkpoint

Explain CodeGuardian AI in 2 minutes without reading notes.

---

# Module 0.2 — System Architecture

### Learn

- Client-server architecture
- Service-oriented architecture
- Data flow
- Component responsibilities
- Separation of concerns

### Output

System architecture diagram.

### Checkpoint

Explain how a GitHub URL travels through the entire system.

---

# Module 0.3 — Git & GitHub

### Learn

- Git basics
- Branches
- Merge
- Pull Request
- Issues
- Commit conventions
- GitHub Projects

### Practice

Create branches:

```text
main
develop
feature/*
```

### Checkpoint

Create a feature branch, make a change, commit it, and merge it.

---

# Module 0.4 — Development Environment

### Setup

- Python
- Node.js
- Git
- Docker
- PostgreSQL
- VS Code
- Virtual environment

### Checkpoint

Run every required tool successfully.

---

# 5. Season 1 — Python & Software Engineering

## Duration

1–2 weeks

This is a short revision phase because Python is already familiar.

---

## Module 1.1 — Advanced Python

### Learn

- OOP
- Classes
- Inheritance
- Abstract classes
- Decorators
- Generators
- Iterators
- Context managers
- Type hints
- Dataclasses
- Exceptions

---

## Module 1.2 — Clean Code

### Learn

- SOLID
- DRY
- Separation of concerns
- Dependency injection
- Design patterns

---

## Module 1.3 — Testing

### Learn

- pytest
- Unit testing
- Integration testing
- Mocking
- Fixtures

### Checkpoint

Create tests for a small Python project.

---

# 6. Season 2 — Compiler Fundamentals

## Duration

2 weeks

This is one of the most important foundations.

---

# Module 2.1 — How Code Becomes Execution

### Learn

```text
Source Code
     ↓
Lexer
     ↓
Parser
     ↓
AST
     ↓
Intermediate Representation
     ↓
Machine Code
```

Understand:

- Lexing
- Parsing
- Syntax
- Semantics
- AST
- Compilation

### Checkpoint

Explain the difference between source code, parse tree, and AST.

---

# Module 2.2 — AST

### Learn

- Python `ast`
- Nodes
- Visitors
- Traversal
- Node relationships

### Build

A Python AST analyzer.

Input:

```python
def add(a, b):
    return a + b
```

Output:

```text
FunctionDef
 ├── arguments
 │    ├── a
 │    └── b
 │
 └── Return
      └── BinOp
```

### Checkpoint

Extract from a repository:

- Functions
- Classes
- Imports
- Variables
- Function calls

---

# 7. Season 3 — Static Code Analysis

## Duration

3–4 weeks

---

# Module 3.1 — AST-Based Analysis

Build:

```text
Repository
     ↓
Python Files
     ↓
AST
     ↓
Functions
     ↓
Metrics
```

Extract:

- Function length
- Number of branches
- Loops
- Function calls
- Nested depth

---

# Module 3.2 — Control Flow Graph

Learn:

- Nodes
- Edges
- Branches
- Loops
- Paths

Example:

```text
        start
          |
       condition
       /       \
     yes       no
      |         |
      A         B
       \       /
        finish
```

---

# Module 3.3 — Call Graph

Represent:

```text
main()
  |
  +---- login()
  |
  +---- database()
            |
            +---- query()
```

---

# Module 3.4 — Data Flow

Track how data moves through functions.

Example:

```text
input
  ↓
validation
  ↓
processing
  ↓
database
```

---

# Module 3.5 — Complexity

Learn:

- Cyclomatic complexity
- Function complexity
- Nesting depth
- Number of dependencies

---

## Season 3 Checkpoint

Given a Python repository, CodeGuardian should produce:

```text
Files
Functions
Classes
AST
CFG
Call Graph
Complexity Metrics
```

---

# 8. Season 4 — Graph Theory

## Duration

1–2 weeks

---

# Module 4.1 — Graph Fundamentals

Learn:

- Nodes
- Edges
- Directed graphs
- Undirected graphs
- Weighted graphs
- Paths
- Cycles
- Degree

---

# Module 4.2 — Graph Algorithms

Learn:

- BFS
- DFS
- Shortest path
- Connected components

---

# Module 4.3 — NetworkX

Build:

- Graph creation
- Graph traversal
- Visualization
- Graph statistics

---

# Checkpoint

Represent a complete Python repository as a graph.

---

# 9. Season 5 — Code Graph Representation

## Duration

2 weeks

Now combine previous seasons.

```text
AST
 +
CFG
 +
Call Graph
 +
Data Flow
     ↓
Code Graph
```

---

# Module 5.1 — Node Features

Possible features:

```text
node_type
function_length
complexity
number_of_calls
number_of_parameters
number_of_branches
```

---

# Module 5.2 — Edge Features

Examples:

```text
CALLS
FOLLOWS
DEPENDS_ON
CONTAINS
DATA_FLOW
```

---

# Module 5.3 — Graph Dataset

Convert repository graphs into ML-ready data.

Target structure:

```text
Graph
 ├── Nodes
 ├── Edges
 ├── Node Features
 ├── Edge Features
 └── Labels
```

---

# 10. Season 6 — Deep Learning Fundamentals

## Duration

2–3 weeks

---

# Module 6.1 — PyTorch

Learn:

- Tensor
- Dataset
- DataLoader
- Model
- Forward pass
- Loss
- Optimizer
- Backpropagation
- Training loop

---

# Module 6.2 — Neural Network Fundamentals

Understand:

```text
Input
 ↓
Linear Layer
 ↓
Activation
 ↓
Linear Layer
 ↓
Output
```

Learn:

- Activation functions
- Cross entropy
- Binary classification
- Overfitting
- Regularization

---

# Module 6.3 — Model Evaluation

Learn:

- Accuracy
- Precision
- Recall
- F1
- Confusion Matrix
- ROC-AUC

---

# Checkpoint

Train a normal neural network on a small classification dataset.

---

# 11. Season 7 — Graph Neural Networks

## Duration

4–5 weeks

This is the core Deep Learning section.

---

# Module 7.1 — Why GNN?

Understand why traditional neural networks don't naturally understand code graphs.

---

# Module 7.2 — Message Passing

Core idea:

```text
Node
 ↓
Receive information from neighbors
 ↓
Aggregate
 ↓
Update representation
```

---

# Module 7.3 — GCN

Learn:

- Graph convolution
- Neighbor aggregation
- Node embeddings

---

# Module 7.4 — GraphSAGE

Learn:

- Sampling
- Aggregation
- Inductive learning

---

# Module 7.5 — GAT

Learn:

- Attention
- Attention weights
- Important neighbors

---

# Module 7.6 — PyTorch Geometric

Learn:

- Data
- Batch
- MessagePassing
- GCNConv
- SAGEConv
- GATConv

---

# Module 7.7 — GNN Training

Train:

```text
Code Graph
     ↓
GNN
     ↓
Node Embeddings
     ↓
Classifier
     ↓
Bug Probability
```

---

# Checkpoint

A trained GNN predicts whether a function is likely to contain a defect.

---

# 12. Season 8 — Bug Prediction Engine

## Duration

2–3 weeks

---

# Module 8.1 — Dataset

Start with a suitable public dataset.

Potential sources:

- BugsInPy
- CodeXGLUE
- GitHub bug-fix data

Dataset selection will be finalized after studying the available data.

---

# Module 8.2 — Data Preprocessing

```text
Raw Dataset
 ↓
Clean
 ↓
Parse
 ↓
Graph
 ↓
Features
 ↓
Labels
```

---

# Module 8.3 — Training Pipeline

```text
Dataset
 ↓
Train
 ↓
Validation
 ↓
Test
 ↓
Model Checkpoint
```

---

# Module 8.4 — Inference

Input:

```text
Repository
```

Output:

```text
Function A → 91%
Function B → 14%
Function C → 83%
```

---

# 13. Season 9 — Explainable AI

## Duration

1–2 weeks

Goal:

Don't just say:

```text
Bug Probability = 92%
```

Explain why.

Possible explanation:

```text
High complexity
+
Many dependencies
+
Risky API usage
+
Important graph neighbors
```

Study:

- Attention visualization
- Feature importance
- Graph explanations

---

# 14. Season 10 — AI Agents

## Duration

3–4 weeks

---

# Module 10.1 — Agent Fundamentals

Learn:

- LLM
- Tool
- State
- Planning
- Memory
- Agent loop

---

# Module 10.2 — Planner Agent

Input:

```text
Bug Report
```

Output:

```text
1. Inspect function
2. Inspect dependencies
3. Find similar code
4. Generate patch
5. Run tests
```

---

# Module 10.3 — Bug Analyzer

Analyzes:

- Source code
- Graph information
- GNN prediction
- Static analysis results

---

# Module 10.4 — Fix Generator

Generates a candidate patch.

---

# Module 10.5 — Reviewer

Reviews generated patch before execution.

---

# Module 10.6 — Reflection

If tests fail:

```text
Patch
 ↓
Test
 ↓
FAIL
 ↓
Analyze Error
 ↓
Improve Patch
 ↓
Test Again
```

---

# Module 10.7 — Memory

Store:

```text
Bug
Fix
Test Result
Repository
Language
```

This allows future agents to reuse previous knowledge.

---

# Checkpoint

The agent can generate and revise a patch based on test feedback.

---

# 15. Season 11 — Code Execution & Sandboxing

## Duration

2–3 weeks

---

# Module 11.1 — Docker

Learn:

- Images
- Containers
- Volumes
- Networks
- Resource limits

---

# Module 11.2 — Sandbox

Never execute AI-generated code directly on the host.

Flow:

```text
Generated Patch
 ↓
Docker Container
 ↓
Install Dependencies
 ↓
Run Tests
 ↓
Collect Logs
 ↓
Destroy Container
```

---

# Module 11.3 — Test Runner

Automate:

```text
pytest
coverage
exit code
stdout
stderr
execution time
```

---

# Checkpoint

AI-generated patches can be tested automatically inside an isolated environment.

---

# 16. Season 12 — Backend

## Duration

3–4 weeks

---

# Module 12.1 — FastAPI

Learn:

- Routes
- Request/Response
- Pydantic
- Dependency Injection
- Middleware
- Background tasks

---

# Module 12.2 — PostgreSQL

Store:

- Users
- Repositories
- Analyses
- Functions
- Predictions
- Agent runs
- Patches
- Test results

---

# Module 12.3 — Redis

Use for:

- Caching
- Job state
- Temporary data
- Background task coordination

---

# Module 12.4 — API Design

Main endpoints:

```text
POST /repositories
POST /analysis
GET  /analysis/{id}
GET  /predictions/{id}
POST /fix
POST /execute
GET  /reports/{id}
```

---

# Checkpoint

Frontend can communicate with the complete backend.

---

# 17. Season 13 — Frontend

## Duration

3–4 weeks

---

# Module 13.1 — React

Learn:

- Components
- Props
- State
- Hooks
- Routing
- API integration

---

# Module 13.2 — Dashboard

Build:

```text
Repository Dashboard
       ↓
Risk Overview
       ↓
File Explorer
       ↓
Function Analysis
       ↓
Graph Visualization
       ↓
AI Fix
       ↓
Test Results
```

---

# Module 13.3 — Code Viewer

Use a code editor such as Monaco Editor.

Display:

- Source code
- Risk highlights
- Suggested changes
- Diff

---

# Module 13.4 — Graph Visualization

Visualize:

- AST
- CFG
- Call Graph
- Important graph nodes

---

# Checkpoint

A user can analyze a repository entirely through the web interface.

---

# 18. Season 14 — System Integration

## Duration

2 weeks

Connect everything:

```text
Frontend
 ↓
FastAPI
 ↓
Repository Manager
 ↓
Static Analysis
 ↓
Graph Builder
 ↓
GNN
 ↓
Agents
 ↓
Docker
 ↓
Results
 ↓
Frontend
```

---

# 19. Season 15 — MLOps

## Duration

2 weeks

Learn:

- MLflow
- Model versioning
- Experiment tracking
- Dataset versioning
- Training reproducibility

---

# 20. Season 16 — Testing

## Duration

1–2 weeks

Build:

- Unit tests
- Integration tests
- Model tests
- API tests
- Agent tests
- End-to-end tests

Target:

```text
Reliable system
```

Not necessarily 100% coverage.

---

# 21. Season 17 — Deployment

## Duration

2 weeks

Learn:

- Docker Compose
- Environment variables
- CI/CD
- GitHub Actions
- Logging
- Monitoring

---

# 22. Season 18 — Research & Optimization

## Duration

Continuous

Compare:

```text
GCN
vs
GraphSAGE
vs
GAT
```

Perform:

- Hyperparameter tuning
- Ablation studies
- Error analysis
- Performance benchmarking

---

# 23. Season 19 — Final Product

Final system:

```text
                CodeGuardian AI

                      │
                      ▼

              GitHub Repository
                      │
                      ▼
             Repository Analyzer
                      │
                      ▼
              Static Analysis
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
         AST         CFG       Call Graph
          │           │           │
          └───────────┼───────────┘
                      ▼
                 Code Graph
                      │
                      ▼
                  GNN Model
                      │
                      ▼
                Risk Prediction
                      │
                      ▼
                 Explanation
                      │
                      ▼
                Agent Planner
                      │
             ┌────────┼────────┐
             ▼        ▼        ▼
          Analyzer  Fixer   Reviewer
             │        │        │
             └────────┼────────┘
                      ▼
                 Test Runner
                      │
                 ┌────┴────┐
                 │         │
               PASS       FAIL
                 │         │
                 │    Reflection
                 │         │
                 │       Retry
                 │         │
                 └────┬────┘
                      ▼
               Verified Patch
                      │
                      ▼
                  Dashboard
```

---

# 24. Completion Criteria

CodeGuardian AI is considered complete when it can:

- [ ] Accept a GitHub repository
- [ ] Clone and analyze it
- [ ] Parse Python source code
- [ ] Generate AST
- [ ] Generate CFG
- [ ] Generate Call Graph
- [ ] Build code graphs
- [ ] Generate graph features
- [ ] Run a trained GNN
- [ ] Predict bug-prone functions
- [ ] Explain predictions
- [ ] Start an AI agent workflow
- [ ] Generate a candidate patch
- [ ] Run tests in Docker
- [ ] Detect failures
- [ ] Reflect and retry
- [ ] Produce a verified patch
- [ ] Display results through React
- [ ] Store analysis history
- [ ] Track experiments
- [ ] Run automated tests
- [ ] Deploy the system

---

# 25. Important Rule

Do not attempt to build all of these simultaneously.

Always work in this order:

```text
Understand
    ↓
Small Experiment
    ↓
Mini Project
    ↓
Production Module
    ↓
Integration
```

If a concept is not understood, stop and learn it before continuing.

---

# 26. Definition of Done

A module is DONE only when:

- [ ] Concept understood
- [ ] Notes written
- [ ] Implementation completed
- [ ] Tests written
- [ ] Example verified
- [ ] Documentation updated
- [ ] Git commit created
- [ ] Module integrated

---

# 27. Final Learning Outcome

After completing CodeGuardian AI, the developer should be comfortable discussing:

### Programming

Python, TypeScript, Git

### Compiler Engineering

AST, CFG, Call Graph, Data Flow

### Machine Learning

Classification, evaluation, training

### Deep Learning

PyTorch, GNN, GCN, GraphSAGE, GAT

### AI Engineering

Agents, tools, memory, reflection

### Backend

FastAPI, PostgreSQL, Redis

### Frontend

React, visualization, code editors

### Infrastructure

Docker, CI/CD, deployment

### Research

Datasets, experiments, benchmarks, ablation studies

---

# Final Principle

CodeGuardian AI is not simply a collection of technologies.

The objective is to understand how these technologies interact to solve a real software engineering problem.

The most important skill gained from this project is not the ability to use a specific framework.

It is the ability to:

**Understand a complex problem → design a system → research possible solutions → build the components → evaluate them → integrate them → deploy them.**