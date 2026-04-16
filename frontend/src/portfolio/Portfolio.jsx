import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button, Navbar } from "react-bootstrap";
import { PortfolioTable } from "./features/portfolioTable";
import { PortfolioGraph } from "./features/portfolioGraph";
import { PortfolioTuto } from "./features/portfolioTuto";
import { deletePortfolio, fetchPortfolios } from "./service/api_requests";
import { fetchPortfolioData } from "./service/api_requests";
import { deleteChat } from "../home/service/api_requests";

export default function Portfolio() {
    const navigate = useNavigate();
    const [portfolioList, setPortfolioList] = useState([])
    useEffect(() => {
        const loadData = async () => {
            const data = await fetchPortfolios();
            if (data) {
                setPortfolioList(data);
            }
        };
        loadData();
    }, []);
    const portfolioId = useParams();

    const [portfolioData, setPortfolioData] = useState(null);
    const [returnDaily, setReturnDaily] = useState(null);
    const [returnMonthly, setReturnMonthly] = useState(null);
    const [returnYearly, setReturnYearly] = useState(null);
    const [returnYearToDate, setReturnYearToDate] = useState(null);

    useEffect(() => {
        if (portfolioId) {
            const loadData = async () => {
                const data = await fetchPortfolioData(portfolioId.portfolioId);
                setPortfolioData(data[0]);
                setReturnDaily(data[1]);
                setReturnMonthly(data[2]);
                setReturnYearly(data[3]);
                setReturnYearToDate(data[4]);
                console.log("portfolioData : ", data[0]);
            };
            loadData();
        }
    }, [portfolioId]);


    return (
        <div className="h-100 d-flex flex-column overflow-hidden">
            <ul className="nav nav-tabs">
                {portfolioList.map((id) =>
                (<li key={"li_portfolio_" + id} className="d-flex flex-row align-items-center nav-item" style={{ transform: 'translateY(0px)' }}>

                    <Button
                        key={"a_portfolio_" + id}
                        className={`nav-link border-0 rounded-0 ${id === parseInt(portfolioId.portfolioId) ? "active" : ""}`}
                        onClick={() => {
                            navigate(`/portfolio/${id}`);
                        }}
                    >
                        Portefeuille {id}
                    </Button>
                    {portfolioId.portfolioId === id.toString() &&
                        <Button className="nav-link bg-danger rounded-0 border-0 color-white" style={{ transform: 'translateY(0px)' }} onClick={async () => {
                            const res = await deletePortfolio(id);
                            if (res) {
                                setPortfolioList((prev) => prev.filter((c) => c.portfolioId !== id));
                                navigate("/portfolio");
                            }
                        }}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-trash" viewBox="0 0 16 16">
                                <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z" />
                                <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z" />
                            </svg>
                        </Button>
                    }

                </li>)
                )}
            </ul>
            {portfolioId.portfolioId ?
                <div className="d-flex flex-column overflow-auto mt-1 align-items-center min-vh-0">
                    <h2 className="text-white mt-2 text-center fw-bold">Analyse de mon portefeuille {portfolioId.portfolioId}</h2>
                    {returnDaily && returnDaily.length > 0 && <PortfolioGraph
                        returnDaily={returnDaily}
                        returnMonthly={returnMonthly}
                        returnYearly={returnYearly}
                        returnYearToDate={returnYearToDate} />}
                    {portfolioData && portfolioData.length > 0 && <PortfolioTable portfolioData={portfolioData} columnsToShow={["ticker","weight","name","unit_buy_price","unit_price","pnl"]} />}
                </div>
                :
                <div className="d-flex flex-column overflow-auto mt-1 align-items-center flex-fill min-vh-0">
                    <PortfolioTuto />
                </div>}
        </div>
    );
}