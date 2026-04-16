import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Header from './layout/Header'
import Footer from './layout/Footer'
import Login from "./login/Login";
import Portfolio from './portfolio/Portfolio'
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from './context/AuthContext';
import { AuthCallback } from './login/AuthCallback';
import 'bootstrap/dist/css/bootstrap.min.css';
import "./styles/Global.css"
import Home from "./home/Home";
const App = () => {
    return (
        <AuthProvider>
            <Router>
                <div className="app-container">
                    <Header />
                    <div className="main-content">
                        <Routes>
                            <Route path="/login" element={<Login />} />

                            <Route path="/auth/callback" element={<AuthCallback />} />


                            <Route path="/" element={
                                <ProtectedRoute>
                                    <Home />
                                </ProtectedRoute>}
                            />
                            <Route path="/chat/:chatId" element={
                                <ProtectedRoute>
                                    <Home />
                                </ProtectedRoute>}
                            />
                            <Route path="/portfolio" element={
                                <ProtectedRoute>
                                    <Portfolio />
                                </ProtectedRoute>
                            }
                            />
                            <Route path="/portfolio/:portfolioId" element={
                                <ProtectedRoute>
                                    <Portfolio />
                                </ProtectedRoute>}
                            />
                            <Route path="/about-us" element={
                                <Footer />
                            } />
                        </Routes>
                    </div>
                    {/*<Footer />*/}
                </div>

            </Router>
        </AuthProvider>
    );
}

export default App;