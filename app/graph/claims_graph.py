from typing import TypedDict

from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from app.agents.claim_reconstruction import (
    reconstruct_claim,
)

from app.agents.policy_agent import (
    analyze_policy,
)

from app.agents.evidence_agent import (
    analyze_evidence,
)

from app.agents.missing_info_agent import (
    analyze_missing_information,
)

from app.agents.adjudication_agent import (
    adjudicate_claim,
)

from app.agents.critic_agent import (
    critique_adjudication,
)


class ClaimState(TypedDict, total=False):
    claim_id: str
    raw_documents: str

    claim_reconstruction: dict

    policy_context: list
    coverage_analysis: dict

    evidence_analysis: dict

    missing_information: dict

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


def policy_node(
    state: ClaimState
):
    result = analyze_policy(
        state["claim_reconstruction"]
    )

    return {
        "policy_context":
            result["policy_context"],

        "coverage_analysis":
            result["coverage_analysis"],
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


def missing_information_node(
    state: ClaimState
):
    result = analyze_missing_information(
        state["claim_reconstruction"],
        state["coverage_analysis"],
        state["evidence_analysis"],
    )

    return {
        "missing_information": result
    }

def adjudication_node(
    state: ClaimState
):
    result = adjudicate_claim(
        state["claim_reconstruction"],
        state["coverage_analysis"],
        state["evidence_analysis"],
        state["missing_information"],
    )

    return {
        "adjudication": result
    }

def critic_node(
    state: ClaimState
):
    result = critique_adjudication(
        state["claim_reconstruction"],
        state["coverage_analysis"],
        state["evidence_analysis"],
        state["missing_information"],
        state["adjudication"],
    )

    return {
        "critic_feedback": result
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

    builder.add_node(
        "missing_information",
        missing_information_node,
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
        "missing_information",
    )

    builder.add_node(
    "adjudication",
    adjudication_node,
    )

    builder.add_edge(
        "missing_information",
        "adjudication",
    )

    builder.add_node(
    "critic",
    critic_node,
    )

    builder.add_edge(
        "adjudication",
        "critic",
    )

    builder.add_edge(
        "critic",
        END,
    )

    return builder.compile()


claim_graph = build_claim_graph()