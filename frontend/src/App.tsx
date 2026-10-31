import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Assess } from "./pages/Assess";
import { Confirm } from "./pages/Confirm";
import { Documents } from "./pages/Documents";
import { Landing } from "./pages/Landing";
import { Packet } from "./pages/Packet";
import { Results } from "./pages/Results";
import { Scheme } from "./pages/Scheme";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Landing />} />
          <Route path="/assess" element={<Assess />} />
          <Route path="/confirm" element={<Confirm />} />
          <Route path="/results" element={<Results />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/scheme/:id" element={<Scheme />} />
          <Route path="/packet" element={<Packet />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
