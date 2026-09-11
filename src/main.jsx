import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import AppErrorBoundary from "./AppErrorBoundary";
import "./styles.css";
import "./trustCenter.css";
import "./accessibility.css";
import "./notifications.css";
import "./visualFixes.css";
import "./desktopReadability.css";

createRoot(document.getElementById("root")).render(<AppErrorBoundary><App /></AppErrorBoundary>);
