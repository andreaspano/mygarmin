// L'ingresso dell'app React (todo 33). Dal todo 51 le pagine sono due e a
// sceglierle e' `App`.
import "./styles.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
