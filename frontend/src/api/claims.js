import axios from "axios";
import { createClaimJobClient } from "./claimJobs";

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
  timeout: 25000,
});

const jobs = createClaimJobClient({ api, storage: typeof window !== 'undefined' ? window.sessionStorage : undefined });
export const processClaim = jobs.process;
export const resumeClaim = jobs.resume;
export const getActiveClaimJob = jobs.getActiveJob;
export const resetClaimSubmission = jobs.resetSubmission;

export default api;
