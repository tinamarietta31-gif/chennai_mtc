import React, { useState, useMemo } from 'react';
import Header from './components/Header';
import SearchPanel from './components/SearchPanel';
import RouteResults from './components/RouteResults';
import MapView from './components/MapView';
import LiveBusTracker from './components/LiveBusTracker';

function App() {
  const [routes, setRoutes] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchParams, setSearchParams] = useState({ source: '', destination: '' });
  const [selectedBusId, setSelectedBusId] = useState(null);
  const [isSearchActive, setIsSearchActive] = useState(false);
  const [isRoutesExpanded, setIsRoutesExpanded] = useState(false);

  // App-level environment state
  const [weatherCondition, setWeatherCondition] = useState('clear');
  const [trafficCondition, setTrafficCondition] = useState('normal');

  // Convert selectedRoute.stops_list into mapData format for MapView
  const mapData = useMemo(() => {
    if (!selectedRoute || !selectedRoute.stops_list || selectedRoute.stops_list.length === 0) {
      return null;
    }

    const path = selectedRoute.stops_list.map(stop => ({
      lat: stop.latitude,
      lng: stop.longitude
    }));

    const markers = selectedRoute.stops_list.map((stop, index) => ({
      position: { lat: stop.latitude, lng: stop.longitude },
      title: stop.stop_name,
      sequence: stop.sequence || index + 1,
      isSource: index === 0,
      isDestination: index === selectedRoute.stops_list.length - 1
    }));

    return { path, markers };
  }, [selectedRoute]);

  const handleSearch = async (source, destination, time) => {
    setLoading(true);
    setError(null);
    setSelectedBusId(null);
    setSearchParams({ source, destination });
    setIsSearchActive(true);
    setIsRoutesExpanded(false); // keep routes panel closed on new search

    try {
      const response = await fetch('http://localhost:8000/search-route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source,
          destination,
          time_of_day: time
        })
      });

      const data = await response.json();

      if (response.ok && Array.isArray(data) && data.length > 0) {
        setRoutes(data);
        setSelectedRoute(data[0]);
        setSelectedBusId(null);
        setError(null);
      } else if (response.ok && data.routes && data.routes.length > 0) {
        setRoutes(data.routes);
        setSelectedRoute(data.routes[0]);
        setSelectedBusId(null);
        setError(null);
      } else {
        setRoutes([]);
        setSelectedRoute(null);
        setError(data.detail || data.message || 'No routes found between the specified stops');
      }
    } catch (err) {
      setError('Failed to connect to server. Please make sure the backend is running.');
      setRoutes([]);
    }

    setLoading(false);
  };

  return (
    <div className={`relative w-full h-screen overflow-hidden bg-background font-sans text-slate-100 transition-colors duration-1000 ${trafficCondition === 'very_heavy' ? 'hue-rotate-15' : ''
      }`}>
      {/* Absolute Fullscreen Map Layer */}
      <div className="absolute inset-0 z-0">
        <MapView
          mapData={mapData}
          selectedRoute={selectedRoute}
          allRoutes={routes}
          weather={weatherCondition}
          traffic={trafficCondition}
          selectedBusId={selectedBusId}
          setSelectedBusId={setSelectedBusId}
        />
      </div>

      {/* Floating Header */}
      <div className="absolute top-4 left-0 sm:left-4 z-50 w-full sm:w-[420px] pointer-events-none px-4 sm:px-0">
        <Header />
      </div>

      {/* Centered Search Panel (Initial State) */}
      {!isSearchActive && (
        <div className="absolute inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm pointer-events-auto">
          <div className="w-full max-w-lg transform -translate-y-10 transition-all duration-500 hover:scale-[1.01]">
            <SearchPanel onSearch={handleSearch} loading={loading} />
            {error && (
              <div className="mt-4 glass-panel border-red-500/50 bg-red-900/30 text-white p-4 animate-fadeIn">
                <p className="font-semibold text-red-400">Error</p>
                <p className="text-sm">{error}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Floating UI Container (Left Panel - Active Search State) */}
      {isSearchActive && (
        <div className="absolute top-[104px] left-0 sm:left-4 right-0 sm:right-auto bottom-4 px-4 sm:px-0 w-full sm:w-[420px] z-40 flex flex-col gap-4 pointer-events-none transition-all duration-500 animate-slideRight">

          {/* Unified Header & Route Results Accordion */}
          <div className="pointer-events-auto shrink-0 flex flex-col glass-panel overflow-hidden transition-all duration-300">
            {/* Top Bar (Always visible) */}
            <div
              className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-slate-800/50 transition-colors"
              onClick={() => setIsRoutesExpanded(!isRoutesExpanded)}
            >
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Active Route</span>
                  <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded border border-slate-700">
                    {routes.length} found
                  </span>
                </div>
                <span className="text-sm font-medium text-emerald-400 truncate max-w-[240px]">
                  {searchParams.source} → {searchParams.destination || 'Any'}
                </span>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsSearchActive(false);
                  }}
                  className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold uppercase tracking-wider rounded border border-slate-600 transition-colors"
                >
                  New Search
                </button>
                <div className={`transform transition-transform duration-300 ${isRoutesExpanded ? 'rotate-180' : ''}`}>
                  <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                </div>
              </div>
            </div>

            {/* Expandable Route Results */}
            <div className={`transition-all duration-500 ease-in-out ${isRoutesExpanded ? 'max-h-[600px] opacity-100 border-t border-slate-700/50' : 'max-h-0 opacity-0 overflow-hidden'}`}>
              <div className="p-4" onClick={(e) => e.stopPropagation()}>
                {routes.length > 0 ? (
                  <RouteResults
                    routes={routes}
                    onSelectRoute={(route) => {
                      setSelectedRoute(route);
                      setSelectedBusId(null);
                      setIsRoutesExpanded(false); // Auto-collapse on selection
                    }}
                    selectedRoute={selectedRoute}
                  />
                ) : (
                  <div className="text-center py-4 text-slate-400 text-sm">No routes available</div>
                )}
              </div>
            </div>
          </div>

          {error && (
            <div className="pointer-events-auto shrink-0 glass-panel border-red-500/50 bg-red-900/30 text-white p-4">
              <p className="font-semibold text-red-400">Error</p>
              <p className="text-sm">{error}</p>
            </div>
          )}

          {/* Scrollable Line Trackers Area */}
          <div className="flex-1 overflow-y-auto w-full pr-2 pt-2 pointer-events-auto custom-scrollbar pb-20">

            {searchParams.source && (
              <LiveBusTracker
                fromStop={searchParams.source}
                toStop={searchParams.destination}
                routeNumber={selectedRoute?.route_number}
                selectedBusId={selectedBusId}
                setSelectedBusId={setSelectedBusId}
              />
            )}
          </div>
        </div>
      )}
      {/* Weather Overlay Effects */}
      {weatherCondition === 'rain' && (
        <div className="absolute inset-0 pointer-events-none z-30 bg-[url('https://www.transparenttextures.com/patterns/stardust.png')] opacity-30 mix-blend-overlay animate-pulse"></div>
      )}
      {weatherCondition === 'heavy_rain' && (
        <div className="absolute inset-0 pointer-events-none z-30 bg-[url('https://www.transparenttextures.com/patterns/stardust.png')] opacity-60 mix-blend-overlay"></div>
      )}
    </div>
  );
}

export default App;
