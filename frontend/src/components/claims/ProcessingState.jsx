import { LoaderCircle } from "lucide-react";

const stageLabels = {
  uploading: 'Uploading claim evidence',
  queued: 'Your claim is in the queue',
  processing: 'ClaimPilot is analyzing your claim',
  completed: 'Your assessment is ready',
};

function ProcessingState({ progress }) {
  const elapsed = Math.max(0, Math.floor(progress?.elapsed_seconds || 0));
  return (
    <div className="rounded-2xl border border-indigo-200 bg-indigo-50 p-6" role="status" aria-live="polite">
      <div className="flex items-start gap-4">
        <LoaderCircle className="mt-0.5 shrink-0 animate-spin text-indigo-600" size={24} />
        <div>
          <h3 className="font-semibold text-slate-900">
            {stageLabels[progress?.status] || 'Checking your claim’s progress'}
          </h3>
          <p className="mt-1 text-sm text-slate-600">
            {progress?.message || 'Reconnecting to your saved claim…'}
          </p>
          {progress?.status === 'queued' && Number.isFinite(progress.queue_position) && (
            <p className="mt-3 text-sm font-medium text-indigo-900">Queue position: {progress.queue_position}</p>
          )}
          {Number.isFinite(progress?.elapsed_seconds) && (
            <p className="mt-3 text-sm text-slate-600">Elapsed: {Math.floor(elapsed / 60)}m {elapsed % 60}s</p>
          )}
          {progress?.connection_lost && (
            <p className="mt-3 text-sm text-amber-800">{progress.connection_message}</p>
          )}
          <p className="mt-3 text-xs leading-5 text-slate-500">
            Progress updates automatically. You can return to this page or refresh after your upload has been accepted.
          </p>
        </div>
      </div>
    </div>
  );
}

export default ProcessingState;
