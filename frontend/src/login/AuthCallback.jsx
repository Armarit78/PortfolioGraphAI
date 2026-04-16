import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const API_BASE_URL = import.meta.env.VITE_API_URL;

export const AuthCallback = () => {
    const navigate = useNavigate();
    const { login } = useAuth();
    const [params] = useSearchParams();

    useEffect(() => {

        console.log("URL complète:", window.location.href);
        console.log("Token récupéré:", params.get("token"));
        const token = params.get("token");
        if (!token) {
            navigate("/login?error=auth_failed");
            return;
        }

        fetch(`${API_BASE_URL}/api/auth/set-session`, {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token }),
        })
            .then(res => res.json())
            .then(() => login())
            .then(() => navigate('/'))
            .catch(() => navigate('/login?error=auth_failed'));
    }, []);

    return <p>Authentification en cours...</p>;
};