"""
Yahoo Finance — Screener complet d'actions
==========================================
Utilise yf.screen() avec EquityQuery pour récupérer toutes les actions
disponibles sur Yahoo Finance (pas de liste de tickers en dur).

Colonnes du DataFrame final :
  ticker | name | isin | market_cap

Export : stocks_yahoo.pkl  (+ stocks_yahoo.csv pour lecture humaine)

Dépendances :
    pip install yfinance pandas

Limitations connues :
  - Yahoo Finance plafonne à 250 résultats par requête.
    Le script pagine sur plusieurs régions pour maximiser la couverture.
  - L'ISIN est récupéré via yf.Ticker(t).isin (appel réseau par ticker).
    Pour des milliers d'actions, cette étape peut prendre plusieurs minutes.
    Désactivez-la (FETCH_ISIN = False) si vous n'avez pas besoin des ISIN.
"""

import time
import pandas as pd
import yfinance as yf
from yfinance import EquityQuery, Ticker

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
FETCH_ISIN   = False    # False = plus rapide, mais ISIN absent
PAGE_SIZE    = 250     # max autorisé par Yahoo
DELAY_SCREEN = 0.3     # secondes entre deux appels screener
DELAY_ISIN   = 0.25    # secondes entre deux appels Ticker.isin
OUTPUT_PKL   = "stocks_yahoo_enriched.pkl"
OUTPUT_CSV   = "stocks_yahoo_enriched.csv"

# Régions couvertes par Yahoo Finance Screener
REGIONS = [
    "us", "ca",                            # Amérique du Nord
    "fr", "de", "gb", "es", "it", "nl",   # Europe occidentale
    "ch", "se", "no", "dk", "fi", "be",   # Europe nordique / Benelux
    "pt", "at", "ie", "pl", "cz", "hu",   # Europe périphérique
    "au", "nz",                            # Océanie
    "jp", "cn", "hk", "kr", "tw", "in",   # Asie principale
    "sg", "th", "my", "id", "ph",          # Asie du Sud-Est
    "br", "mx", "ar", "cl",               # Amérique latine
    "za", "eg",                            # Afrique
    "il", "sa"                   # Moyen-Orient
]


# ---------------------------------------------------------------------------
# Étape 1 — Collecte des tickers via le screener
# ---------------------------------------------------------------------------

def screen_region(region: str) -> list[dict]:
    """
    Pagine sur toutes les pages disponibles pour une région donnée.
    Retourne une liste de dicts bruts issus du screener Yahoo.
    """
    query = EquityQuery("eq", ["region", region])
    results = []
    offset = 0
    max_offset = 251

    while offset<max_offset:
        try:
            resp = yf.screen(
                query,
                offset=offset,
                size=PAGE_SIZE,
                sortField="intradaymarketcap",
                sortAsc=False,
            )
            max_offset = resp['total']
        except Exception as e:
            print(f"    ⚠ Erreur screener (region={region}, offset={offset}) : {e}")
            break

        quotes = resp.get("quotes", []) if isinstance(resp, dict) else []
        if not quotes:
            break

        results.extend(quotes)
        print(f"    région={region:4s}  offset={offset:5d}  +{len(quotes)} actions "
              f"(total région : {len(results)})")

        if len(quotes) < PAGE_SIZE:
            break  # dernière page

        offset += PAGE_SIZE
        time.sleep(DELAY_SCREEN)

    return results


def collect_all_tickers() -> pd.DataFrame:
    """
    Parcourt toutes les régions et dédoublonne par ticker.
    Retourne un DataFrame avec : ticker, name, market_cap.
    """
    all_quotes: list[dict] = []
    seen: set[str] = set()

    for region in REGIONS:
        print(f"\n→ Région : {region.upper()}")
        quotes = screen_region(region)
        nb_quotes = len(quotes)
        for i,q in enumerate(quotes):
            sym = q.get("symbol", "")
            print(f"Quote {i} / {nb_quotes}")
            infos = Ticker(sym).get_info()
            all_quotes.append({
                "ticker":     sym,
                "longName":       q.get("longName") or q.get("shortName") or q.get("displayName") or None,
                "shortName" : q.get("shortName") or None,
                "market_cap": q.get("marketCap") or None,
                "region": q.get("region") or None,
                "quoteType":q.get("quoteType") or None,
                "exchange":q.get("exchange") or None,
                "exchangeFullName":q.get("fullExchangeName") or None,
                "avgvolume3m":q.get("averageDailyVolume3Month") or None,
                "industry":infos.get("industry") or None,
                "longBusinessSummary":infos.get("longBusinessSummary") or None,
                "website":infos.get("website") or None,
            })
        time.sleep(DELAY_SCREEN)

    df = pd.DataFrame(all_quotes, columns=["ticker", "longName","shortName", "market_cap","region","quoteType","exchange","exchangeFullName","avgvolume3m","industry","longBusinessSummary","website"])
    return df


# ---------------------------------------------------------------------------
# Étape 2 — Enrichissement ISIN (optionnel)
# ---------------------------------------------------------------------------

def enrich_isin(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pour chaque ticker, tente de récupérer l'ISIN via yf.Ticker(t).isin.
    Ajoute une colonne 'isin' au DataFrame.
    """
    isins: list[str] = []
    n = len(df)

    for i, ticker in enumerate(df["ticker"]):
        if (i + 1) % 100 == 0 or i == 0:
            print(f"  ISIN : {i+1}/{n}  ({ticker})")
        try:
            isin = yf.Ticker(ticker).isin or "N/A"
        except Exception:
            isin = "N/A"
        isins.append(isin)
        time.sleep(DELAY_ISIN)

    df = df.copy()
    df.insert(2, "isin", isins)   # colonne après 'name'
    return df


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 65)
    print("  Yahoo Finance — Screener complet d'actions")
    print("=" * 65)

    # --- Screener ---
    print("\n[1/3] Collecte des tickers via yf.screen()…")
    df = collect_all_tickers()
    print(f"\n  → {len(df)} actions uniques récupérées.")

    # --- ISIN ---
    if FETCH_ISIN:
        print(f"\n[2/3] Récupération des ISIN (peut prendre du temps)…")
        df = enrich_isin(df)
    else:
        df.insert(2, "isin", "N/A")
        print("\n[2/3] Récupération ISIN désactivée (FETCH_ISIN=False).")

    # --- Tri & export ---
    print("\n[3/3] Export…")
    df = df.sort_values("market_cap", ascending=False, na_position="last") \
           .reset_index(drop=True)

    # Pickle
    df.to_pickle(OUTPUT_PKL)
    print(f"  ✅ Pickle  → {OUTPUT_PKL}")

    # CSV (lecture humaine)
    df_csv = df.copy()
    df_csv["market_cap"] = df_csv["market_cap"].apply(
        lambda v: f"${v/1e9:.2f}B" if pd.notna(v) and v >= 1e9
        else (f"${v/1e6:.2f}M" if pd.notna(v) and v >= 1e6 else ("N/A" if pd.isna(v) else str(v)))
    )
    df_csv.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"  ✅ CSV     → {OUTPUT_CSV}")

    print(f"\n{'='*65}")
    print(f"  TERMINÉ — {len(df)} actions  |  colonnes : {list(df.columns)}")
    print(f"{'='*65}")
    print("\nAperçu (top 10 par capitalisation) :")
    print(df.head(10).to_string(index=True))

    # --- Rechargement exemple ---
    print("\n\n# Pour recharger le pickle dans un autre script :")
    print("# import pandas as pd")
    print(f'# df = pd.read_pickle("{OUTPUT_PKL}")')
    print("# print(df.head())")