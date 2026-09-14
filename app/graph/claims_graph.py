from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from app.agents.evidence_agent import analyze_evidence
from app.agents.claim_reconstruction import reconstruct_claim
from app.agents.policy_agent import analyze_policy


class ClaimState(TypedDict, total=False):
    claim_id: str
    raw_documents: str

    claim_reconstruction: dict

    policy_context: list
    coverage_analysis: dict

    evidence_analysis: dict
    missing_information: list

    adjudication: dict
    critic_feedback: dict

    final_assessment: dict


def reconstruction_node(state: ClaimState):
    result = reconstruct_claim(
        state["raw_documents"]
    )

    return {
        "claim_reconstruction": result
    }


def policy_node(state: ClaimState):
    result = analyze_policy(
        state["claim_reconstruction"]
    )

    return {
        "policy_context": result["policy_context"],
        "coverage_analysis": result["coverage_analysis"],
    }


def evidence_node(
    state: ClaimState
):

    result = analyze_evidence(
        state["claim_reconstruction"],
        state["coverage_analysis"],
    )

    return {
        "evidence_analysis": result
    }

def build_claim_graph():

    builder = StateGraph(
        ClaimState
    )

    builder.add_node(
        "reconstruct_claim",
        reconstruction_node,
    )

    builder.add_node(
        "policy_reasoning",
        policy_node,
    )

    builder.add_node(
        "evidence_analysis",
        evidence_node,
    )

    builder.add_edge(
        START,
        "reconstruct_claim",
    )

    builder.add_edge(
        "reconstruct_claim",
        "policy_reasoning",
    )

    builder.add_edge(
        "policy_reasoning",
        "evidence_analysis",
    )

    builder.add_edge(
        "evidence_analysis",
        END,
    )

    return builder.compile()


claim_graph = build_claim_graph()