import React, { useState, useEffect } from 'react';
import { FaLocationArrow, FaMapMarkerAlt, FaSearch } from 'react-icons/fa';

const SearchPanel = ({ onSearch, loading }) => {
  const [source, setSource] = useState('');
  const [destination, setDestination] = useState('');

  // All stops for autocomplete
  const [allStops, setAllStops] = useState([]);

  // Filtered suggestions
  const [sourceSuggestions, setSourceSuggestions] = useState([]);
  const [destSuggestions, setDestSuggestions] = useState([]);

  // Dropdown visibility
  const [showSourceDropdown, setShowSourceDropdown] = useState(false);
  const [showDestDropdown, setShowDestDropdown] = useState(false);

  // Selected source data
  const [selectedSource, setSelectedSource] = useState(null);
  const [destinationStops, setDestinationStops] = useState([]); // Stops reachable from source

  // Load all stops on component mount
  useEffect(() => {
    const loadAllStops = async () => {
      try {
        const response = await fetch('http://localhost:8000/get-all-stops-with-routes');
        const data = await response.json();
        setAllStops(data.stops || []);
      } catch (error) {
        console.error('Error loading stops:', error);
      }
    };
    loadAllStops();
  }, []);

  // Filter source suggestions as user types (from ALL stops)
  useEffect(() => {
    if (source.length >= 1 && !selectedSource) {
      const query = source.toLowerCase().trim();
      const queryWords = query.split(/\s+/).filter(w => w.length > 0);

      // Score-based matching: exact start > word start > contains
      const scored = allStops
        .map(stop => {
          const name = stop.stop_name.toLowerCase();
          const allMatch = queryWords.every(word => name.includes(word));
          if (!allMatch) return null;

          // Higher score = better match
          let score = 0;
          if (name.startsWith(query)) score += 100;
          if (name.includes(query)) score += 50;
          queryWords.forEach(w => { if (name.startsWith(w)) score += 20; });
          score += (stop.routes?.length || 0); // Prefer stops with more routes

          return { stop, score };
        })
        .filter(Boolean)
        .sort((a, b) => b.score - a.score)
        .slice(0, 15)
        .map(s => s.stop);

      setSourceSuggestions(scored);
      setShowSourceDropdown(scored.length > 0);
    } else {
      setSourceSuggestions([]);
      setShowSourceDropdown(false);
    }
  }, [source, allStops, selectedSource]);

  // Filter destination suggestions (only from reachable stops on same routes)
  useEffect(() => {
    if (!selectedSource || destinationStops.length === 0) {
      setDestSuggestions([]);
      setShowDestDropdown(false);
      return;
    }

    if (destination.length === 0) {
      // Show nearest reachable stops when field is empty (sorted by stops_away)
      setDestSuggestions(destinationStops.slice(0, 15));
      return;
    }

    const query = destination.toLowerCase().trim();
    const queryWords = query.split(/\s+/).filter(w => w.length > 0);

    const scored = destinationStops
      .map(stop => {
        const name = stop.stop_name.toLowerCase();
        const allMatch = queryWords.every(word => name.includes(word));
        if (!allMatch) return null;

        let score = 0;
        if (name.startsWith(query)) score += 100;
        if (name.includes(query)) score += 50;
        queryWords.forEach(w => { if (name.startsWith(w)) score += 20; });
        // Prefer closer stops
        score -= (stop.stops_away || 0);

        return { stop, score };
      })
      .filter(Boolean)
      .sort((a, b) => b.score - a.score)
      .slice(0, 15)
      .map(s => s.stop);

    setDestSuggestions(scored);
    setShowDestDropdown(scored.length > 0);
  }, [destination, destinationStops, selectedSource]);

  // Load destination stops when source is selected
  const loadDestinationStops = async (stopName, routes) => {
    try {
      const response = await fetch(
        `http://localhost:8000/get-destination-stops?from_stop=${encodeURIComponent(stopName)}`
      );
      const data = await response.json();
      setDestinationStops(data.destination_stops || []);
    } catch (error) {
      console.error('Error loading destination stops:', error);
      setDestinationStops([]);
    }
  };

  // Handle source selection
  const handleSourceSelect = (stop) => {
    setSource(stop.stop_name);
    setSelectedSource(stop);
    setShowSourceDropdown(false);
    setDestination('');
    setDestSuggestions([]);

    // Load stops reachable from this source
    loadDestinationStops(stop.stop_name, stop.routes);
  };

  // Handle destination selection
  const handleDestSelect = (stop) => {
    setDestination(stop.stop_name);
    setShowDestDropdown(false);
  };

  // Handle form submit
  const handleSubmit = (e) => {
    e.preventDefault();
    if (source && destination) {
      const hour = new Date().getHours(); // Auto-detect current hour
      onSearch(source, destination, hour);
    }
  };

  return (
    <div className="glass-panel p-6 shadow-2xl relative overflow-visible">
      {/* Subtle ambient light */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500 opacity-5 blur-3xl rounded-full -mr-10 -mt-10 pointer-events-none"></div>

      <h2 className="text-xl font-bold text-slate-100 mb-6 flex items-center tracking-wide">
        <FaSearch className="mr-3 text-slate-400 text-lg" />
        Find Your Route
      </h2>

      <form onSubmit={handleSubmit} className="space-y-5 relative z-10">
        {/* Source Input */}
        <div className="relative">
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1.5 ml-1">
            Origin
          </label>
          <div className="relative group">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-emerald-400 group-focus-within:text-emerald-300 transition-colors">
              <FaLocationArrow />
            </span>
            <input
              type="text"
              value={source}
              onChange={(e) => {
                setSource(e.target.value);
                setSelectedSource(null);
                setDestinationStops([]);
                setDestination('');
                setShowSourceDropdown(true);
              }}
              onFocus={() => {
                if (source.length >= 1 && !selectedSource && sourceSuggestions.length > 0) {
                  setShowSourceDropdown(true);
                }
              }}
              onBlur={() => {
                setTimeout(() => setShowSourceDropdown(false), 250);
              }}
              placeholder="Search origin stop..."
              className="input-field pl-11"
              autoComplete="off"
            />
          </div>

          {/* Source Dropdown */}
          {showSourceDropdown && sourceSuggestions.length > 0 && (
            <div className="autocomplete-dropdown">
              {sourceSuggestions.map((stop, index) => (
                <div
                  key={`src-${stop.stop_id}-${index}`}
                  className="autocomplete-item"
                  onClick={() => handleSourceSelect(stop)}
                >
                  <div className="font-semibold text-white">{stop.stop_name}</div>
                  {stop.routes && stop.routes.length > 0 && (
                    <div className="text-xs text-accent-neon mt-1 font-medium tracking-wide">
                      Route{stop.routes.length > 1 ? 's' : ''}: {stop.routes.slice(0, 5).join(', ')}
                      {stop.routes.length > 5 && ` +${stop.routes.length - 5}`}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Destination Input */}
        <div className="relative">
          <label className="flex justify-between items-center text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1.5 ml-1">
            <span>Destination</span>
            {selectedSource && destinationStops.length > 0 && (
              <span className="text-[10px] text-slate-400 font-medium lowercase bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">
                {destinationStops.length} stops available
              </span>
            )}
          </label>
          <div className="relative group">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-rose-400 group-focus-within:text-rose-300 transition-colors">
              <FaMapMarkerAlt />
            </span>
            <input
              type="text"
              value={destination}
              onChange={(e) => {
                setDestination(e.target.value);
                setShowDestDropdown(true);
              }}
              onFocus={() => {
                // Always show dropdown on focus if we have destination stops
                if (selectedSource && destinationStops.length > 0) {
                  if (destSuggestions.length > 0) {
                    setShowDestDropdown(true);
                  } else if (destination.length === 0) {
                    setDestSuggestions(destinationStops.slice(0, 15));
                    setShowDestDropdown(true);
                  }
                }
              }}
              onBlur={() => {
                setTimeout(() => setShowDestDropdown(false), 250);
              }}
              placeholder={selectedSource ? "Search destination..." : "Select origin first..."}
              disabled={!selectedSource}
              className={`input-field pl-11 ${!selectedSource ? 'opacity-50 cursor-not-allowed bg-slate-800/80 border-slate-700/50' : ''
                }`}
              autoComplete="off"
            />
          </div>

          {/* Destination Dropdown */}
          {showDestDropdown && destSuggestions.length > 0 && (
            <div className="autocomplete-dropdown">
              {destSuggestions.map((stop, index) => (
                <div
                  key={`dest-${stop.stop_id}-${index}`}
                  className="autocomplete-item flex justify-between items-center"
                  onClick={() => handleDestSelect(stop)}
                >
                  <div>
                    <div className="font-semibold text-white">{stop.stop_name}</div>
                    {stop.routes && (
                      <div className="text-xs text-accent-neon mt-1 font-medium tracking-wide">
                        Via: {stop.routes.join(', ')}
                      </div>
                    )}
                  </div>
                  <div className="text-xs font-bold text-slate-400 bg-slate-800 px-2 py-1 rounded-md border border-slate-700">
                    {stop.stops_away} stops
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Quick destination suggestions */}
          {selectedSource && destinationStops.length > 0 && !destination && (
            <div className="mt-3">
              <p className="text-[10px] text-slate-400 uppercase tracking-widest mb-2 ml-1">Popular Destinations</p>
              <div className="flex flex-wrap gap-2">
                {destinationStops.slice(0, 4).map((stop, index) => (
                  <button
                    key={index}
                    type="button"
                    onClick={() => setDestination(stop.stop_name)}
                    className="px-3 py-1.5 text-xs font-medium bg-slate-800/80 text-slate-300 border border-slate-700 rounded-lg hover:border-accent-neon hover:text-white transition-all duration-200 truncate max-w-[140px]"
                    title={stop.stop_name}
                  >
                    {stop.stop_name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading || !source || !destination}
          className={`w-full py-3.5 px-4 rounded-xl font-semibold text-sm tracking-wider uppercase transition-all duration-300 mt-2 ${loading || !source || !destination
              ? 'bg-slate-800/80 text-slate-500 cursor-not-allowed border border-slate-700/50'
              : 'bg-slate-700 hover:bg-slate-600 text-white border border-slate-600 shadow-md transform hover:-translate-y-0.5'
            }`}
        >
          {loading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-slate-300" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Optimizing Route...
            </span>
          ) : (
            <span>Search Routes</span>
          )}
        </button>
      </form>
    </div>
  );
};

export default SearchPanel;
