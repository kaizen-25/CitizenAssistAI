import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { SessionProvider } from "./hooks/useSession";
import { I18nProvider } from "./hooks/useT";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <I18nProvider>
      <SessionProvider>
        <App />
      </SessionProvider>
    </I18nProvider>
  </StrictMode>,
);
