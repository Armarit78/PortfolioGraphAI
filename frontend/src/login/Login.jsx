import { Button } from "react-bootstrap";

const Login = () => {
    const API_BASE_URL = import.meta.env.VITE_API_URL
    const handleGoogleLogin = () => {
        window.location.href = `${API_BASE_URL}/api/auth/login`;
    };

    return (
        <div className="auth-wrapper my-5 d-flex align-items-center justify-content-center">
            <div className="mainAuth">
                <div className="login">
                    <div className="d-flex flex-column p-4 align-items-center">
                        <label className="authLabel text-center mb-4">Login</label>
                        <Button className="btn authButton w-75" onClick={handleGoogleLogin}>
                            S'identifier avec Google
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Login;