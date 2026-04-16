from .serviceLogin import serviceLogin

class controllerConnexion:
    '''
    Classe de contrôle de la connexion et de l'inscription des utilisateurs
    Gère la logique de connexion et d'inscription en interagissant avec les services appropriés
    '''
    
    def __init__(self, login=None):
        self.serviceLogin = login or serviceLogin()

    def get_auth_url(self):
        return self.serviceLogin.get_auth_url()

    async def handle_callback(self, code: str):
        return await self.serviceLogin.handle_callback(code)
    
    def create_jwt(self, user):
        return self.serviceLogin.create_jwt(user)

    def verify_jwt(self, token):
        return self.serviceLogin.verify_jwt(token)
