import { Button } from "react-bootstrap";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { use, useState, useEffect } from "react";

export function PortfolioGraph({ returnDaily, returnMonthly, returnYearly, returnYearToDate }) {

    const [legend, setLegend] = useState("Jour");
    const [currentData, setCurrentData] = useState(returnDaily);

    useEffect(() => {
        if (legend === "Jour") setCurrentData(returnDaily);
        else if (legend === "Mois") setCurrentData(returnMonthly);
        else if (legend === "Annee") setCurrentData(returnYearly);
        else if (legend === "Year to Date") setCurrentData(returnYearToDate);
    }, [legend, returnDaily, returnMonthly, returnYearly, returnYearToDate]);


    const dataWithTimestamp = currentData.map(d => ({ ...d, x: new Date(d.x).getTime() }));

    const getTicks = (filtered, legend) => {
        const sorted = [...filtered].sort((a, b) => new Date(a.x) - new Date(b.x));
        if (legend === "Annee") {
            return [...new Set(sorted.map(d => d.x.slice(0, 4)))]
                .map(y => new Date(`${y}-01-01`).getTime());
        }
        if (legend === "Mois") {
            return [...new Set(sorted.map(d => d.x.slice(0, 7)))]
                .map(m => new Date(`${m}-01`).getTime()).slice(-9);
        }
        if (legend === "Jour") {
            return sorted.slice(-9).map(d => new Date(d.x).getTime());
        }
        if (legend === "Year to Date") {
            const now = new Date();
            const startOfYear = new Date(`${now.getFullYear()}-01-01`);
            return [...new Set(
                sorted
                    .filter(d => new Date(d.x) >= startOfYear)
                    .map(d => d.x.slice(0, 7))
            )].map(m => new Date(`${m}-01`).getTime());
        }
        return sorted.map(d => new Date(d.x).getTime());
    };

    const formatXAxis = (value) => {
        const date = new Date(value);
        if (legend === "Annee") return date.getFullYear().toString();
        if (legend === "Mois") return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        if (legend === "Jour") return `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
        if (legend === "Year to Date") return `${String(date.getMonth() + 1).padStart(2, '0')}`;
        return value;
    };


    return (
        <div className="d-flex flex-column m-0 p-0 align-items-center w-100 h-100">
            <ResponsiveContainer width="80%" height={300}>
                <LineChart data={dataWithTimestamp}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                        dataKey="x"
                        stroke="white"
                        tick={{ fill: "white" }}
                        scale="time"
                        type="number"
                        domain={["dataMin", "dataMax"]}
                        ticks={getTicks(currentData, legend)}
                        tickFormatter={formatXAxis}
                    />
                    <YAxis stroke="white" tick={{ fill: "white" }} tickFormatter={(value) => `${(100 * value).toFixed(1)} %`} />
                    <Tooltip
                        formatter={(value) => [`${(100 * value).toFixed(1)} %`, "Valeur"]}
                        labelFormatter={(label) => new Date(label).toISOString().slice(0, 10)}
                    />
                    <Line type="linear" dataKey="y" stroke="#8884d8" strokeWidth={3} dot={false} />
                </LineChart>
            </ResponsiveContainer>

            <div className="d-flex flex-row align-items_center w-75">
                <Button className="bg-secondary m-2 flex-fill border-0" onClick={() => setLegend("Jour")}>
                    Jour
                </Button>
                <Button className="bg-secondary m-2 flex-fill border-0" onClick={() => setLegend("Mois")}>
                    Mois
                </Button>
                <Button className="bg-secondary m-2 flex-fill border-0" onClick={() => setLegend("Annee")}>
                    Année
                </Button>
                <Button className="bg-secondary m-2 flex-fill border-0" onClick={() => setLegend("Year to Date")}>
                    Year to Date
                </Button>

            </div>

        </div>
    );
}