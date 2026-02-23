import React, { useState, useEffect } from 'react';
import { FaBus, FaClock, FaSyncAlt, FaMapMarkerAlt, FaExclamationCircle } from 'react-icons/fa';
import API_BASE_URL from '../config';

const LiveBusTracker = ({ fromStop, toStop, routeNumber, selectedBusId, setSelectedBusId }) => {
  const [liveBuses, setLiveBuses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  const fetchLiveBuses = async () => {
    setLoading(true);
    try {
      // Fetch ETA data if we have source and destination
      if (fromStop && toStop && routeNumber) {
        const etaResponse = await fetch(`${API_BASE_URL}/get-bus-eta`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            from_stop: fromStop,
            to_stop: toStop,
            route_number: routeNumber
          })
        });
        const etaData = await etaResponse.json();
        if (etaData.incoming_buses && etaData.incoming_buses.length > 0) {
          setLiveBuses(etaData.incoming_buses);
          setLastUpdate(new Date().toLocaleTimeString());
          setError(null);
          setLoading(false);
          return;
        }
      }

      // Fallback: fetch live positions and filter by route only
      const response = await fetch(`${API_BASE_URL}/live-bus-positions`);
      const data = await response.json();
      if (data.buses) {
        let buses = data.buses;
        if (routeNumber) {
          buses = buses.filter(bus =>
            String(bus.route) === String(routeNumber)
          );
        }
        // Map live-position fields to match ETA format for display
        const mapped = buses.map(bus => ({
          bus_id: bus.bus_id,
          route_number: bus.route,
          current_location: bus.current_stop,
          direction: bus.direction,
          latitude: bus.latitude,
          longitude: bus.longitude,
          last_update: bus.last_update,
          delay_status: bus.delay_status,
          passengers: bus.passengers
        }));
        setLiveBuses(mapped);
        setLastUpdate(new Date().toLocaleTimeString());
        setError(null);
      } else {
        setLiveBuses([]);
        setError('No live bus data');
      }
    } catch (err) {
      setError('Failed to fetch live bus data');
      setLiveBuses([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchLiveBuses();
    const interval = setInterval(fetchLiveBuses, 30000);
    return () => clearInterval(interval);
  }, [fromStop, toStop, routeNumber]);

  if (!fromStop) {
    return (
      <div className="glass-panel p-6 shadow-2xl relative">
        <h3 className="text-lg font-bold text-white mb-4 flex items-center tracking-wide">
          <FaBus className="mr-3 text-accent-pink" />
          Live Bus Tracker
        </h3>
        <p className="text-slate-400 text-sm">Select an origin stop to monitor incoming buses in real-time.</p>
      </div>
    );
  }

  return (
    <div className="glass-panel p-6 shadow-2xl relative overflow-visible">
      <div className="absolute top-0 right-0 w-32 h-32 bg-accent-pink opacity-10 blur-3xl rounded-full -mr-10 -mt-10 pointer-events-none"></div>

      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-6">
        <h3 className="text-lg font-bold text-white flex items-center tracking-wide">
          <FaBus className="mr-3 text-accent-pink" />
          Live Arrivals
        </h3>
        <div className="flex items-center gap-3">
          {lastUpdate && (
            <span className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold flex items-center">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse mr-1.5"></span>
              Updated: {lastUpdate}
            </span>
          )}
          <button
            onClick={fetchLiveBuses}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-bold uppercase tracking-wider rounded-lg border border-slate-700 hover:border-slate-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FaSyncAlt className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      <div className="mb-5 p-4 bg-slate-800/50 border border-slate-700/50 rounded-xl relative overflow-hidden group">
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-emerald-400 to-primary-500"></div>
        <div className="flex items-start gap-3">
          <FaMapMarkerAlt className="text-emerald-400 mt-1 flex-shrink-0" />
          <div>
            <p className="text-sm text-slate-300">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-0.5">Origin Stop</span>
              <span className="text-white font-medium">{fromStop}</span>
            </p>
            {toStop && toStop !== fromStop && (
              <p className="text-sm text-slate-300 mt-2">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-0.5">Destination</span>
                <span className="text-emerald-100 font-medium">{toStop}</span>
              </p>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl mb-5 flex items-start gap-3 text-sm font-medium">
          <FaExclamationCircle className="mt-0.5 flex-shrink-0" />
          {error}
        </div>
      )}

      {liveBuses.length === 0 && !loading && !error && (
        <div className="text-center py-10 text-slate-400 border border-dashed border-slate-700 rounded-xl">
          <p className="font-medium">No buses currently tracked</p>
          <p className="text-xs mt-2 uppercase tracking-widest text-slate-500">Check back soon</p>
        </div>
      )}

      <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
        {liveBuses.map((bus, index) => {
          // Support both ETA response format and live-positions format
          const busId = bus.bus_id;
          const route = bus.route_number || bus.route || routeNumber;
          const currentLocation = bus.current_location || bus.current_stop || 'Unknown';
          const etaMinutes = bus.eta_minutes;
          const arrivalTime = bus.arrival_time;
          const stopsAway = bus.stops_away;
          const distanceKm = bus.distance_km;
          const delayStatus = bus.delay_status || 'Unknown';
          const passengers = bus.passengers;
          const confidence = bus.confidence;
          const lastUpdate = bus.last_update;
          const lat = bus.latitude;
          const lng = bus.longitude;

          return (
            <div
              key={busId}
              onClick={() => setSelectedBusId && setSelectedBusId(busId === selectedBusId ? null : busId)}
              className={`p-5 rounded-xl border relative overflow-hidden cursor-pointer transition-all ${selectedBusId === busId
                ? 'bg-slate-800 border-emerald-400 ring-1 ring-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.3)] transform scale-[1.02]'
                : index === 0
                  ? 'bg-gradient-to-br from-emerald-900/40 to-slate-800/80 border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.1)] hover:border-emerald-400/80'
                  : 'bg-slate-800/40 border-slate-700/50 hover:border-slate-500'
                }`}
            >
              {index === 0 && (
                <div className="absolute top-0 right-0 px-3 py-1 bg-gradient-to-r from-emerald-500 to-emerald-400 text-white text-[10px] font-black uppercase tracking-widest rounded-bl-lg">
                  Arriving Next
                </div>
              )}

              <div className="flex justify-between items-start mt-1">
                <div>
                  <div className="flex items-center gap-3">
                    <span className={`text-2xl font-black tracking-wider px-3 py-1 rounded-lg border shadow-inner ${index === 0
                      ? 'bg-emerald-900/50 text-white border-emerald-500/30'
                      : 'bg-slate-900/80 text-white border-slate-700'
                      }`}>
                      {route}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-3 flex items-center gap-2">
                    <span className="text-emerald-400">📍</span>
                    <span className="truncate max-w-[160px]" title={currentLocation}>{currentLocation}</span>
                  </p>
                  {stopsAway !== undefined && (
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs font-bold text-slate-300 uppercase tracking-wider bg-slate-900/50 inline-block px-2 py-1 rounded border border-slate-700/50">
                        {stopsAway} stops away
                      </span>
                      {distanceKm !== undefined && (
                        <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider bg-cyan-900/30 inline-block px-2 py-1 rounded border border-cyan-700/50">
                          {distanceKm} km
                        </span>
                      )}
                    </div>
                  )}
                  {!stopsAway && bus.direction && (
                    <p className="text-xs font-bold text-slate-300 mt-1 uppercase tracking-wider bg-slate-900/50 inline-block px-2 py-1 rounded border border-slate-700/50">
                      {bus.direction} direction
                    </p>
                  )}
                </div>

                <div className="text-right flex flex-col justify-between items-end h-full">
                  {etaMinutes !== undefined ? (
                    <>
                      <div className="text-4xl font-black text-white tracking-tighter">
                        {Math.round(etaMinutes)}
                        <span className="text-sm font-bold text-slate-400 tracking-widest uppercase ml-0.5">min</span>
                      </div>
                      {arrivalTime && (
                        <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium mt-1">
                          <FaClock className="text-slate-500" size={10} />
                          ETA: {arrivalTime}
                        </div>
                      )}
                      {distanceKm !== undefined && (
                        <div className="text-xs text-cyan-400 font-bold mt-1">
                          📏 {distanceKm} km away
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="text-sm font-bold text-slate-400 tracking-widest uppercase">
                      {passengers !== undefined ? `${passengers} pax` : '—'}
                    </div>
                  )}
                  {confidence !== undefined && (
                    <div className="text-[10px] text-slate-500 mt-1">
                      {Math.round(confidence * 100)}% confidence
                    </div>
                  )}
                  <p className={`text-xs font-bold uppercase tracking-widest mt-2 px-2 py-0.5 rounded-full border bg-slate-900/50`}>{delayStatus}</p>
                </div>
              </div>

              <div className="flex justify-between items-center mt-4 pt-3 border-t border-slate-700/50">
                <div className="flex items-center gap-4 text-[10px] uppercase font-bold tracking-widest text-slate-500">
                  {lat && lng && (
                    <span className="flex items-center gap-1.5">
                      <span className="text-primary-400">🗺️</span> {lat}, {lng}
                    </span>
                  )}
                  <span className="flex items-center gap-1.5">
                    <span className="text-accent-pink">🎯</span> {busId}
                  </span>
                  {lastUpdate && (
                    <span className="flex items-center gap-1.5">
                      <FaClock size={8} /> {lastUpdate}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default LiveBusTracker;
