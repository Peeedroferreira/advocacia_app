import requests 
import json

API_GATEWAY_BASE_URL = "https://p55kko7yc6.execute-api.sa-east-1.amazonaws.com/dev"
API_GATEWAY_LOGIN_ENDPOINT = f"{API_GATEWAY_BASE_URL}/login"
API_GATEWAY_REGISTER_ENDPOINT = f"{API_GATEWAY_BASE_URL}/register" 

class AuthService:
    def __init__(self):
        pass

    def _process_lambda_response(self, response, operation_name="operação"):
        """Processa a resposta HTTP e extrai o corpo da resposta da Lambda."""
        print(f"Resposta bruta da {operation_name} (status {response.status_code}): {response.text}")
        response.raise_for_status() # Lança exceção para respostas de erro HTTP (4xx ou 5xx)
        
        lambda_response_data = response.json() # Resposta completa do API Gateway
        
        if 'body' in lambda_response_data and isinstance(lambda_response_data['body'], str):
            try:
                body_data = json.loads(lambda_response_data['body'])
                print(f"Corpo da resposta da Lambda ({operation_name}, parseado): {body_data}")
                return body_data # Este é o dict com 'success', 'message', etc.
            except json.JSONDecodeError as e:
                print(f"Erro ao fazer parse do JSON no 'body' da resposta da Lambda ({operation_name}): {e}")
                print(f"String do 'body' que causou o erro: {lambda_response_data['body']}")
                return {"success": False, "message": f"Resposta inválida do servidor (formato do corpo na {operation_name})."}
        elif 'success' in lambda_response_data: # Fallback se não for proxy e a Lambda retornar diretamente
            print(f"Usando resposta direta da Lambda (sem 'body' de proxy, {operation_name}): {lambda_response_data}")
            return lambda_response_data
        else:
            print(f"Estrutura de resposta inesperada da Lambda ({operation_name}): {lambda_response_data}")
            return {"success": False, "message": f"Resposta inválida do servidor (estrutura na {operation_name})."}

    def _handle_request_exception(self, e, operation_name="operação"):
        """Lida com exceções comuns do requests."""
        if isinstance(e, requests.exceptions.HTTPError):
            error_message = f"Erro HTTP na {operation_name}: {e}"
            if e.response is not None:
                try:
                    print(f"Resposta de erro HTTP ({operation_name}): {e.response.text}")
                    # Tenta extrair a mensagem de erro do corpo da resposta da Lambda, se existir
                    error_details_outer = e.response.json()
                    if 'body' in error_details_outer and isinstance(error_details_outer['body'], str):
                        try:
                            body_error_details = json.loads(error_details_outer['body'])
                            if 'message' in body_error_details:
                                return {"success": False, "message": body_error_details['message']}
                        except json.JSONDecodeError:
                            pass # Usa a mensagem externa
                    if 'message' in error_details_outer: # Se a mensagem estiver no nível superior
                         return {"success": False, "message": error_details_outer['message']}
                    error_message += f" - Detalhes: {error_details_outer}"

                except json.JSONDecodeError:
                    error_message += f" - Resposta não JSON: {e.response.text}"
            print(error_message)
            return {"success": False, "message": f"Erro de comunicação com o servidor ({operation_name})."}
        elif isinstance(e, requests.exceptions.ConnectionError):
            print(f"Erro de conexão na {operation_name}: {e}")
            return {"success": False, "message": f"Não foi possível conectar ao servidor ({operation_name})."}
        elif isinstance(e, requests.exceptions.Timeout):
            print(f"Timeout na requisição de {operation_name}: {e}")
            return {"success": False, "message": f"A requisição de {operation_name} demorou muito."}
        else: # requests.exceptions.RequestException ou outros
            print(f"Erro na requisição de {operation_name}: {e}")
            return {"success": False, "message": f"Erro inesperado ({operation_name}): {e}"}

    def login(self, username: str, password: str) -> dict:
        payload = {"username": username, "password": password}
        headers = {"Content-Type": "application/json"}
        api_url = API_GATEWAY_LOGIN_ENDPOINT

        try:
            print(f"Tentando login para {username} em {api_url}...")
            print(f"PAYLOAD DE LOGIN A SER ENVIADO: {json.dumps(payload)}")
            response = requests.post(api_url, data=json.dumps(payload), headers=headers, timeout=15)
            return self._process_lambda_response(response, "login")
        except Exception as e:
            return self._handle_request_exception(e, "login")

    def register(self, username: str, password: str, email: str = None) -> dict:
        payload = {"username": username, "password": password}
        if email: 
            payload["email"] = email
        headers = {"Content-Type": "application/json"}
        api_url = API_GATEWAY_REGISTER_ENDPOINT

        try:
            print(f"Tentando registrar usuário {username} em {api_url}...")
            print(f"PAYLOAD DE REGISTRO A SER ENVIADO: {json.dumps(payload)}")
            response = requests.post(api_url, data=json.dumps(payload), headers=headers, timeout=15)
            return self._process_lambda_response(response, "registro")
        except Exception as e:
            return self._handle_request_exception(e, "registro")

if __name__ == '__main__':
    auth = AuthService()
    
    print("--- Teste de Login (chamada real) ---")
    result_admin_login = auth.login("admin", "Pedromaster12!") 
    print("Resultado final do login para 'admin':")
    print(json.dumps(result_admin_login, indent=2))

    print("\n--- Teste de Registro (chamada real) ---")
    # Use um nome de usuário diferente a cada teste de registro para evitar conflitos
    import uuid
    unique_id = str(uuid.uuid4())[:8] # Gera um ID curto e único
    new_username = f"teste_usuario_{unique_id}"
    new_password = "outraSenhaForte456!"
    new_email = f"{new_username}@exemplo.com"
    
    result_register = auth.register(new_username, new_password, new_email)
    print(f"Resultado do registro para {new_username}:")
    print(json.dumps(result_register, indent=2))

    if result_register.get("success"):
        print(f"\n--- Testando login com usuário recém-criado: {new_username} ---")
        result_new_user_login = auth.login(new_username, new_password)
        print("Resultado final do login para novo usuário:")
        print(json.dumps(result_new_user_login, indent=2))

    print("\n--- Teste de login inválido (chamada real) ---")
    result_invalid_login = auth.login("usuario_que_nao_existe_mesmo", "senha_qualquer_errada")
    print("Resultado final do login inválido:")
    print(json.dumps(result_invalid_login, indent=2))
