import React from 'react';
import { FaRoute, FaStar, FaMapSigns, FaRuler, FaBolt, FaCheckCircle, FaExclamationTriangle } from 'react-icons/fa';

const RouteResults = ({ routes, onSelectRoute, selectedRoute }) => {
  if (!routes || routes.length === 0) {
    return null;
  }

  const getBadgeIcon = (type) => {
    if (type.includes('Recommended')) return <FaStar className="mr-1" />;
    if (type.includes('Least')) return <FaMapSigns className="mr-1" />;
    if (type.includes('Shortest')) return <FaRuler className="mr-1" />;
    return <FaBolt className="mr-1" />;
  };

  const getBadgeClass = (type) => {
    if (type.includes('Recommended')) return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
    if (type.includes('Least')) return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
    if (type.includes('Shortest')) return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30';
    return 'bg-primary-500/20 text-primary-300 border-primary-500/30';
  };

  return (
    <div className="w-full">

      <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
        {routes.map((route, index) => (
          <div
            key={`${route.route_number}-${index}`}
            className={`p-5 rounded-xl border cursor-pointer transition-all duration-300 relative overflow-hidden group ${selectedRoute?.route_number === route.route_number
              ? 'bg-slate-800/80 border-slate-500 shadow-md transform -translate-y-0.5'
              : 'bg-slate-800/40 border-slate-700/50 hover:bg-slate-800/60 hover:border-slate-600 hover:-translate-y-0.5'
              }`}
            onClick={() => onSelectRoute && onSelectRoute(route)}
          >
            {selectedRoute?.route_number === route.route_number && (
              <div className="absolute top-0 left-0 w-1 h-full bg-blue-500"></div>
            )}

            <div className="flex justify-between items-start">
              <div>
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-xl font-bold text-slate-100 tracking-wider px-3 py-1 bg-slate-900/60 rounded border border-slate-700/50 group-hover:border-slate-500 transition-colors">
                    {route.route_number}
                  </span>
                  {route.route_type && route.route_type.includes('Direct') && (
                    <span className={`px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md border flex items-center ${getBadgeClass(route.route_type)}`}>
                      {getBadgeIcon(route.route_type)}
                      {route.route_type.includes('Recommended') ? 'Best' :
                        route.route_type.includes('Least') ? 'Fewest Stops' :
                          route.route_type.includes('Shortest') ? 'Shortest' : 'Direct'}
                    </span>
                  )}
                  {route.rank && (
                    <span className="px-2.5 py-1 bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] uppercase font-bold tracking-wider rounded-md">
                      Rank {route.rank}
                    </span>
                  )}
                </div>

                <div className="mt-4 flex items-center text-sm font-medium text-slate-300">
                  <span className="text-emerald-400 truncate max-w-[120px]" title={route.source_stop}>{route.source_stop}</span>
                  <span className="mx-2 text-slate-500">→</span>
                  <span className="text-rose-400 truncate max-w-[120px]" title={route.destination_stop}>{route.destination_stop}</span>
                </div>

                <div className="flex items-center gap-4 mt-2">
                  <div className="text-xs text-slate-400 flex items-center bg-slate-900/50 px-2 py-1 rounded">
                    <span className="text-slate-500 mr-1.5">●</span>
                    {route.stops_between || route.num_stops || '?'} stops
                  </div>
                  <div className="text-xs text-slate-400 flex items-center bg-slate-900/50 px-2 py-1 rounded">
                    <FaRuler className="text-slate-500 mr-1.5" size={10} />
                    {(route.total_distance_km || route.distance)?.toFixed(1) || '?'} km
                  </div>
                </div>
              </div>

              <div className="text-right flex flex-col justify-between items-end h-full">
                {route.delay_probability !== undefined && (
                  <div className={`flex flex-col items-end px-3 py-2 rounded-lg border ${route.delay_probability > 0.5
                    ? 'bg-rose-500/10 border-rose-500/20'
                    : 'bg-emerald-500/10 border-emerald-500/20'
                    }`}>
                    <span className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold mb-0.5">Reliability</span>
                    <div className={`flex items-center text-sm font-bold ${route.delay_probability > 0.5 ? 'text-rose-400' : 'text-emerald-400'
                      }`}>
                      {route.delay_probability > 0.5 ? <FaExclamationTriangle className="mr-1.5" size={12} /> : <FaCheckCircle className="mr-1.5" size={12} />}
                      {Math.round((1 - route.delay_probability) * 100)}%
                    </div>
                  </div>
                )}

                {selectedRoute?.route_number === route.route_number && (
                  <div className="mt-4 text-[10px] text-primary-400 uppercase tracking-widest font-bold flex items-center">
                    <span className="w-2 h-2 rounded-full bg-primary-500 animate-pulse mr-2"></span>
                    Selected
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RouteResults;
