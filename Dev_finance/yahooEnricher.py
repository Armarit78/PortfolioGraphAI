import os.path
import pickle
import pandas as pd
import numpy as np
from tqdm import tqdm
from transformers.quantizers.quantizer_quark import CHECKPOINT_KEYS
from yfinance import Ticker


def load_pickle_to_dataframe(file_path: str) -> pd.DataFrame:
    with open(file_path, 'rb') as file:
        data = pickle.load(file)
    if isinstance(data, pd.DataFrame):
        return data
    elif isinstance(data, dict):
        return pd.DataFrame.from_dict(data)

    elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return pd.DataFrame(data)

    elif isinstance(data, np.ndarray):
        return pd.DataFrame(data)
    else:
        raise ValueError("Unsupported data type in pickle file")



def filter_yahoo_stock(ent:pd.DataFrame)->pd.DataFrame:
    # étape 1 : pour chaque longName, on garde la avgvolyme3m max
    ent = ent.sort_values(by=["longName", "avgvolume3m"], ascending=[True, False])
    # étape 2 : on supprime toutes les lignes non traités dans les 3 mois et sans market_cap
    ent = ent.dropna(subset=["avgvolume3m", "market_cap"])
    # étape 3: on supprime tous les doublons de longName (on garde le premier)
    ent = ent.sort_values(by=["longName", "avgvolume3m"], ascending=[True, False])
    ent = ent.drop_duplicates(subset=["longName"], keep="first")
    # étape 4 : on construit la colonne shortTicker
    ent["shortTicker"] = ent["ticker"].str.split(".").str[0]
    # étape 5 : on refiltre pour ne garder qu'une instance
    ent = ent.sort_values(by=["shortTicker", "avgvolume3m"], ascending=[True, False])
    # ent = ent.drop_duplicates(subset=["shortTicker"],keep="first")
    # étape 6 = p, refiltre pour ne garde qu'une instance de shortName
    ent = ent.sort_values(by=["shortName", "avgvolume3m"], ascending=[True, False])
    ent = ent.drop_duplicates(subset=["shortName"], keep="first")
    return ent


def fetch_infos(ticker):
    try:
        t = Ticker(ticker).info
        return t.get("industry",None),t.get("longBusinessSummary",None),t.get("website",None)
    except Exception as e:
        return "Erreur","Erreur","Erreur"

BATCH_SIZE = 500
CHECKPOINT_PATH = "checkpoint.csv"
NEW_COLUMNS = ["industry","summary","website"]

if __name__ == "__main__":

    if os.path.exists(CHECKPOINT_PATH):
        ent = pd.read_csv(CHECKPOINT_PATH)
        print("reprise...")
    else:
        ent = pd.read_csv("stocks_yahoo.csv")
        ent = filter_yahoo_stock(ent)
        for col in NEW_COLUMNS:
            if col not in ent.columns:
                ent[col] = None

    for i in tqdm(ent.index):
        if pd.isna(ent.at[i,"industry"]):
            ticker = ent.at[i, "ticker"]
            industry,summary,website = fetch_infos(ticker)
            ent.at[i, "industry"] = industry
            ent.at[i, "summary"] = summary
            ent.at[i, "website"] = website

        if (i+1)%BATCH_SIZE == 0:
            print("Batch done..., next batch")
            ent = filter_yahoo_stock(ent)
            ent.to_csv(CHECKPOINT_PATH,index=False)

    ent.to_pickle("stocks_yahoo_enriched.pickle")
    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)
    print("done")


