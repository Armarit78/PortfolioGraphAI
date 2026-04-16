import os
import pickle
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

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


if __name__ == "__main__":
    ent = load_pickle_to_dataframe("stocks_yahoo_enriched.pickle")
    ent = ent.sort_values(by=["website", "avgvolume3m"], ascending=[True, False])
    ent = ent.drop_duplicates(subset=["website"], keep="first")
    ent["richString"] = "Ticker : " + ent["ticker"] + " | LongName : " + ent["longName"] + " | ShortName : " + ent[
        "shortName"] + " | Industry : " + ent["industry"] + " | Summary : " + ent["summary"].str[:500]
    model = SentenceTransformer("all-MiniLM-L6-v2")
    richString = ent["richString"].fillna("").to_list()
    print(richString)

    embeddings = model.encode(richString, convert_to_tensor=True, show_progress_bar=True)

    torch.save(embeddings, "company_embeddings.pt")
    ent.to_pickle("company_enriched.pickle")


