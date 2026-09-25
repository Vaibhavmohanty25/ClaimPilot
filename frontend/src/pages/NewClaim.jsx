import { useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  ArrowLeft,
  ArrowRight,
  FileCheck2,
  Files,
  Image as ImageIcon,
} from "lucide-react";

import FileDropzone from "../components/claims/FileDropzone";
import ProcessingState from "../components/claims/ProcessingState";
import { processClaim } from "../api/claims";

function NewClaim() {
  const navigate = useNavigate();

  const [files, setFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState("");

  const documentFiles = files.filter(
    (file) => !file.type.startsWith("image/")
  );

  const imageFiles = files.filter((file) =>
    file.type.startsWith("image/")
  );

  async function handleSubmit(event) {
    event.preventDefault();

    if (files.length === 0) {
      setError("Please select at least one claim file.");
      return;
    }

    setError("");
    setIsProcessing(true);

    try {
      const claimResult = await processClaim(files);

      navigate("/claims/review", {
        state: {
          claim: claimResult,
        },
      });
    } catch (err) {
      console.error("Claim processing failed:", err);

      if (err.response) {
        const backendMessage =
          err.response?.data?.detail ||
          err.response?.data?.message;

        setError(
          typeof backendMessage === "string"
            ? backendMessage
            : "The backend returned an error while processing the claim."
        );
      } else if (err.code === "ECONNABORTED") {
        setError(
          "Claim processing timed out. Check the FastAPI logs and try again."
        );
      } else {
        setError(
          "Could not connect to the ClaimPilot backend. Make sure Uvicorn is running on port 8000."
        );
      }
    } finally {
      setIsProcessing(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl">
      <button
        type="button"
        onClick={() => navigate("/")}
        className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft size={16} />
        Back to dashboard
      </button>

      <div className="mt-6">
        <p className="text-sm font-semibold text-indigo-600">
          CLAIM INTAKE
        </p>

        <h1 className="mt-2 text-3xl font-bold text-slate-950">
          Process New Claim
        </h1>

        <p className="mt-2 max-w-3xl text-slate-500">
          Upload all documents and damage photographs related to the
          same claim. ClaimPilot will evaluate the complete evidence
          set together before producing a final preliminary conclusion.
        </p>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_320px]">
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <div className="mb-5">
            <h2 className="text-lg font-semibold text-slate-950">
              Claim evidence bundle
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Add multiple files before submitting. All selected files
              will be processed as one claim.
            </p>
          </div>

          <FileDropzone
            files={files}
            onFilesChange={setFiles}
            disabled={isProcessing}
          />

          {files.length > 0 && (
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-center gap-2">
                  <Files size={18} className="text-indigo-600" />

                  <p className="font-medium text-slate-900">
                    Documents
                  </p>
                </div>

                <p className="mt-2 text-2xl font-bold text-slate-950">
                  {documentFiles.length}
                </p>

                <p className="text-xs text-slate-500">
                  Claim forms, police reports, estimates, PDFs
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-center gap-2">
                  <ImageIcon size={18} className="text-indigo-600" />

                  <p className="font-medium text-slate-900">
                    Damage Images
                  </p>
                </div>

                <p className="mt-2 text-2xl font-bold text-slate-950">
                  {imageFiles.length}
                </p>

                <p className="text-xs text-slate-500">
                  JPG, JPEG, PNG and WEBP evidence
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {isProcessing && (
            <div className="mt-5">
              <ProcessingState />
            </div>
          )}

          <div className="mt-6 flex flex-col gap-4 border-t border-slate-200 pt-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-slate-700">
                {files.length === 0
                  ? "No files selected"
                  : `${files.length} files ready for analysis`}
              </p>

              {files.length > 0 && (
                <p className="mt-1 text-xs text-slate-500">
                  These files will be evaluated together as one claim.
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={files.length === 0 || isProcessing}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {isProcessing
                ? "Processing Claim..."
                : "Process Complete Claim"}

              {!isProcessing && <ArrowRight size={17} />}
            </button>
          </div>
        </form>

        <aside className="h-fit rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
            <FileCheck2 size={21} />
          </div>

          <h2 className="mt-4 font-semibold text-slate-950">
            Recommended evidence set
          </h2>

          <p className="mt-2 text-sm leading-6 text-slate-500">
            A stronger claim assessment usually includes multiple
            sources of evidence.
          </p>

          <ul className="mt-5 space-y-3 text-sm text-slate-600">
            <li>Claim form</li>
            <li>Police or incident report</li>
            <li>Repair estimate</li>
            <li>One or more damage photographs</li>
          </ul>

          <div className="mt-6 rounded-xl bg-indigo-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
              Important
            </p>

            <p className="mt-2 text-sm leading-6 text-indigo-900">
              Upload all related files before clicking Process Complete
              Claim. ClaimPilot evaluates the evidence bundle together.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default NewClaim;