import { DataGrid } from '@mui/x-data-grid';
import { Box } from '@mui/material';

export const PortfolioTable = ({ portfolioData, columnsToShow }) => {
  console.log("portfolioData reçu : ", portfolioData);

  const columns = [
    { field: "name", headerName: "Nom", flex: 1 },
    { field: "ticker", headerName: "Ticker", flex: 1 },
    {
      field: "weight",
      headerName: "Poids",
      type: 'number',
      valueFormatter: (value) => value.toLocaleString('fr-FR', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }),
      flex: 1
    },
    {
      field: "unit_buy_price",
      headerName: "Cours Achat",
      type: 'number',
      valueFormatter: (value) => value.toLocaleString('fr-FR', {
    style: 'currency',
        currency:'EUR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }),
      flex: 1
    },
    {
      field: "unit_price",
      headerName: "Cours Actuel",
      type: 'number',
      valueFormatter: (value) => value.toLocaleString('fr-FR', {
    style: 'currency',
        currency:'EUR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }),
      flex: 1
    },
    {
      field: "pnl",
      headerName: "P&L",
      type: 'number',
      flex: 1,
      valueFormatter: (value) => `${(value * 100).toFixed(2)}  %`,
      cellClassName: (params) => {
        if (params.value == null) return '';

      return params.value >= 0
        ? 'text-success'
        : 'text-danger';
      },
    }
  ];

  const columns_displayed = columns.filter((c)=>(columnsToShow.includes(c.field)));

  return (
    // On définit une hauteur pour que le tableau soit visible
    <Box className="m-3" sx={{ height: 400, width: '75%', mt: 2 }}>
      <DataGrid
        rows={portfolioData}
        columns={columns_displayed}
        sortModel={[{ field: 'weight', sort: 'desc' }]}
        getRowId={(row) => row.ticker}
        pageSizeOptions={[5, 10]}
        disableRowSelectionOnClick
      />
    </Box>
  );
};