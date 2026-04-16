const API_BASE_URL = import.meta.env.VITE_API_URL
export const handleLogin = async (email, password, setResult) => {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            email: email,
            password: password
        })
    });

    const data = await response.json();
    if (data.success) {
        localStorage.setItem("logged", "true");
        localStorage.setItem("username", data.username);
        localStorage.setItem("email", email);
    }
    return data
}

export const handleSignUp = async (name, email, password, confirmPassword, setResult) => {
    const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            username: name,
            email: email,
            password: password,
            confirmPassword: confirmPassword
        })
    });
    const data = await response.json();
    if (data.success) {
        localStorage.setItem("logged", "true");
        localStorage.setItem("username", data.username);
        localStorage.setItem("email", data.email);

    }
    return data
}