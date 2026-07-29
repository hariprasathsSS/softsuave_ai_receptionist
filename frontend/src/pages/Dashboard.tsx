import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { fetchDashboardStats } from "../api/calls";
import type { DashboardStats } from "../types";

const NAV_ITEMS = [
  { label: "Live Monitor", path: "/calls/live", icon: "🎙️", description: "Watch live calls and transcripts in real-time", color: "border-l-green-500" },
  { label: "Call Logs", path: "/calls", icon: "📋", description: "Browse past calls, recordings, and transcripts", color: "border-l-blue-500" },
  { label: "Profiles", path: "/profiles", icon: "👤", description: "Manage AI receptionist profiles and settings", color: "border-l-purple-500" },
  { label: "Bookings", path: "/bookings", icon: "📅", description: "View and manage appointment bookings", color: "border-l-yellow-500" },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    fetchDashboardStats()
      .then(setStats)
      .catch(() => setStats(null));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3">
          <h1 className="text-xl font-bold text-gray-900">AI Receptionist</h1>
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-4 sm:p-8">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 mb-8">
          <StatCard title="Active Profiles" value={stats ? String(stats.active_profiles) : "—"} />
          <StatCard title="Calls Today" value={stats ? String(stats.calls_today) : "—"} />
          <StatCard title="Bookings Today" value={stats ? String(stats.bookings_today) : "—"} />
        </div>

        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Access</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`bg-white rounded-xl shadow-sm border border-gray-200 border-l-4 ${item.color} p-5 text-left hover:shadow-md transition-shadow`}
            >
              <div className="flex items-center gap-3 mb-1">
                <span className="text-2xl">{item.icon}</span>
                <h3 className="font-semibold text-gray-900">{item.label}</h3>
              </div>
              <p className="text-sm text-gray-500 ml-10">{item.description}</p>
            </button>
          ))}
        </div>
      </main>
    </div>
  );
}

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-sm font-medium text-gray-500">{title}</h3>
      <p className="text-3xl font-bold mt-2 text-gray-900">{value}</p>
    </div>
  );
}
