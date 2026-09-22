import { BrowserRouter, Routes, Route } from "react-router-dom";

import AppLayout from "./components/layout/AppLayout";
import Dashboard from "./pages/Dashboard";
import NewClaim from "./pages/NewClaim";
import ClaimReview from "./pages/ClaimReview";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/claims/new" element={<NewClaim />} />
          <Route path="/claims/review" element={<ClaimReview />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;