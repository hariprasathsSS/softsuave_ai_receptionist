import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import CallLogList from "./pages/calls/CallLogList";
import CallDetail from "./pages/calls/CallDetail";
import LiveMonitor from "./pages/calls/LiveMonitor";
import ProfileList from "./pages/profiles/ProfileList";
import BookingCalendar from "./pages/bookings/BookingCalendar";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/calls" element={<CallLogList />} />
        <Route path="/calls/live" element={<LiveMonitor />} />
        <Route path="/calls/:id" element={<CallDetail />} />
        <Route path="/profiles" element={<ProfileList />} />
        <Route path="/bookings" element={<BookingCalendar />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
