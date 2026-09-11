# Research Direction

## Main hypothesis

> Structural representations of software can improve code-risk localization compared with relying only on conventional source-code metrics.

## Experimental ladder

1. Rule-based risk scoring
2. Classical ML using engineered features
3. Graph representation without learning
4. GNN-based prediction
5. Risk-aware repair
6. Verification loop measuring whether accepted patches reduce measured risk while preserving tests

## Desired demonstration

A repository enters the system; structural information is extracted; risky components are ranked; the system explains the ranking; an AI repair is proposed; the repair runs in isolation; tests execute; the repository is re-analyzed; and the patch is accepted or rejected using evidence.

## Research caution

Do not claim the system detects all bugs, guarantees security, or fixes every vulnerability. Report measured performance and limitations.
