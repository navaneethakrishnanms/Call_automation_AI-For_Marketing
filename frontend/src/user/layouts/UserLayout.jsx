import { useAuth } from '../../shared/contexts/AuthContext'
import { LogOut, Sparkles, MessageSquare } from 'lucide-react'

function UserLayout({ children }) {
    const { logout } = useAuth()

    return (
        <div className="min-h-screen flex flex-col">
            {/* Top Navigation */}
            <header className="sticky top-0 z-30 glass-card rounded-none border-t-0 border-x-0 px-6 py-4">
                <div className="flex items-center justify-between max-w-7xl mx-auto w-full">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                            <Sparkles className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h1 className="font-bold text-lg gradient-text">Marketing AI</h1>
                            <p className="text-xs text-white/50 capitalize">User Portal</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">

                        <a 
                            href="/user/feedback"
                            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary-500/10 text-primary-300 hover:bg-primary-500/20 transition-colors"
                        >
                            <MessageSquare className="w-4 h-4" />
                            <span className="hidden sm:inline">Feedback</span>
                        </a>
                        <button 
                            onClick={logout}
                            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 transition-colors"
                        >
                            <LogOut className="w-4 h-4" />
                            <span className="hidden sm:inline">Logout</span>
                        </button>
                    </div>
                </div>
            </header>

            {/* Page content */}
            <main className="flex-1 p-6 overflow-auto">
                <div className="max-w-7xl mx-auto w-full animate-fade-in">
                    {children}
                </div>
            </main>
        </div>
    )
}

export default UserLayout
