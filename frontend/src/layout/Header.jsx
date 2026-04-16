import React, { useEffect, useState } from 'react';
import "/src/styles/Header.css"
import { NavLink } from "react-router-dom";
import { useAuth } from '../context/AuthContext';

const Header = () => {

    const { user, logout } = useAuth();

    const handleAuthClick = async () => {
        if (user) {
            await logout();
        }
        // Si pas connecté, le NavLink vers /login suffit
    };
    return (
        <header className="d-flex flex-wrap justify-content-center px-5">
            <NavLink to="/" className="d-flex align-items-center py-3 me-md-auto text-white text-decoration-none fw-bold">
                <img src="/logo.svg" alt="Logo" width="30" height="30" className="d-inline-block align-top me-2" />
                KyberAI
            </NavLink>
            <ul className="nav nav-pills">
                <li key="home-link" className="nav-item">
                    <NavLink to="/"
                        className={({ isActive }) => `nav-link ${isActive ? 'active' : ''} py-3 h-100`}>ACCUEIL</NavLink>
                </li>
                <li key="portfolio-link" className="nav-item">
                    <NavLink to="/portfolio" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''} py-3 h-100`}>MES
                        PORTEFEUILLES</NavLink>
                </li>
                <li className="nav-item">
                    <NavLink
                        to='/login'
                        onClick={handleAuthClick}
                        className={({ isActive }) => `nav-link ${isActive ? 'active' : ''} py-3 h-100`}
                    >
                        {user ? "SE DÉCONNECTER" : "SE CONNECTER"}
                    </NavLink>
                </li>
                <li className="nav-item">
                    <NavLink
                        to='/about-us'
                        className={({ isActive }) => `nav-link ${isActive ? 'active' : ''} py-3 h-100`}
                    >
                        A PROPOS
                    </NavLink>
                </li>
            </ul>
        </header>
    );
};

export default Header;