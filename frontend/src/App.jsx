import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'

// Public pages
import Login from './pages/Login'
import Register from './pages/Register'
import Unauthorized from './pages/Unauthorized'

// Citizen pages
import CitizenDashboard from './pages/citizen/Dashboard'
import SubmitComplaint from './pages/citizen/SubmitComplaint'
import CitizenComplaintDetail from './pages/citizen/ComplaintDetail'
import Notifications from './pages/citizen/Notifications'

// Staff pages
import StaffDashboard from './pages/staff/Dashboard'
import StaffComplaintDetail from './pages/staff/ComplaintDetail'

// Admin pages
import AdminDashboard from './pages/admin/Dashboard'
import AdminComplaints from './pages/admin/Complaints'
import AdminUsers from './pages/admin/Users'
import AdminReports from './pages/admin/Reports'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: { borderRadius: '12px', fontSize: '14px' },
            success: { iconTheme: { primary: '#2563eb', secondary: '#fff' } },
          }}
        />
        <Routes>
          {/* Public */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/unauthorized" element={<Unauthorized />} />
          <Route path="/" element={<Navigate to="/login" replace />} />

          {/* Citizen */}
          <Route path="/citizen/dashboard" element={
            <ProtectedRoute allowedRoles={['Complainant']}><CitizenDashboard /></ProtectedRoute>
          } />
          <Route path="/citizen/submit" element={
            <ProtectedRoute allowedRoles={['Complainant']}><SubmitComplaint /></ProtectedRoute>
          } />
          <Route path="/citizen/complaint/:id" element={
            <ProtectedRoute allowedRoles={['Complainant']}><CitizenComplaintDetail /></ProtectedRoute>
          } />
          <Route path="/citizen/notifications" element={
            <ProtectedRoute allowedRoles={['Complainant']}><Notifications /></ProtectedRoute>
          } />

          {/* Staff */}
          <Route path="/staff/dashboard" element={
            <ProtectedRoute allowedRoles={['Staff']}><StaffDashboard /></ProtectedRoute>
          } />
          <Route path="/staff/assigned" element={
            <ProtectedRoute allowedRoles={['Staff']}><StaffDashboard /></ProtectedRoute>
          } />
          <Route path="/staff/complaint/:id" element={
            <ProtectedRoute allowedRoles={['Staff']}><StaffComplaintDetail /></ProtectedRoute>
          } />

          {/* Admin */}
          <Route path="/admin/dashboard" element={
            <ProtectedRoute allowedRoles={['Administrator']}><AdminDashboard /></ProtectedRoute>
          } />
          <Route path="/admin/complaints" element={
            <ProtectedRoute allowedRoles={['Administrator']}><AdminComplaints /></ProtectedRoute>
          } />
          <Route path="/admin/complaint/:id" element={
            <ProtectedRoute allowedRoles={['Administrator']}><StaffComplaintDetail /></ProtectedRoute>
          } />
          <Route path="/admin/users" element={
            <ProtectedRoute allowedRoles={['Administrator']}><AdminUsers /></ProtectedRoute>
          } />
          <Route path="/admin/reports" element={
            <ProtectedRoute allowedRoles={['Administrator']}><AdminReports /></ProtectedRoute>
          } />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
