// L'ingresso dell'app React: per ora una sola pagina, la Day (todo 33).
import "./styles.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { DayPage } from "./components/DayPage";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <DayPage />
  </StrictMode>,
);
