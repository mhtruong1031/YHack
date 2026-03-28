import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { BackgroundVideo } from "./components/BackgroundVideo";
import "./styles/global.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <div className="app-shell">
      <BackgroundVideo />
      <div className="app-main">
        <App />
      </div>
    </div>
  </StrictMode>
);
