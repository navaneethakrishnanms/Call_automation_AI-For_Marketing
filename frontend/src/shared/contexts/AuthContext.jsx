import { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const AuthContext = createContext();

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        // Check local storage for session
        const storedUser = localStorage.getItem('auth_user');
        if (storedUser) {
            setUser(JSON.parse(storedUser));
        }
        setLoading(false);
    }, []);

    const login = (username, password) => {
        // Hardcoded roles for simplicity
        if (username === 'admin' && password === 'admin') {
            const adminUser = { role: 'admin', username: 'admin' };
            setUser(adminUser);
            localStorage.setItem('auth_user', JSON.stringify(adminUser));
            navigate('/admin');
            return true;
        } else if (username === 'user' && password === 'user') {
            const normalUser = { role: 'user', username: 'user' };
            setUser(normalUser);
            localStorage.setItem('auth_user', JSON.stringify(normalUser));
            navigate('/request-call');
            return true;
        }
        return false;
    };

    const logout = () => {
        setUser(null);
        localStorage.removeItem('auth_user');
        navigate('/login');
    };

    if (loading) return null;

    return (
        <AuthContext.Provider value={{ user, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}
