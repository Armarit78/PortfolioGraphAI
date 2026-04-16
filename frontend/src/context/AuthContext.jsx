import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);
const API_BASE_URL = import.meta.env.VITE_API_URL
export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        fetch(`${API_BASE_URL}/api/auth/me`, {
            credentials: 'include' // envoie le cookie automatiquement
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) setUser(data.user);
            })
            .catch(() => { })
            .finally(() => setIsLoading(false));
    }, []);

    const login = () => {
        return fetch(`${API_BASE_URL}/api/auth/me`, { credentials: 'include' })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    setUser(data.user);
                    localStorage.setItem('username', data.user.username);
                    localStorage.setItem('email', data.user.email);
                }
            });
    };

    const logout = async () => {
        await fetch(`${API_BASE_URL}/api/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        setUser(null);
        localStorage.removeItem('username');
        localStorage.removeItem('email');
    };

    return (
        <AuthContext.Provider value={{ user, login, logout, isLoading }}>
            {!isLoading && children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);