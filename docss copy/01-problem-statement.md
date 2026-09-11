# Problem Statement

## Problem

Large repositories are difficult to review completely. Static analysis finds known patterns, while AI coding agents can understand repositories and generate changes. Developers still need to know which code is risky, why it is risky, how changes propagate, and whether an AI-generated repair actually works.

## Proposed solution

Code Guardian combines structural code analysis, dependency/graph analysis, rule-based risk scoring, machine-learning research, natural-language explanations, AI-assisted repair, isolated execution, and verification.

## Target users

- Software developers
- Code reviewers
- Student/research teams
- Engineering teams
- Security/reliability researchers

## Initial scope

Python repositories first, with an architecture that can later support additional languages.

## Non-goals

The initial system will not try to replace general-purpose coding agents, guarantee detection of all bugs, autonomously deploy production code, train a foundation model from scratch, or support every language immediately.
