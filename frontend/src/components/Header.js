import React from 'react';
import { FaBus, FaMapMarkedAlt, FaBrain } from 'react-icons/fa';

const Header = () => {
  return (
    <header className="glass-panel w-full">
      <div className="px-5 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 pointer-events-auto">
            <div className="bg-slate-800 p-2.5 rounded-xl border border-slate-700 shadow-sm flex-shrink-0">
              <FaBus className="text-slate-200 text-2xl" />
            </div>
            <div className="flex flex-col">
              <h1 className="text-xl font-bold text-slate-100 tracking-tight leading-none bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-blue-500">
                Chennai MTC
              </h1>
              <p className="text-slate-400 text-[10px] font-bold tracking-[0.2em] uppercase mt-1">
                Smart Transport
              </p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
