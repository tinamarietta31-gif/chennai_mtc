import React from 'react';
import { FaBus, FaMapMarkedAlt, FaBrain } from 'react-icons/fa';

const Header = () => {
  return (
    <header className="glass-panel w-full compact-header">
      <div className="px-5 py-2 sm:py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 sm:space-x-4 pointer-events-auto">
            <div className="bg-slate-800 p-2 sm:p-2.5 rounded-xl border border-slate-700 shadow-sm flex-shrink-0">
              <FaBus className="text-slate-200 text-xl sm:text-2xl" />
            </div>
            <div className="flex flex-col">
              <h1 className="text-lg sm:text-xl font-bold text-slate-100 tracking-tight leading-none bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-blue-500">
                Chennai MTC
              </h1>
              <p className="text-slate-400 text-[8px] sm:text-[10px] font-bold tracking-[0.2em] uppercase mt-0.5 sm:mt-1">
                Smart Transport <span className="text-[6px] opacity-30 ml-2">v2.1.0</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
