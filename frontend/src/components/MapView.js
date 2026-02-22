import React, { useMemo, useEffect, useRef, useState, useCallback } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { FaBus } from 'react-icons/fa';

// Fix for default marker icons in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom marker icons for dark theme
const createCustomIcon = (color, size = 24) => {
  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        background-color: ${color};
        width: ${size}px;
        height: ${size}px;
        border-radius: 50%;
        border: 2px solid #1e293b;
        box-shadow: 0 0 15px ${color}80;
      "></div>
    `,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
};

const sourceIcon = createCustomIcon('#10b981', 24); // Emerald
const destinationIcon = createCustomIcon('#f43f5e', 24); // Rose
const stopIcon = createCustomIcon('#3b82f6', 12); // Blue (smaller radius)

const createBusIcon = (color = '#3b82f6', route = '') => {
  const shortRoute = route.length > 4 ? route.substring(0, 4) : route;
  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        width: 28px;
        height: 28px;
        background-color: ${color};
        border: 2px solid #ffffff;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.4);
        position: relative;
      ">
        <svg fill="#ffffff" width="16" height="16" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path d="M4 16c0 .88.39 1.67 1 2.22V20c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h8v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm9 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm1.5-6H6V6h12v5z"/>
        </svg>
        <div style="
          position: absolute;
          top: -22px;
          background: #ffffff;
          color: #0f172a;
          font-size: 10px;
          font-weight: 800;
          padding: 2px 6px;
          border-radius: 4px;
          box-shadow: 0 2px 6px rgba(0,0,0,0.3);
          border: 1px solid ${color};
          white-space: nowrap;
        ">
          ${shortRoute}
        </div>
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14],
  });
};

const routeColors = {
  'S13': '#3b82f6',   // Blue
  'D51ET': '#a855f7', // Purple
  'D70CT': '#10b981', // Green
  'V51': '#f43f5e',   // Red
  'D70': '#f59e0b',   // Orange
  '51': '#06b6d4',    // Cyan
  'S570': '#6366f1',  // Indigo
  'M1': '#d946ef',    // Fuchsia
  'M70': '#8b5cf6',   // Violet
};

const getBusColor = (route) => {
  if (routeColors[route]) return routeColors[route];
  let hash = 0;
  for (let i = 0; i < route.length; i++) {
    hash = route.charCodeAt(i) + ((hash << 5) - hash);
  }
  const colors = ['#3b82f6', '#a855f7', '#10b981', '#f43f5e', '#f59e0b', '#06b6d4', '#6366f1', '#d946ef', '#8b5cf6'];
  return colors[Math.abs(hash) % colors.length];
};

const FitBounds = ({ path }) => {
  const map = useMap();
  useEffect(() => {
    if (path && path.length > 0) {
      const bounds = L.latLngBounds(path.map(p => [p.lat, p.lng]));
      // Shift padding slightly to the right to account for the left UI panel
      map.fitBounds(bounds, { paddingBottomRight: [50, 50], paddingTopLeft: [450, 50], animate: true, duration: 1.5 });
    }
  }, [path, map]);
  return null;
};

const MapView = ({ mapData, selectedRoute, allRoutes, selectedBusId, setSelectedBusId }) => {
  const mapRef = useRef(null);
  const [liveBuses, setLiveBuses] = useState([]);
  const [roadPath, setRoadPath] = useState([]);
  const defaultCenter = useMemo(() => [13.0827, 80.2707], []); // Chennai

  const fetchRoadRoute = useCallback(async (stops) => {
    if (!stops || stops.length < 2) {
      setRoadPath([]);
      return;
    }
    try {
      const coords = stops.map(s => `${s.lng},${s.lat}`).join(';');
      const approaches = stops.map(() => 'unrestricted').join(';');
      const url = `https://router.project-osrm.org/route/v1/driving/${coords}?overview=full&geometries=geojson&continue_straight=true&approaches=${approaches}`;
      const res = await fetch(url);
      const data = await res.json();
      if (data.code === 'Ok' && data.routes && data.routes.length > 0) {
        const geometry = data.routes[0].geometry;
        const path = geometry.coordinates.map(c => [c[1], c[0]]);
        setRoadPath(path);
      } else {
        setRoadPath(stops.map(s => [s.lat, s.lng]));
      }
    } catch (e) {
      setRoadPath(stops.map(s => [s.lat, s.lng]));
    }
  }, []);

  useEffect(() => {
    if (mapData?.path && mapData.path.length > 1) {
      fetchRoadRoute(mapData.path);
    } else {
      setRoadPath([]);
    }
  }, [mapData, fetchRoadRoute]);

  useEffect(() => {
    const fetchBuses = async () => {
      try {
        await fetch('http://localhost:8000/simulate-bus-movement', { method: 'POST' });
        const res = await fetch('http://localhost:8000/live-bus-positions');
        const data = await res.json();
        if (data.buses) {
          const validBuses = data.buses.filter(b => b.latitude && b.longitude);
          setLiveBuses(prev => {
            return validBuses.map(newBus => {
              const oldBus = prev.find(b => b.bus_id === newBus.bus_id);
              if (oldBus && oldBus.latitude !== newBus.latitude) {
                return { ...newBus, prevLat: oldBus.latitude, prevLng: oldBus.longitude, moved: true };
              }
              return { ...newBus, moved: false };
            });
          });
        }
      } catch (e) {
        // silently fail
      }
    };
    fetchBuses();
    const interval = setInterval(fetchBuses, 3000);
    return () => clearInterval(interval);
  }, []);

  const mapCenter = useMemo(() => {
    if (mapData?.path && mapData.path.length > 0) {
      const lats = mapData.path.map((p) => p.lat);
      const lngs = mapData.path.map((p) => p.lng);
      return [
        (Math.min(...lats) + Math.max(...lats)) / 2,
        (Math.min(...lngs) + Math.max(...lngs)) / 2,
      ];
    }
    return defaultCenter;
  }, [mapData, defaultCenter]);

  const allRoutePaths = useMemo(() => {
    if (!allRoutes || allRoutes.length === 0) return [];
    return allRoutes
      .filter(r => r.route_number !== selectedRoute?.route_number)
      .map(r => ({
        route_number: r.route_number,
        path: (r.stops_list || []).map(s => [s.latitude, s.longitude])
      }))
      .filter(r => r.path.length > 1);
  }, [allRoutes, selectedRoute]);

  const displayedBuses = useMemo(() => {
    if (selectedBusId) {
      return liveBuses.filter(b => b.bus_id === selectedBusId);
    }
    if (selectedRoute) {
      return liveBuses.filter(b => b.route === selectedRoute.route_number);
    }
    return liveBuses;
  }, [liveBuses, selectedBusId, selectedRoute]);

  const getMarkerIcon = (marker) => {
    if (marker.isSource) return sourceIcon;
    if (marker.isDestination) return destinationIcon;
    return stopIcon;
  };

  return (
    <div className="w-full h-full bg-[#0f172a] relative z-0">
      <MapContainer
        ref={mapRef}
        center={mapCenter}
        zoom={12}
        style={{ height: '100vh', width: '100vw', outline: 'none' }}
        scrollWheelZoom={true}
        zoomControl={false}
      >
        {/* Premium Dark Map (CartoDB Dark Matter - High Zoom Support) */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          className="map-tiles"
          maxZoom={19}
        />

        {mapData?.path && mapData.path.length > 0 && (
          <FitBounds path={mapData.path} />
        )}

        {/* Selected Route Polyline */}
        {roadPath.length > 0 && (
          <Polyline
            positions={roadPath}
            pathOptions={{
              color: '#06b6d4', // Cyan neon
              weight: 4,
              opacity: 0.9,
              lineCap: 'round',
              lineJoin: 'round',
              className: 'neon-polyline'
            }}
          />
        )}

        {/* Other Routes (Dimmed) */}
        {allRoutePaths.map((r, i) => (
          <Polyline
            key={`other-route-${i}`}
            positions={r.path}
            pathOptions={{
              color: '#475569',
              weight: 2,
              opacity: 0.4,
              dashArray: '5 10',
            }}
          />
        ))}

        {/* Stop Markers */}
        {mapData?.markers?.map((marker, index) => (
          <Marker
            key={`marker-${index}`}
            position={[marker.position.lat, marker.position.lng]}
            icon={getMarkerIcon(marker)}
          >
            <Popup>
              <div className="text-slate-100">
                <div className="flex items-center mb-2">
                  <FaBus className="text-accent-neon mr-2" />
                  <span className="font-semibold">{marker.title}</span>
                </div>
                <p className="text-xs text-slate-400">Stop #{marker.sequence}</p>
                {marker.isSource && (
                  <span className="inline-block mt-2 text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-1 rounded-md">
                    Boarding Point
                  </span>
                )}
                {marker.isDestination && (
                  <span className="inline-block mt-2 text-xs bg-rose-500/20 text-rose-400 border border-rose-500/30 px-2 py-1 rounded-md">
                    Alighting Point
                  </span>
                )}
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Live Bus Markers */}
        {displayedBuses.map((bus, index) => (
          <Marker
            key={`bus-${bus.bus_id || index}`}
            position={[bus.latitude, bus.longitude]}
            icon={createBusIcon(getBusColor(bus.route), bus.route)}
            eventHandlers={{
              click: () => setSelectedBusId && setSelectedBusId(bus.bus_id),
            }}
          >
            <Popup>
              <div className="min-w-[220px] text-slate-100">
                <div className="flex items-center gap-3 mb-3 pb-3 border-b border-slate-700">
                  <div style={{
                    width: '36px', height: '36px', borderRadius: '10px',
                    backgroundColor: getBusColor(bus.route) + '20', // 20% opacity background
                    border: '1px solid ' + getBusColor(bus.route),
                    color: getBusColor(bus.route),
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontWeight: '800', fontSize: '12px',
                    boxShadow: '0 0 10px ' + getBusColor(bus.route) + '40'
                  }}>
                    {bus.route}
                  </div>
                  <div>
                    <p className="font-bold text-lg leading-tight tracking-wide text-white">Bus {bus.bus_id}</p>
                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">
                      To: <span className="text-emerald-400">{bus.destination || 'Terminus'}</span>
                    </p>
                  </div>
                </div>
                <div className="space-y-3">
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">📍 Next Stop</span>
                    <p className="text-sm font-medium mt-0.5">{bus.current_stop}</p>
                  </div>
                  <div className="flex items-center gap-2 bg-slate-800/50 p-2 rounded-lg border border-slate-700">
                    <span className={`inline-block w-2.5 h-2.5 rounded-full ${bus.delay_status === 'On Time' ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]' :
                      bus.delay_status === 'Early' ? 'bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.8)]' :
                        bus.delay_status === 'Slightly Delayed' ? 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]' : 'bg-rose-400 shadow-[0_0_8px_rgba(244,63,94,0.8)]'
                      }`}></span>
                    <span className={`text-sm font-semibold tracking-wide ${bus.delay_status === 'On Time' ? 'text-emerald-400' :
                      bus.delay_status === 'Early' ? 'text-blue-400' :
                        bus.delay_status === 'Slightly Delayed' ? 'text-amber-400' : 'text-rose-400'
                      }`}>
                      {bus.delay_status}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-xs text-slate-400 pt-2 border-t border-slate-700">
                    <span className="flex items-center gap-1.5 bg-slate-800 px-2 py-1 rounded-md">👥 {bus.passengers} Pax</span>
                    <span className="flex items-center gap-1.5 opacity-70">⏱️ {bus.last_update}</span>
                  </div>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* No Route Overlay (Subtle gradient overlay when idle) */}
      {!mapData && (
        <div className="absolute inset-0 pointer-events-none flex items-center justify-center bg-radial-gradient from-transparent to-slate-900/40 z-10 transition-opacity duration-1000">
          <div className="glass-panel px-6 py-4 flex flex-col items-center gap-3 backdrop-blur-xl border border-slate-700/50 opacity-80 mix-blend-screen ml-40">
            <div className="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center shadow-lg">
              <FaBus className="text-xl text-slate-400 animate-pulse" />
            </div>
            <p className="text-sm font-medium tracking-wide text-slate-300">AWAITING ROUTE INPUT</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default MapView;
