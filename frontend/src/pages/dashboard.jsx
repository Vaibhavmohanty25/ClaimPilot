import { Link } from "react-router-dom";

function Dashboard() {
  return (
    <div className="min-h-screen bg-slate-100 p-10">
      <div className="mx-auto max-w-6xl">
        <h1 className="text-4xl font-bold text-slate-950">
          ClaimPilot
        </h1>

        <p className="mt-3 text-slate-500">
          AI-assisted motor insurance claims investigation
        </p>

        <Link
          to="/claims/new"
          className="mt-6 inline-block rounded-xl bg-indigo-600 px-5 py-3 font-medium text-white hover:bg-indigo-500"
        >
          Process New Claim
        </Link>
      </div>
    </div>
  );
}

export default Dashboard;