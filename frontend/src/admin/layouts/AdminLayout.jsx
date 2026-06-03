import { NavLink, useLocation } from 'react-router-dom'
import {
    LayoutDashboard,
    Megaphone,
    Phone,
    Users,
    Sparkles,
    Menu,
    LogOut,
    Mic,
    Upload,
    PhoneCall,
    MessageSquare
} from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '../../shared/contexts/AuthContext'

const adminNavItems = [
    { path: '/admin', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/admin/campaigns', label: 'Campaigns', icon: Megaphone },
    { path: '/admin/calls', label: 'Calls', icon: Phone },
    { path: '/admin/bulk-calls', label: 'Bulk Calls', icon: Upload },
    { path: '/admin/leads', label: 'Leads', icon: Users },
    { path: '/admin/call-requests', label: 'Call Requests', icon: PhoneCall },
    { path: '/admin/feedback', label: 'Feedback', icon: MessageSquare },
]

function AdminLayout({ children }) {
    const [sidebarOpen, setSidebarOpen] = useState(false)
    const location = useLocation()
    const { user, logout } = useAuth()

    const navItems = adminNavItems
    const currentPage = navItems.find(item => item.path === location.pathname)?.label || 'Dashboard'

    return (
        <div className="min-h-screen flex">
            {/* Mobile sidebar backdrop */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 bg-black/50 z-40 lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        w-64 glass-card rounded-none lg:rounded-r-3xl
        transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0
        transition-transform duration-300 ease-in-out
        flex flex-col
      `}>
                {/* Logo */}
                <div className="p-6 border-b border-white/10">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                            <Sparkles className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h1 className="font-bold text-lg gradient-text">Marketing AI</h1>
                            <p className="text-xs text-white/50 capitalize">Admin Portal</p>
                        </div>
                    </div>
                </div>

                {/* Navigation */}
                <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
                    {navItems.map(({ path, label, icon: Icon }) => (
                        <NavLink
                            key={path}
                            to={path}
                            end={path === '/admin'}
                            onClick={() => setSidebarOpen(false)}
                            className={({ isActive }) => `
                sidebar-link
                ${isActive ? 'sidebar-link-active' : ''}
              `}
                        >
                            <Icon className="w-5 h-5" />
                            <span>{label}</span>
                        </NavLink>
                    ))}
                </nav>

                {/* Footer */}
                <div className="p-4 border-t border-white/10 space-y-4">
                    <button 
                        onClick={logout}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 transition-colors"
                    >
                        <LogOut className="w-4 h-4" />
                        Logout
                    </button>
                    

                </div>
            </aside>

            {/* Main content */}
            <main className="flex-1 flex flex-col min-h-screen">
                {/* Header */}
                <header className="sticky top-0 z-30 glass-card rounded-none border-t-0 border-x-0 px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <button
                                className="lg:hidden btn-icon"
                                onClick={() => setSidebarOpen(true)}
                            >
                                <Menu className="w-5 h-5" />
                            </button>
                            <div>
                                <h2 className="text-xl font-semibold text-white">{currentPage}</h2>
                                <p className="text-sm text-white/50">
                                    {new Date().toLocaleDateString('en-US', {
                                        weekday: 'long',
                                        year: 'numeric',
                                        month: 'long',
                                        day: 'numeric'
                                    })}
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center gap-3">
                        </div>
                    </div>
                </header>

                {/* Page content */}
                <div className="flex-1 p-6 overflow-auto">
                    <div className="animate-fade-in">
                        {children}
                    </div>
                </div>
            </main>
        </div>
    )
}

export default AdminLayout
