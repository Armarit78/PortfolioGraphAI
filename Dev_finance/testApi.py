from pathlib import Path
from signal import pthread_sigmask

import yfinance as yf
import pickle
from yfinance import screen

lu = yf.EquityQuery("is-in",
    ["exchange",
    "NMS", "NYQ", # USA
    "PAR", "AMS", "BRU", # Euronext
    "LSE",         # UK
    "GER", "FRA",  # Allemagne
    "JPX", "HKG",  # Japon / HK
    "TOR",         # Canada
    "EBS"          # Suisse (souvent noté EBS ou SWX)
])

MAX_SIZE = 250


def build_universe(query):
    data = screen(query, size=0, offset=0)
    count = data["total"]
    offset = 0
    print(count)

    # On initialise un dictionnaire pour stocker le mapping
    universe_dict = {}

    while offset < count:
        # Récupération des données pour la page actuelle
        page_data = screen(query, size=MAX_SIZE, offset=offset)

        # On met à jour le dictionnaire : {shortName: symbol}
        # On utilise une compréhension de dictionnaire pour plus de rapidité
        batch_mapping = {
            quote.get("longName",""): quote.get("symbol","")
            for quote in page_data["quotes"]
            if "symbol" in quote and "longName" in quote
        }

        universe_dict.update(batch_mapping)
        offset += MAX_SIZE
        print(offset)
        print(len(batch_mapping))

    return universe_dict

res = build_universe(lu)
path = Path("backend/portfolioConstruction/tests/tickers.pickle")
with path.open("wb") as f:
    pickle.dump(res,f,protocol=pickle.HIGHEST_PROTOCOL)
    print("ok")

