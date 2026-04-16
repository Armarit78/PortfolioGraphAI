
from supabase import create_client
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv
from dacite import from_dict
import json

from backend.ai.core.llm import dbg
from backend.portfolioConstruction.Portfolio import Portfolio

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
FERNET_KEY = os.getenv("FERNET_KEY")

if FERNET_KEY is None:
    raise ValueError("FERNET_KEY is not set in environment variables")

class ServiceSavePortfolio:
    def __init__(self):
        self.fernet = Fernet(FERNET_KEY)
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        

    def create_portfolio(self, user_email, portfolio : Portfolio):
        # Obtenir l'id du portefeuille
        try:
            id_portfolio = max(self.get_portfolios_list(user_email)[1]) + 1
        except Exception as e:
            print(f"Error getting portfolio list: {e}")
            id_portfolio = 1
        
        data = {"id" : id_portfolio, "user_email": user_email}
        
        portfolio_data = portfolio
        
        data["content"] = self.encrypt_portfolio(portfolio_data).decode()
        
        
        try:
            self.supabase.table("portfolios").insert(data).execute()
            return True, "Portfolio created successfully"
        except Exception as e:
            print(f"Error inserting portfolio: {e}")
            return False, f"Error inserting portfolio: {str(e)}"

    def save_portfolio(self, user_email, portfolio_id, portfolio):
        pass
    
    def get_portfolio(self, user_email, portfolio_id):
        
        try :
            response = self.supabase.table("portfolios").select("*").eq("id", portfolio_id).eq("user_email", user_email).execute()
            if not response.data or len(response.data) == 0:
                return False, None, "Portfolio not found or does not belong to the user"
            
            encrypted_content = response.data[0]["content"]
            decrypted_content = self.decrypt_portfolio(encrypted_content.encode())
            dbg("Decrypted Content : ",decrypted_content)
            portfolio = from_dict(data_class=Portfolio,data=decrypted_content)
            dbg("Portfolio from BDD : ",portfolio)
            return True, portfolio, "Portfolio retrieved successfully"
        except Exception as e:
            print(f"Error fetching portfolio: {e}")
            return False, None, f"Error fetching portfolio: {str(e)}"
        
    
    def get_portfolios_list(self, user_email):
        
        try :
            response = self.supabase.table("portfolios").select("id").eq("user_email", user_email).execute()
            ids = list(set([row["id"] for row in response.data]))
            return True, ids, "Portfolios retrieved successfully"
        except Exception as e:
            print(f"Error fetching portfolios: {e}")
            return False, [], f"Error fetching portfolios: {str(e)}"
    
    def encrypt_portfolio(self, portfolio: Portfolio):
        token = self.fernet.encrypt(json.dumps(portfolio).encode())
        return token

    def decrypt_portfolio(self, token: bytes):
        return json.loads(self.fernet.decrypt(token).decode())
    
    def delete_portfolio(self, email, portfolio_id):
        if portfolio_id == 0:
            return True, "Portfolio deleted successfully"
        try:
            # Vérifier que le portefeuille appartient à l'utilisateur
            response = self.supabase.table("portfolios").select("*").eq("id", portfolio_id).eq("user_email", email).execute()
            if not response.data or len(response.data) == 0:
                return False, "Portfolio not found or does not belong to the user"
                        
            # Supprimer le portefeuille
            self.supabase.table("portfolios").delete().eq("id", portfolio_id).eq("user_email", email).execute()
            
            return True, "Portfolio deleted successfully"
        except Exception as e:
            return False, f"Error deleting portfolio: {str(e)}"