# System Architecture

## Project Name

**CodeGuardian AI**

AI-Powered Autonomous Code Intelligence Platform

---

# Purpose

This document describes the complete architecture of CodeGuardian AI.

It explains:

- High-Level Architecture
- Component Responsibilities
- Data Flow
- AI Pipeline
- Deep Learning Pipeline
- Agent Workflow
- Backend Architecture
- Frontend Architecture
- Database Architecture

This document acts as the blueprint for the entire project.

---

# High-Level Architecture

```

                    React Frontend

                           │

                           ▼

                  FastAPI Backend API

                           │

──────────────────────────────────────────────────────────────

                    Repository Manager

                           │

                           ▼

                  GitHub Repository Clone

                           │

                           ▼

                  Static Analysis Engine

                           │

──────────────────────────────────────────────────────────────

AST Parser

↓

Control Flow Graph

↓

Call Graph

↓

Data Flow Graph

↓

Complexity Analyzer

↓

Graph Builder

──────────────────────────────────────────────────────────────

↓

Graph Neural Network

↓

Bug Prediction Engine

↓

Explainability Engine

↓

Risk Report

──────────────────────────────────────────────────────────────

↓

AI Agent System

↓

Planner Agent

↓

Bug Analyzer Agent

↓

Fix Generator Agent

↓

Reviewer Agent

↓

Reflection Agent

↓

Memory Agent

↓

Execution Agent

──────────────────────────────────────────────────────────────

↓

Docker Sandbox

↓

Run Tests

↓

Collect Logs

↓

Retry

↓

Generate Patch

──────────────────────────────────────────────────────────────

↓

PostgreSQL

Redis

FAISS

──────────────────────────────────────────────────────────────

↓

React Dashboard

```

---

# System Modules

The project is divided into multiple independent modules.

```

Frontend

↓

Backend

↓

Repository Analysis

↓

Static Analysis

↓

Graph Generation

↓

Deep Learning

↓

AI Agents

↓

Execution Engine

↓

Database

↓

Dashboard

```

Each module has a single responsibility.

---

# Module Responsibilities

## 1 Repository Manager

Responsibilities

- Clone GitHub repository
- Download latest version
- Maintain repository cache
- Detect programming language
- Send repository for analysis

Input

GitHub URL

Output

Local Repository

---

## 2 Static Analysis Engine

Responsible for understanding source code without executing it.

Tasks

- Parse source code
- Generate AST
- Generate CFG
- Generate Call Graph
- Generate Data Flow Graph
- Measure complexity

Output

Graph Representation

---

## 3 Graph Builder

Responsible for converting compiler outputs into machine learning graphs.

Input

AST

CFG

Call Graph

Output

Graph Data Structure

Used by

PyTorch Geometric

---

## 4 Graph Neural Network

Responsible for predicting risky functions.

Possible Models

- GCN
- GraphSAGE
- GAT

Input

Graph

Output

Risk Score

---

## 5 Explainability Engine

Responsible for explaining predictions.

Example

Risk Score

92%

Reasons

- Deep nesting
- Dangerous API
- High complexity
- Similar historical bug

---

## 6 AI Agent System

Responsible for autonomous fixing.

Agents

Planner

↓

Analyzer

↓

Retriever

↓

Fix Generator

↓

Reviewer

↓

Reflection

↓

Memory

↓

Executor

---

## 7 Docker Execution Engine

Responsible for validating generated fixes.

Tasks

- Build Docker Container
- Execute Tests
- Capture Logs
- Return Results

---

## 8 Dashboard

Responsible for visualizing everything.

Features

- Repository View
- File Explorer
- Risk Heatmap
- Graph Viewer
- AI Timeline
- Patch Viewer
- Test Results

---

# Backend Architecture

```

React

↓

REST API

↓

FastAPI

↓

Services

↓

AI

↓

Database

```

The backend follows a modular architecture.

---

# Frontend Architecture

```

Dashboard

↓

Repository

↓

File

↓

Function

↓

Prediction

↓

Patch

↓

Report

```

---

# AI Workflow

Step 1

User submits GitHub Repository.

↓

Step 2

Repository Manager clones repository.

↓

Step 3

Static Analysis starts.

↓

Step 4

Generate AST.

↓

Step 5

Generate CFG.

↓

Step 6

Generate Call Graph.

↓

Step 7

Create Graph.

↓

Step 8

Run Graph Neural Network.

↓

Step 9

Predict Risk.

↓

Step 10

Explain Prediction.

↓

Step 11

AI Agent analyzes risky function.

↓

Step 12

Generate Fix.

↓

Step 13

Run Tests.

↓

Step 14

Pass

↓

Generate Patch

Else

↓

Reflection

↓

Retry

---

# Data Flow

```

GitHub URL

↓

Repository

↓

Parser

↓

Graph

↓

GNN

↓

Prediction

↓

Agent

↓

Patch

↓

Docker

↓

Verified Patch

↓

Dashboard

```

---

# Design Principles

The project follows these principles.

## Modular

Every module is independent.

---

## Scalable

New agents can be added without changing existing modules.

---

## Explainable

Every prediction should have reasoning.

---

## Secure

Generated code never executes on the host machine.

Always use Docker.

---

## Research Friendly

Models can be replaced easily.

GCN

↓

GraphSAGE

↓

GAT

↓

Graph Transformer

---

# Future Architecture

Version 2

- Multi-language support
- Java
- C++
- JavaScript

Version 3

- VSCode Extension
- GitHub App
- Cloud Deployment

Version 4

- Team Collaboration
- Real-time Analysis
- Multi-Agent Collaboration

---

# Final Architecture Summary

```

GitHub Repository

↓

Static Analysis

↓

Graph Builder

↓

Graph Neural Network

↓

Prediction

↓

Explainability

↓

AI Agents

↓

Docker Sandbox

↓

Verified Patch

↓

Dashboard

```

This architecture serves as the foundation for every future implementation in CodeGuardian AI.