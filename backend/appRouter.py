import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv
import os

from backend.ai.controller.AIController import AIController
# Importation des fonctionnalités
from backend.authentification.controllerConnexion import controllerConnexion
from backend.ai.controller.AILocalController import LocalController
from backend.portfolioGestion.controllerPortfolioGestion import controllerPortfolioGestion
#from tests_backend.test_router_benchmark import session_id

connexion = controllerConnexion()
ai = AIController()
#pour générer des chats en local
#TODO adapter les méthodes traditionnelles (old methods)
#ai = LocalController()
portfolioGestion = controllerPortfolioGestion()
load_dotenv()
frontend_url = os.getenv("FRONTEND_URL")

#initialisation de l'IA + mémoire + close à la fin de l'API
@asynccontextmanager
async def lifespan(app:FastAPI):
    await ai.initialize()
    yield
    await ai.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],  # accepte toutes les origines (simple pour dev)
    allow_credentials=True,
    allow_methods=["*"],  # accepte GET, POST, OPTIONS, PUT, DELETE...
    allow_headers=["*"],  # accepte tous les headers
)


@app.get("/api/auth/login")
async def auth_login():
    url = connexion.get_auth_url()
    return RedirectResponse(url)

@app.get("/api/auth/callback")
async def auth_callback(code: str):
    user, error = await connexion.handle_callback(code)
    if error:
        return RedirectResponse(f"{frontend_url}/login?error=auth_failed")
    
    token = connexion.create_jwt(user)
    return RedirectResponse(f"{frontend_url}/auth/callback?token={token}")

@app.post("/api/auth/set-session")
async def set_session(body: dict):
    token = body.get("token")
    response = JSONResponse(content={"success": True})
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=7 * 24 * 60 * 60,
    )
    return response

@app.get("/api/auth/me")
async def auth_me(request: Request):
    token = request.cookies.get("session")
    if not token:
        return {"success": False, "user": None}
    payload, error = connexion.verify_jwt(token)
    if error:
        return {"success": False, "user": None}
    return {"success": True, "user": payload}

@app.post("/api/auth/logout")
async def auth_logout(response: Response):
    response.delete_cookie("session")
    return {"success": True}


@app.post("/api/auth/signup")
async def sign_up(request : Request):
    data = await request.json()
    try : # On essaie de récupérer les données
        username = data["username"]
        email = data["email"]
        password = data["password"]
        confirmPassword = data["confirmPassword"]
    except KeyError:
        return {"success": False, "message": "Email, password or confirmPassword not provided", "username": None, "email": None}
    success, message = connexion.signUpAI(username, email, password, confirmPassword)
    return {"success": success, "message": message, "username": username if success else None, "email": email if success else None}

########################################
##### AI #####
########################################

@app.post("/api/ai/request")
async def ai_request(request : Request):
    data = await request.json()
    try : # On essaie de récupérer les données
        prompt = data["prompt"]
        email = data["email"]
        id_chat = data.get("id_chat", None)
        print(f"[INFO] {email} sent prompt for chat {id_chat}")
    except KeyError:
        return {"success": False, "message": "Prompt not provided", "response": None, "id_chat": None}
    answer = await ai.chat(id_chat,prompt)
    print(f"answer : {answer}")
    return {"success":answer.get("status",""),"message":prompt,"response":answer.get("message",""),"id_chat":id_chat}

@app.post("/api/ai/newChat")
async def ai_newChat(request:Request):
    data = await request.json()
    try:
        email = data["email"]
        chat_name = f"Chat_{int(time.time())}"
        status,session_id,log_message = await ai.create_chat_bdd(chat_name,email)
        print(f"[INFO] {email} created new chat {session_id}")
    except Exception as e:
        return {"success": False, "message": str(e), "chatId": None}

    try:
        status,message = await ai.create_chat(session_id=session_id,client_context={"email":email})
        print(f"creation chat langraph : {status}  et {message}")
    except Exception as e:
        return {"success":False,"message":str(e),"chatId":session_id}
    return {"success": True, "message": message, "chatId":session_id}

@app.post("/api/ai/getChat") 
async def ai_getChat(request : Request):
    #TODO fonction pour charger un chat
    data = await request.json()
    try : # On essaie de récupérer les données
        id_chat = data["id_chat"]
        email = data["email"]
        print(f"[INFO] {email} requested chat {id_chat}")
    except KeyError:
        return {"success": False, "message": "Chat name or username not provided", "response": None}

    response = await ai.get_chat(id_chat)
    print(f"get_chat  : {response}")
    return response

@app.post("/api/ai/getAllChats")
async def ai_getAllChats(request : Request):
    data = await request.json()
    try : # On essaie de récupérer les données
        email = data["email"]
        print(f"[INFO] {email} requested all chats")
    except KeyError:
        return {"success": False, "message": "Username not provided", "chats": None}
    
    success, chats, message = ai.getAllChatsAi(email)
    print(f"test liste des chats :  {chats}")
    if not success:
        return {"success": False, "message": message, "chats": None}
    
    return {"success": True, "message": "Chats retrieved", "chats": chats}

@app.post("/api/ai/deleteChat")
async def ai_deleteChat(request : Request):
    data = await request.json()
    try : # On essaie de récupérer les données
        id_chat = data["id_chat"]
        email = data["email"]
        print(f"[INFO] {email} requested deletion of chat {id_chat}")
    except KeyError:
        return {"success": False, "message": "Chat name or username not provided"}
    
    success, message = await ai.delete_chat(id_chat, email)
    return {"success": success, "message": message}

########################################
##### PORTFOLIO GESTION #####
########################################

@app.post("/api/portfolio/getAll")
async def portfolio_get(request : Request):

    data = await request.json()
    try : # On essaie de récupérer les données
        email = data["email"]
        print(f"[INFO] {email} requested all portfolios")
    except KeyError:
        return {"success": False, "message": "Email not provided", "portfolios": None}

    # Récupération des portfolios de l'utilisateur
    success, portfolios, message = portfolioGestion.get_portfolios(email)
    if not success:
        return {"success": False, "message": message, "portfolios": None}

    return {"success": True, "message": "Portfolios retrieved successfully", "portfolios": portfolios}

@app.post("/api/portfolio/get")
async def portfolio_get(request : Request):
    data = await request.json()
    try : # On essaie de récupérer les données
        email = data["email"]
        id_portfolio = data["id_portfolio"]
        print(f"[INFO] {email} requested portfolio {id_portfolio}")
    except KeyError:
        return {"success": False, "message": "Email or portfolio id not provided", "portfolio": None}
    
    success, portfolio_data, return_daily, return_monthly, return_yearly, return_year_to_date, message = portfolioGestion.get_portfolio(email, id_portfolio)
    if not success:
        return {"success": False, "message": message, "portfolio": None, "return_daily": None, "return_monthly": None, "return_yearly": None, "return_year_to_date": None}
    
    return {"success": True, "message": "Portfolio retrieved successfully", "portfolio": portfolio_data, "return_daily": return_daily, "return_monthly": return_monthly, "return_yearly": return_yearly, "return_year_to_date": return_year_to_date}


@app.post("/api/portfolio/delete")
async def portfolio_delete(request: Request):
    data = await request.json()
    try:  # On essaie de récupérer les données
        email = data["email"]
        id = data["portfolioId"]
        print(f"[INFO] {email} requested deletion of portfolio {id}")
    except KeyError:
        return {"success": False, "message": "Email not provided", "portfolios": None}

    # Récupération des portfolios de l'utilisateur
    success, message = portfolioGestion.delete_portfolio(email,id)
    if not success:
        return {"success": False, "message": message, "portfolios": None}

    return {"success": True, "message": f"Portfolio {id} deleted successfully"}