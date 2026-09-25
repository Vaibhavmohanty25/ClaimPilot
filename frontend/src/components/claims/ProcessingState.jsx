import { LoaderCircle } from "lucide-react";

function ProcessingState() {
  return (
    <div className="rounded-2xl border border-indigo-200 bg-indigo-50 p-6">
      <div className="flex items-start gap-4">
        <LoaderCircle
          className="mt-0.5 animate-spin text-indigo-600"
          size={24}
        />

        <div>
          <h3 className="font-semibold text-slate-900">
            ClaimPilot is analyzing the claim
          </h3>

          <p className="mt-1 text-sm text-slate-600">
            This can take a little while because documents,
            images, policy evidence and multiple AI agents are
            being evaluated.
          </p>

          <div className="mt-4 space-y-2 text-sm text-slate-600">
            <p>Preparing submitted evidence...</p>
            <p>Running multimodal claim analysis...</p>
            <p>Evaluating policy and supporting evidence...</p>
            <p>Preparing the preliminary assessment...</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProcessingState;