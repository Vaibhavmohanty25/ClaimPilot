# ClaimPilot

ClaimPilot is a GenAI-powered insurance claims assistant that analyzes claim documents, reasons over policy coverage, identifies inconsistencies, and prepares a preliminary claim assessment for human review.

The project is designed as a multi-agent system for insurance workflows, with a focus on motor insurance claims.

It is being built to simulate how an insurance claims team could use Generative AI to reduce manual document review and speed up early-stage claim assessment.

---

## Project Goal

Insurance claims usually involve multiple documents such as:

- Claim forms
- Insurance policies
- Police reports
- Repair estimates
- Invoices
- Emails
- Supporting documents
- Damage photographs

Manually reviewing all of these documents can take time and may lead to missed inconsistencies.

ClaimPilot aims to automate the first layer of claim analysis by using GenAI agents that can:

- Understand claim documents
- Reconstruct what happened
- Retrieve relevant policy clauses
- Reason about coverage
- Detect contradictions
- Identify unsupported claim items
- Flag cases that require human review

The system does not try to replace the human adjuster. Instead, it acts as an AI claims copilot that prepares a structured and explainable assessment.

---

# Current Workflow

```text
Claim Documents
      |
      v
Claim Reconstruction Agent
      |
      v
Policy Retrieval using RAG
      |
      v
Policy Reasoning Agent
      |
      v
Evidence Analysis Agent
      |
      v
Human Review / Further Processing