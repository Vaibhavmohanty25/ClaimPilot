from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from app.agents.claim_reconstruction import (
    reconstruct_claim,
)


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


def reconstruction_node(
    state: ClaimState
):

    result = reconstruct_claim(
        state["raw_documents"]
    )

    return {
        "claim_reconstruction": result
    }


def build_claim_graph():

    builder = StateGraph(
        ClaimState
    )

    builder.add_node(
        "reconstruct_claim",
        reconstruction_node,
    )

    builder.add_edge(
        START,
        "reconstruct_claim",
    )

    builder.add_edge(
        "reconstruct_claim",
        END,
    )

    return builder.compile()


claim_graph = build_claim_graph()