import requests
import pandas as pd
import time
import os


class EODHDScraper:
    def __init__(self, api_token):
        self.api_token = api_token
        self.base_url = "https://eodhd.com/api"

    def get_exchanges(self):
        """Récupère la liste de toutes les places boursières mondiales disponibles."""
        url = f"{self.base_url}/exchanges-list/"
        params = {"api_token": self.api_token, "fmt": "json"}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la récupération des échanges : {e}")
            return []

    def get_symbols_for_exchange(self, exchange_code):
        """Récupère tous les tickers pour un code d'échange donné (ex: 'PA', 'US', 'LSE')."""
        url = f"{self.base_url}/exchange-symbol-list/{exchange_code}"
        params = {"api_token": self.api_token, "fmt": "json"}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erreur pour l'échange {exchange_code} : {e}")
            return []

    def run(self, limit_exchanges=None, filename="market_data.pickle"):
        """
        Exécute le workflow complet :
        1. Liste les échanges
        2. Récupère les tickers
        3. Filtre les actions ordinaires
        4. Sauvegarde en .pickle
        """
        all_symbols = []
        exchanges = self.get_exchanges()

        # Filtrage optionnel (ex: ['US', 'PA']) pour ne pas vider son quota
        if limit_exchanges:
            exchanges = [e for e in exchanges if e['Code'] in limit_exchanges]

        if not exchanges:
            print("Aucun échange trouvé. Vérifiez votre clé API.")
            return

        print(f"--- Début de l'extraction ({len(exchanges)} places boursières) ---")

        for ex in exchanges:
            code = ex['Code']
            name = ex['Name']
            print(f"Récupération : {name} [{code}]...")

            symbols = self.get_symbols_for_exchange(code)

            if symbols:
                # Ajout du nom de l'échange et de la zone géographique pour chaque ligne
                for s in symbols:
                    s['Exchange_Full_Name'] = name
                    s['Operating_MIC'] = ex.get('OperatingMIC')
                all_symbols.extend(symbols)

            # Respecter une légère pause pour l'API
            time.sleep(0.1)

        # Conversion en DataFrame
        df = pd.DataFrame(all_symbols)

        if not df.empty:
            # Nettoyage : On ne garde que les actions (Common Stock)
            # On retire les entrées sans Ticker ou sans Nom
            df = df[df['Type'] == 'Common Stock']
            df = df.dropna(subset=['Code', 'Name'])

            # Sauvegarde en format binaire Pickle
            df.to_pickle(filename)
            print(f"\nExtraction terminée !")
            print(f"Fichier sauvegardé : {os.path.abspath(filename)}")
            print(f"Nombre total d'entreprises : {len(df)}")
            return df
        else:
            print("Aucune donnée récupérée.")
            return None


# --- CONFIGURATION ET EXÉCUTION ---
if __name__ == "__main__":
    # 1. Remplacez par votre clé API réelle
    # Note : Le token 'demo' ne fonctionne que pour 'US' et 'PA'
    MY_API_KEY = "69b2e1193bd517.62223522"

    scraper = EODHDScraper(MY_API_KEY)

    # 2. Lancer l'extraction
    # Laissez limit_exchanges=None pour tenter tout le monde (attention au quota !)
    df_final = scraper.run(limit_exchanges=None, filename="entreprises_cotees.pickle")

    # 3. Aperçu rapide
    if df_final is not None:
        print("\n--- Aperçu des données ---")
        print(df_final[['Code', 'Name', 'Exchange', 'Currency']].head())