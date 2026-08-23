import { MapContainer, TileLayer, Polyline, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { RiskBand } from "../types";
import { bandColor } from "../lib";

export interface CorridorPolyline {
  id: string;
  name: string;
  
  positions: [number, number][];
  band: RiskBand;
}

export interface RoutePolyline {
  id: string;
  name: string;
  positions: [number, number][];
  color?: string;
}

export interface MapPanelProps {
  corridors?: CorridorPolyline[];
  routes?: RoutePolyline[];
  
  center?: [number, number];
  
  zoom?: number;
  
  height?: number | string;
  className?: string;
}

const DEFAULT_CENTER: [number, number] = [18, 58];
const DEFAULT_ZOOM = 4;

const TILE_URL = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

export function MapPanel({
  corridors = [],
  routes = [],
  center = DEFAULT_CENTER,
  zoom = DEFAULT_ZOOM,
  height = 360,
  className,
}: MapPanelProps) {
  return (
    <div
      className={`overflow-hidden rounded-lg border border-slate-200 ${className ?? ""}`}
      style={{ height }}
    >
      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={false}
        style={{ height: "100%", width: "100%", background: "#EEF2F4" }}
      >
        <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />

        {routes.map((route) => (
          <Polyline
            key={route.id}
            positions={route.positions}
            pathOptions={{
              color: route.color ?? "#64748b",
              weight: 1.5,
              opacity: 0.6,
              dashArray: "4 6",
            }}
          >
            <Tooltip sticky>{route.name}</Tooltip>
          </Polyline>
        ))}

        {corridors.map((corridor) => (
          <Polyline
            key={corridor.id}
            positions={corridor.positions}
            pathOptions={{
              color: bandColor(corridor.band),
              weight: 5,
              opacity: 0.9,
            }}
          >
            <Tooltip sticky>
              {corridor.name} â€” {corridor.band}
            </Tooltip>
          </Polyline>
        ))}
      </MapContainer>
    </div>
  );
}

export default MapPanel;
