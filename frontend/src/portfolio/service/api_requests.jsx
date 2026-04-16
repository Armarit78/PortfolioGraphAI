import React from "react"

const API_BASE_URL = import.meta.env.VITE_API_URL
//charge la liste des portefeuilles associés à un compte
export const fetchPortfolios = async () => {
    try {
        console.log("Fetching portfolios for email: ", localStorage.getItem("email"));
        const response = await fetch(
            `${API_BASE_URL}/api/portfolio/getAll`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    email: localStorage.getItem("email"),
                })
            }
        );

        const data = await response.json();
        return data.portfolios;
    } catch (error) {
        console.log("Erreur lors de la récupération des portefeuilles : " + error)
    }

}

export const deletePortfolio = async (portfolioId) => {
    try {
        console.log(`Deleting portfolio id : ${portfolioId}`);
        const response = await fetch(
            "http://localhost:8000/api/portfolio/delete",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    email: localStorage.getItem("email"),
                    portfolioId: portfolioId
                })
            }
        );

        const data = await response.json();

        console.log("Data : ", data);

        return data.success;
    } catch (error) {
        console.log("Erreur lors de la récupération des portefeuilles : " + error)
    }

}

export const fetchPortfolioData = async (portfolioId) => {
    try {
        console.log("Fetching data for portfolioId: ", portfolioId);
        const response = await fetch(
            `${API_BASE_URL}/api/portfolio/get`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    email: localStorage.getItem("email"),
                    id_portfolio: portfolioId
                })
            }
        );

        const data = await response.json();

        console.log("Data : ", data);

        return [data.portfolio, data.return_daily, data.return_monthly, data.return_yearly, data.return_year_to_date];
    } catch (error) {
        console.log("Erreur lors de la récupération des données du portefeuille : " + error)
    }

}