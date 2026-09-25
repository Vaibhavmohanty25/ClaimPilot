import { useLocation, useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  Camera,
  CheckCircle2,
  CircleDollarSign,
  FileText,
  Info,
  ShieldCheck,
  TriangleAlert,
  UserCheck,
  XCircle,
} from "lucide-react";

function ClaimReview() {
  const location = useLocation();
  const navigate = useNavigate();

  const claim = location.state?.claim;

  if (!claim) {
    return (
      <div className="mx-auto max-w-5xl">
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <h1 className="text-2xl font-bold text-slate-950">
            No claim loaded
          </h1>

          <p className="mt-2 text-slate-500">
            Process a claim first to open the review workspace.
          </p>

          <button
            type="button"
            onClick={() => navigate("/claims/new")}
            className="mt-6 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-500"
          >
            Process a Claim
          </button>
        </div>
      </div>
    );
  }

  const reconstruction = claim.reconstruction || {};
  const visual = claim.visual_analysis || {};
  const coverage = claim.coverage_analysis || {};
  const evidence = claim.evidence_analysis || {};
  const crossModal = claim.cross_modal_analysis || {};
  const missing = claim.missing_information || {};
  const adjudication = claim.adjudication || {};
  const critic = claim.critic_feedback || {};

  const claimedAmount =
    reconstruction.claimed_amount ??
    reconstruction.repair_estimate_total ??
    null;

  const payableAmount =
    adjudication.recommended_payable_amount ?? null;

  function formatCurrency(value) {
    if (value === null || value === undefined) {
      return "Not available";
    }

    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(value);
  }

  function getReadinessStyle(status) {
    if (status === "READY") {
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    }

    if (status === "READY_WITH_CAUTION") {
      return "bg-amber-50 text-amber-700 border-amber-200";
    }

    if (status === "NOT_READY") {
      return "bg-red-50 text-red-700 border-red-200";
    }

    return "bg-slate-100 text-slate-700 border-slate-200";
  }

  function getRecommendationStyle(status) {
    if (status === "APPROVE") {
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    }

    if (status === "ESCALATE_FOR_HUMAN_REVIEW") {
      return "bg-amber-50 text-amber-700 border-amber-200";
    }

    if (status === "REQUEST_MORE_INFORMATION") {
      return "bg-red-50 text-red-700 border-red-200";
    }

    return "bg-slate-100 text-slate-700 border-slate-200";
  }

  function pretty(value) {
    if (!value) return "Not available";

    return value
      .replaceAll("_", " ")
      .toLowerCase()
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  return (
    <div className="mx-auto max-w-7xl">
      {/* Header */}

      <button
        type="button"
        onClick={() => navigate("/claims/new")}
        className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 transition hover:text-slate-900"
      >
        <ArrowLeft size={16} />
        Back to claim intake
      </button>

      <div className="mt-6 flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-indigo-600">
            CLAIM INVESTIGATION
          </p>

          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">
            Claim Review
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            Claim ID:{" "}
            <span className="font-semibold text-slate-700">
              {claim.claim_id}
            </span>
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <span
            className={`rounded-full border px-4 py-2 text-xs font-semibold ${getReadinessStyle(
              missing.claim_readiness
            )}`}
          >
            {pretty(missing.claim_readiness)}
          </span>

          <span
            className={`rounded-full border px-4 py-2 text-xs font-semibold ${getRecommendationStyle(
              adjudication.recommendation
            )}`}
          >
            {pretty(adjudication.recommendation)}
          </span>
        </div>
      </div>

      {/* Main status banner */}

      {missing.claim_readiness === "NOT_READY" && (
        <section className="mt-8 rounded-2xl border border-red-200 bg-red-50 p-6">
          <div className="flex gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-red-100 text-red-600">
              <TriangleAlert size={22} />
            </div>

            <div>
              <h2 className="text-lg font-semibold text-red-900">
                More information required
              </h2>

              <p className="mt-1 max-w-3xl text-sm leading-6 text-red-700">
                ClaimPilot cannot complete a reliable assessment with the
                currently submitted evidence. Review the missing information
                below before continuing adjudication.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Summary cards */}

      <section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          icon={ShieldCheck}
          label="Coverage"
          value={pretty(coverage.coverage_status)}
          subtext={
            coverage.coverage_confidence !== undefined
              ? `${Math.round(coverage.coverage_confidence * 100)}% confidence`
              : "No confidence available"
          }
        />

        <SummaryCard
          icon={FileText}
          label="Evidence"
          value={pretty(evidence.evidence_status)}
          subtext={
            evidence.evidence_confidence !== undefined
              ? `${Math.round(evidence.evidence_confidence * 100)}% confidence`
              : "No confidence available"
          }
        />

        <SummaryCard
          icon={CircleDollarSign}
          label="Claimed Amount"
          value={formatCurrency(claimedAmount)}
          subtext="Reported claim value"
        />

        <SummaryCard
          icon={UserCheck}
          label="AI Recommendation"
          value={pretty(adjudication.recommendation)}
          subtext={
            adjudication.human_review_required
              ? "Human review required"
              : "No human review flag"
          }
        />
      </section>

      {/* Main evidence workspace */}

      <section className="mt-8 grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        {/* Left */}

        <div className="space-y-6">
          {/* Incident */}

          <Panel
            title="Incident Reconstruction"
            subtitle="What ClaimPilot reconstructed from submitted documents"
            icon={FileText}
          >
            <div className="grid gap-5 md:grid-cols-2">
              <InfoField
                label="Incident"
                value={reconstruction.incident_summary}
              />

              <InfoField
                label="Claim Type"
                value={reconstruction.claim_type}
              />

              <InfoField
                label="Date"
                value={reconstruction.incident_date}
              />

              <InfoField
                label="Location"
                value={reconstruction.incident_location}
              />
            </div>

            {(!reconstruction.incident_summary ||
              !reconstruction.incident_date ||
              !reconstruction.incident_location) && (
              <div className="mt-5 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
                <Info
                  size={19}
                  className="mt-0.5 shrink-0 text-amber-600"
                />

                <p className="text-sm leading-6 text-amber-800">
                  Incident reconstruction is incomplete because the submitted
                  evidence does not contain enough claim context.
                </p>
              </div>
            )}
          </Panel>

          {/* Visual Evidence */}

          <Panel
            title="Visual Evidence"
            subtitle="What the damage images actually show"
            icon={Camera}
          >
            {visual.images_analyzed?.length > 0 ? (
              <>
                <div className="mb-5 flex flex-wrap gap-2">
                  {visual.images_analyzed.map((image) => (
                    <span
                      key={image}
                      className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700"
                    >
                      {image}
                    </span>
                  ))}
                </div>

                {visual.visible_damage?.length > 0 ? (
                  <div className="space-y-3">
                    {visual.visible_damage.map((damage, index) => (
                      <div
                        key={`${damage.region}-${index}`}
                        className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-semibold text-slate-900">
                            {pretty(damage.region)}
                          </span>

                          <SeverityBadge severity={damage.severity} />

                          {damage.confidence !== undefined && (
                            <span className="text-xs text-slate-500">
                              {Math.round(damage.confidence * 100)}% confidence
                            </span>
                          )}
                        </div>

                        <p className="mt-2 text-sm leading-6 text-slate-600">
                          {damage.description}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState text="No visible damage findings were returned." />
                )}

                {visual.regions_not_visible?.length > 0 && (
                  <div className="mt-5">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Regions not visible
                    </p>

                    <div className="mt-2 flex flex-wrap gap-2">
                      {visual.regions_not_visible.map((region) => (
                        <span
                          key={region}
                          className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600"
                        >
                          {pretty(region)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <EmptyState text="No damage photographs were analyzed." />
            )}
          </Panel>

          {/* Cross Modal */}

          <Panel
            title="Cross-Modal Evidence"
            subtitle="How the documents and visual evidence agree"
            icon={BadgeCheck}
          >
            <div className="grid gap-4 md:grid-cols-2">
              <EvidenceList
                title="Supported"
                items={crossModal.supported_items}
                variant="success"
              />

              <EvidenceList
                title="Unverifiable"
                items={crossModal.unverifiable_items}
                variant="warning"
              />

              <EvidenceList
                title="Visually Unsupported"
                items={crossModal.visually_unsupported_items}
                variant="danger"
              />

              <EvidenceList
                title="Risk Flags"
                items={crossModal.risk_flags}
                variant="danger"
              />
            </div>
          </Panel>
        </div>

        {/* Right */}

        <div className="space-y-6">
          {/* Missing Information */}

          <Panel
            title="Missing Information"
            subtitle="What needs to be collected before the claim can progress"
            icon={AlertTriangle}
          >
            <EvidenceList
              title="Missing Documents"
              items={missing.missing_documents}
              variant="danger"
            />

            <div className="mt-5">
              <EvidenceList
                title="Blocking Issues"
                items={missing.blocking_issues}
                variant="danger"
              />
            </div>

            <div className="mt-5">
              <EvidenceList
                title="Next Actions"
                items={missing.recommended_next_actions}
                variant="info"
              />
            </div>
          </Panel>

          {/* Adjudication */}

          <Panel
            title="Preliminary Adjudication"
            subtitle="ClaimPilot's current decision based on available evidence"
            icon={UserCheck}
          >
            <div
              className={`rounded-xl border p-4 ${getRecommendationStyle(
                adjudication.recommendation
              )}`}
            >
              <p className="text-xs font-semibold uppercase tracking-wide">
                Recommendation
              </p>

              <p className="mt-1 text-lg font-bold">
                {pretty(adjudication.recommendation)}
              </p>
            </div>

            <div className="mt-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Coverage Position
              </p>

              <p className="mt-2 text-sm leading-6 text-slate-700">
                {adjudication.coverage_position || "Not available"}
              </p>
            </div>

            <div className="mt-5 rounded-xl bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Recommended Payable
              </p>

              <p className="mt-2 text-2xl font-bold text-slate-950">
                {formatCurrency(payableAmount)}
              </p>
            </div>

            {adjudication.next_action && (
              <div className="mt-5">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Next Action
                </p>

                <p className="mt-2 text-sm leading-6 text-slate-700">
                  {adjudication.next_action}
                </p>
              </div>
            )}
          </Panel>

          {/* Critic */}

          <Panel
            title="Critic Verification"
            subtitle="Independent verification of the AI adjudication"
            icon={ShieldCheck}
          >
            <div className="flex items-start gap-3">
              {critic.verification_status === "VERIFIED" ? (
                <CheckCircle2
                  size={23}
                  className="mt-0.5 shrink-0 text-emerald-600"
                />
              ) : (
                <XCircle
                  size={23}
                  className="mt-0.5 shrink-0 text-red-600"
                />
              )}

              <div>
                <p className="font-semibold text-slate-900">
                  {pretty(critic.verification_status)}
                </p>

                <p className="mt-1 text-sm text-slate-500">
                  {critic.critic_confidence !== undefined
                    ? `${Math.round(
                        critic.critic_confidence * 100
                      )}% verification confidence`
                    : "Confidence unavailable"}
                </p>
              </div>
            </div>

            <div className="mt-5 space-y-3">
              <VerificationRow
                label="Consistent with evidence"
                valid={critic.adjudication_consistent_with_evidence}
              />

              <VerificationRow
                label="Consistent with policy"
                valid={critic.adjudication_consistent_with_policy}
              />

              <VerificationRow
                label="Human review handled correctly"
                valid={critic.human_review_handled_correctly}
              />
            </div>
          </Panel>
        </div>
      </section>
    </div>
  );
}

function SummaryCard({ icon: Icon, label, value, subtext }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-700">
        <Icon size={20} />
      </div>

      <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>

      <p className="mt-2 text-lg font-semibold text-slate-950">
        {value}
      </p>

      <p className="mt-1 text-xs text-slate-500">
        {subtext}
      </p>
    </div>
  );
}

function Panel({ title, subtitle, icon: Icon, children }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
          <Icon size={20} />
        </div>

        <div>
          <h2 className="font-semibold text-slate-950">
            {title}
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            {subtitle}
          </p>
        </div>
      </div>

      <div className="mt-6">{children}</div>
    </section>
  );
}

function InfoField({ label, value }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>

      <p className="mt-2 text-sm leading-6 text-slate-800">
        {value || "Not provided"}
      </p>
    </div>
  );
}

function SeverityBadge({ severity }) {
  const styles = {
    severe: "bg-red-50 text-red-700",
    moderate: "bg-amber-50 text-amber-700",
    minor: "bg-emerald-50 text-emerald-700",
  };

  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
        styles[severity?.toLowerCase()] ||
        "bg-slate-100 text-slate-700"
      }`}
    >
      {severity || "unknown"}
    </span>
  );
}

function EvidenceList({ title, items = [], variant = "info" }) {
  const styles = {
    success: {
      icon: CheckCircle2,
      iconClass: "text-emerald-600",
    },
    warning: {
      icon: AlertTriangle,
      iconClass: "text-amber-600",
    },
    danger: {
      icon: XCircle,
      iconClass: "text-red-600",
    },
    info: {
      icon: Info,
      iconClass: "text-indigo-600",
    },
  };

  const selected = styles[variant] || styles.info;
  const Icon = selected.icon;

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </p>

      {items?.length > 0 ? (
        <div className="mt-3 space-y-2">
          {items.map((item, index) => (
            <div
              key={`${String(item)}-${index}`}
              className="flex items-start gap-2"
            >
              <Icon
                size={16}
                className={`mt-0.5 shrink-0 ${selected.iconClass}`}
              />

              <p className="text-sm leading-5 text-slate-700">
                {typeof item === "string"
                  ? item.replaceAll("_", " ")
                  : JSON.stringify(item)}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-slate-400">
          None
        </p>
      )}
    </div>
  );
}

function VerificationRow({ label, valid }) {
  return (
    <div className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3">
      <span className="text-sm text-slate-700">
        {label}
      </span>

      {valid ? (
        <CheckCircle2
          size={18}
          className="text-emerald-600"
        />
      ) : (
        <XCircle
          size={18}
          className="text-red-600"
        />
      )}
    </div>
  );
}

function EmptyState({ text }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-center text-sm text-slate-500">
      {text}
    </div>
  );
}

export default ClaimReview;