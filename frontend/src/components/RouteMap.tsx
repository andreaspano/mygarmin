// La traccia dell'attivita' su una mappa Leaflet. Le tessere sono di
// OpenStreetMap, come oggi `st.map` carica le sue da Carto: la traccia resta
// nel browser, alle tessere arriva solo la zona. Senza punti non c'e' mappa.
import "leaflet/dist/leaflet.css";

import { useEffect, useState } from "react";
import { MapContainer, Polyline, TileLayer } from "react-leaflet";

import { api } from "../api/client";

export function RouteMap({ activityId }: { activityId: number }) {
  const [points, setPoints] = useState<[number, number][] | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setPoints(null);
    api
      .route(activityId, controller.signal)
      .then((route) => setPoints(route.points))
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          console.error(error);
          setPoints([]);
        }
      });
    return () => controller.abort();
  }, [activityId]);

  if (!points || points.length === 0) return null;
  return (
    <section aria-label="Route">
      <h3 className="section-title">Route</h3>
      {/* La key rifa' la mappa a ogni attivita': `bounds` vale solo alla
          creazione. */}
      <MapContainer key={activityId} bounds={points} className="route-map" scrollWheelZoom={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Polyline positions={points} pathOptions={{ color: "#4a3aa7", weight: 4 }} />
      </MapContainer>
    </section>
  );
}
