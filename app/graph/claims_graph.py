from typing import TypedDict
from app.services.observability import observed_node

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
from app.agents.vision_agent import analyze_visual_evidence
from app.agents.multimodal_evidence_agent import (
    analyze_cross_modal_evidence,
)


class ClaimState(TypedDict, total=False):
    claim_id: str
    raw_documents: str
    document_metadata: list
    image_files: list

    claim_reconstruction: dict

    policy_context: list
    coverage_analysis: dict

    evidence_analysis: dict
    visual_analysis: dict
    cross_modal_analysis: dict

    missing_information: dict

    adjudication: dict

    critic_feedback: dict

    final_assessment: dict


@observed_node
def reconstruction_node(
    state: ClaimState
):
    result = reconstruct_claim(
        state["raw_documents"]
    )

    return {
        "claim_reconstruction": result
    }


@observed_node
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


@observed_node
def visual_node(
    state: ClaimState,
):
    return {
        "visual_analysis": analyze_visual_evidence(
            state.get("image_files", [])
        )
    }


@observed_node
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


@observed_node
def missing_information_node(
    state: ClaimState
):
    result = analyze_missing_information(
        state["claim_reconstruction"],
        state["coverage_analysis"],
        state["evidence_analysis"],
        state.get("cross_modal_analysis"),
    )

    return {
        "missing_information": result
    }


@observed_node
def cross_modal_node(
    state: ClaimState,
):
    return {
        "cross_modal_analysis": analyze_cross_modal_evidence(
            state["claim_reconstruction"],
            state["evidence_analysis"],
            state.get("visual_analysis", {}),
        )
    }

@observed_node
def adjudication_node(
    state: ClaimState
):
    result = adjudicate_claim(
        state["claim_reconstruction"],
        state["coverage_analysis"],
        state["evidence_analysis"],
        state["missing_information"],
        state.get("cross_modal_analysis"),
    )

    return {
        "adjudication": result
    }

@observed_node
def critic_node(
    state: ClaimState
):
    result = critique_adjudication(
        state["claim_reconstruction"],
        state["coverage_analysis"],
        state["evidence_analysis"],
        state["missing_information"],
        state["adjudication"],
        state.get("cross_modal_analysis"),
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
        "visual_analysis",
        visual_node,
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
        "visual_analysis",
    )

    builder.add_edge(
        "visual_analysis",
        "policy_reasoning",
    )

    builder.add_edge(
        "policy_reasoning",
        "evidence_analysis",
    )

    builder.add_edge(
        "evidence_analysis",
        "cross_modal_evidence",
    )

    builder.add_node(
        "cross_modal_evidence",
        cross_modal_node,
    )

    builder.add_edge(
        "cross_modal_evidence",
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
