// La traccia dell'attivita' su una mappa Leaflet. Le tessere sono di
// OpenStreetMap, come oggi `st.map` carica le sue da Carto: la traccia resta
// nel browser, alle tessere arriva solo la zona. I punti li carica
// `TrainingCard`, che mostra "Open the route map" solo se ci sono.
import "leaflet/dist/leaflet.css";

import { MapContainer, Polyline, TileLayer } from "react-leaflet";

export function RouteMap({ activityId, points }: { activityId: number; points: [number, number][] }) {
  return (
    <section aria-label="Route">
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
