import { Routes, Route, Navigate } from 'react-router-dom'
import AdminLayout from './admin/layouts/AdminLayout'
import UserLayout from './user/layouts/UserLayout'

// Admin Pages
import DashboardPage from './admin/pages/DashboardPage'
import CampaignsPage from './admin/pages/CampaignsPage'
import CallsPage from './admin/pages/CallsPage'
import LeadsPage from './admin/pages/LeadsPage'
import BulkCallPage from './admin/pages/BulkCallPage'
import CallRequestsPage from './admin/pages/CallRequestsPage'
import FeedbackAdminPage from './admin/pages/FeedbackAdminPage'

// User Pages
import UserHomePage from './user/pages/UserHomePage'
import UserVoiceChatPage from './user/pages/UserVoiceChatPage'
import UserFeedbackPage from './user/pages/UserFeedbackPage'

// Shared
import LoginPage from './shared/pages/LoginPage'
import { AuthProvider } from './shared/contexts/AuthContext'
import { ProtectedRoute } from './shared/components/ProtectedRoute'

function App() {
    return (
        <AuthProvider>
            <Routes>
                {/* Public Route */}
                <Route path="/login" element={<LoginPage />} />
                
                {/* Admin Routes */}
                <Route path="/admin" element={
                    <ProtectedRoute allowedRoles={['admin']}>
                        <AdminLayout>
                            <DashboardPage />
                        </AdminLayout>
                    </ProtectedRoute>
                } />
                <Route path="/admin/campaigns" element={
                    <ProtectedRoute allowedRoles={['admin']}>
                        <AdminLayout>
                            <CampaignsPage />
                        </AdminLayout>
                    </ProtectedRoute>
                } />
                <Route path="/admin/calls" element={
                    <ProtectedRoute allowedRoles={['admin']}>
                        <AdminLayout>
                            <CallsPage />
                        </AdminLayout>
                    </ProtectedRoute>
                } />
                <Route path="/admin/bulk-calls" element={
                    <ProtectedRoute allowedRoles={['admin']}>
                        <AdminLayout>
                            <BulkCallPage />
                        </AdminLayout>
                    </ProtectedRoute>
                } />
                <Route path="/admin/leads" element={
                    <ProtectedRoute allowedRoles={['admin']}>
                        <AdminLayout>
                            <LeadsPage />
                        </AdminLayout>
                    </ProtectedRoute>
                } />
                <Route path="/admin/call-requests" element={
                    <ProtectedRoute allowedRoles={['admin']}>
                        <AdminLayout>
                            <CallRequestsPage />
                        </AdminLayout>
                    </ProtectedRoute>
                } />
                <Route path="/admin/feedback" element={
                    <ProtectedRoute allowedRoles={['admin']}>
                        <AdminLayout>
                            <FeedbackAdminPage />
                        </AdminLayout>
                    </ProtectedRoute>
                } />

                {/* User Routes */}
                <Route path="/request-call" element={
                    <ProtectedRoute allowedRoles={['user']}>
                        <UserLayout>
                            <UserHomePage />
                        </UserLayout>
                    </ProtectedRoute>
                } />
                <Route path="/user/voice-chat" element={
                    <ProtectedRoute allowedRoles={['user']}>
                        <UserLayout>
                            <UserVoiceChatPage />
                        </UserLayout>
                    </ProtectedRoute>
                } />
                <Route path="/user/feedback" element={
                    <ProtectedRoute allowedRoles={['user']}>
                        <UserLayout>
                            <UserFeedbackPage />
                        </UserLayout>
                    </ProtectedRoute>
                } />

                {/* Default Redirect */}
                <Route path="/" element={<Navigate to="/login" replace />} />
                <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
        </AuthProvider>
    )
}

export default App
