import { MapContainer, TileLayer, CircleMarker, Polyline, Tooltip } from 'react-leaflet';
import type { Route } from '../types';

const COLORS = ['#e6194B', '#3cb44b', '#4363d8', '#f58231', '#911eb4', '#42d4f4', '#f032e6', '#9A6324', '#800000', '#808000', '#000075', '#469990'];

interface Props { routes: Route[]; }

export default function RouteMap({ routes }: Props) {
  // Center: Salt Lake City DC.
  const center: [number, number] = [40.76, -111.89];

  // Flatten layers so react-leaflet sees a single children list of LayerComponents.
  const layers: JSX.Element[] = [];
  routes.forEach((r, idx) => {
    const color = COLORS[idx % COLORS.length];
    const positions: [number, number][] = [
      center,
      ...r.stops.map((s) => [s.latitude, s.longitude] as [number, number]),
      center,
    ];
    layers.push(
      <Polyline key={`${r.route_id}-line`} positions={positions} pathOptions={{ color, weight: 3, opacity: 0.7 }} />
    );
    r.stops.forEach((s) => {
      layers.push(
        <CircleMarker
          key={`${r.route_id}-${s.location_code}`}
          center={[s.latitude, s.longitude]}
          radius={6}
          pathOptions={{ color, fillColor: color, fillOpacity: 0.8 }}
        >
          <Tooltip>
            <strong>{s.location_code}</strong><br />
            {r.route_id} · stop {s.sequence}<br />
            {s.weight_delivered_lbs.toFixed(0)} lbs · {s.cube_delivered.toFixed(0)} cube
          </Tooltip>
        </CircleMarker>
      );
    });
  });

  return (
    <MapContainer center={center} zoom={6} style={{ height: '400px', width: '100%' }}>
      <TileLayer
        attribution='&copy; OpenStreetMap'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {layers}
      <CircleMarker center={center} radius={9} pathOptions={{ color: '#222', fillColor: '#fff', fillOpacity: 1, weight: 3 }}>
        <Tooltip permanent>SLC-DC</Tooltip>
      </CircleMarker>
    </MapContainer>
  );
}
