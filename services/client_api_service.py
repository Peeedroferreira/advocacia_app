import requests
import json
from typing import Optional, List, Dict, Any

# URL base do seu API Gateway (incluindo o estágio, ex: /dev)
API_GATEWAY_CLIENTS_BASE_URL = "https://p55kko7yc6.execute-api.sa-east-1.amazonaws.com/dev"

class ClientApiService:
    def __init__(self, auth_token=None):
        self.auth_token = auth_token
        print(f"ClientApiService: Instanciado com token: {'Sim' if auth_token else 'Não'}")

    def _get_auth_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        # print(f"ClientApiService: Gerando headers: {headers}") # Descomente para debugging de headers
        return headers

    def _handle_api_error(self, http_err: requests.exceptions.HTTPError, operation_name: str) -> Dict[str, Any]:
        """Lida com erros HTTP e tenta parsear a resposta da Lambda."""
        print(f"ClientApiService: Erro HTTP em '{operation_name}': Status {http_err.response.status_code} - Resposta: {http_err.response.text}")
        try:
            error_body = http_err.response.json()
            if isinstance(error_body, str): # Se corpo for string JSON
                try:
                    error_body = json.loads(error_body)
                except json.JSONDecodeError:
                    # Mantém como string se não for JSON válido, mas loga
                    print(f"ClientApiService: Corpo do erro HTTP não era JSON decodificável: {error_body}")
            return error_body 
        except json.JSONDecodeError:
            return {"success": False, "message": f"Erro HTTP {http_err.response.status_code} em '{operation_name}'. Resposta não JSON: {http_err.response.text}"}
        except Exception as e: # Outro erro ao processar a resposta de erro
            return {"success": False, "message": f"Erro HTTP {http_err.response.status_code} em '{operation_name}'. Erro ao processar resposta de erro: {str(e)}"}

    def add_client(self, user_id: str, client_data: Dict[str, Any]) -> Dict[str, Any]:
        operation_name = "adicionar cliente"
        url = f"{API_GATEWAY_CLIENTS_BASE_URL}/users/{user_id}/clients"
        payload = client_data.copy() 

        print(f"ClientApiService ({operation_name}): Chamando URL: {url}")
        print(f"ClientApiService ({operation_name}): User ID: {user_id}")
        print(f"ClientApiService ({operation_name}): Payload: {json.dumps(payload)}")
        
        try:
            response = requests.post(url, headers=self._get_auth_headers(), data=json.dumps(payload), timeout=15)
            print(f"ClientApiService ({operation_name}): Resposta bruta status: {response.status_code}, texto: {response.text}")
            response.raise_for_status()
            return response.json() 
        except requests.exceptions.HTTPError as http_err:
            return self._handle_api_error(http_err, operation_name)
        except requests.exceptions.RequestException as req_err:
            print(f"ClientApiService ({operation_name}): Erro de requisição: {req_err}")
            return {"success": False, "message": f"Erro de comunicação ao {operation_name}: {str(req_err)}"}
        except Exception as e:
            print(f"ClientApiService ({operation_name}): Erro inesperado: {e}")
            return {"success": False, "message": f"Erro inesperado em {operation_name}: {str(e)}"}

    def get_clients_by_user(self, user_id: str) -> Dict[str, Any]:
        operation_name = "buscar clientes por usuário"
        url = f"{API_GATEWAY_CLIENTS_BASE_URL}/users/{user_id}/clients"

        print(f"ClientApiService ({operation_name}): Chamando URL: {url}")
        print(f"ClientApiService ({operation_name}): User ID: {user_id}")

        try:
            response = requests.get(url, headers=self._get_auth_headers(), timeout=15)
            print(f"ClientApiService ({operation_name}): Resposta bruta status: {response.status_code}, texto: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            error_response = self._handle_api_error(http_err, operation_name)
            if "clients" not in error_response:
                 error_response["clients"] = []
            return error_response
        except requests.exceptions.RequestException as req_err:
            print(f"ClientApiService ({operation_name}): Erro de requisição: {req_err}")
            return {"success": False, "message": f"Erro de comunicação ao {operation_name}: {str(req_err)}", "clients": []}
        except Exception as e:
            print(f"ClientApiService ({operation_name}): Erro inesperado: {e}")
            return {"success": False, "message": f"Erro inesperado em {operation_name}: {str(e)}", "clients": []}

    def get_client(self, user_id: str, client_cpf: str) -> Dict[str, Any]:
        operation_name = "buscar cliente específico"
        url = f"{API_GATEWAY_CLIENTS_BASE_URL}/users/{user_id}/clients/{client_cpf}"

        print(f"ClientApiService ({operation_name}): Chamando URL: {url}")
        print(f"ClientApiService ({operation_name}): User ID: {user_id}, CPF Cliente: {client_cpf}")
        
        try:
            response = requests.get(url, headers=self._get_auth_headers(), timeout=15)
            print(f"ClientApiService ({operation_name}): Resposta bruta status: {response.status_code}, texto: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            return self._handle_api_error(http_err, operation_name)
        except requests.exceptions.RequestException as req_err:
            print(f"ClientApiService ({operation_name}): Erro de requisição: {req_err}")
            return {"success": False, "message": f"Erro de comunicação ao {operation_name}: {str(req_err)}"}
        except Exception as e:
            print(f"ClientApiService ({operation_name}): Erro inesperado: {e}")
            return {"success": False, "message": f"Erro inesperado em {operation_name}: {str(e)}"}
            
    def update_client(self, user_id: str, client_cpf: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        operation_name = "atualizar cliente"
        url = f"{API_GATEWAY_CLIENTS_BASE_URL}/users/{user_id}/clients/{client_cpf}"
        payload = update_data.copy()

        print(f"ClientApiService ({operation_name}): Chamando URL: {url}")
        print(f"ClientApiService ({operation_name}): User ID: {user_id}, CPF Cliente: {client_cpf}")
        print(f"ClientApiService ({operation_name}): Payload: {json.dumps(payload)}")

        try:
            response = requests.put(url, headers=self._get_auth_headers(), data=json.dumps(payload), timeout=15)
            print(f"ClientApiService ({operation_name}): Resposta bruta status: {response.status_code}, texto: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            return self._handle_api_error(http_err, operation_name)
        except requests.exceptions.RequestException as req_err:
            print(f"ClientApiService ({operation_name}): Erro de requisição: {req_err}")
            return {"success": False, "message": f"Erro de comunicação ao {operation_name}: {str(req_err)}"}
        except Exception as e:
            print(f"ClientApiService ({operation_name}): Erro inesperado: {e}")
            return {"success": False, "message": f"Erro ao {operation_name}: {str(e)}"}

    def delete_client(self, user_id: str, client_cpf: str) -> Dict[str, Any]:
        operation_name = "remover cliente"
        url = f"{API_GATEWAY_CLIENTS_BASE_URL}/users/{user_id}/clients/{client_cpf}"

        print(f"ClientApiService ({operation_name}): Chamando URL: {url}")
        print(f"ClientApiService ({operation_name}): User ID: {user_id}, CPF Cliente: {client_cpf}")

        try:
            response = requests.delete(url, headers=self._get_auth_headers(), timeout=15)
            print(f"ClientApiService ({operation_name}): Resposta bruta status: {response.status_code}, texto: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            return self._handle_api_error(http_err, operation_name)
        except requests.exceptions.RequestException as req_err:
            print(f"ClientApiService ({operation_name}): Erro de requisição: {req_err}")
            return {"success": False, "message": f"Erro de comunicação ao {operation_name}: {str(req_err)}"}
        except Exception as e:
            print(f"ClientApiService ({operation_name}): Erro inesperado: {e}")
            return {"success": False, "message": f"Erro ao {operation_name}: {str(e)}"}

if __name__ == '__main__':
    print("--- Iniciando Testes do ClientApiService (simulados ou reais) ---")
    
    client_service = ClientApiService(auth_token="dummy_token_for_testing_if_needed") 
    test_user = "test_user_cli"

    print(f"\n--- Testando Adicionar Cliente para {test_user} ---")
    new_client_payload = {
        "client_cpf": "123.456.789-01", 
        "nome_completo": "Cliente Teste CLI",
        "email": "cli.client@example.com",
        "telefone_celular": "(00) 00000-0000"
    }
    # Para testar realmente, descomente e certifique-se que a API está no ar
    # add_result = client_service.add_client(test_user, new_client_payload)
    # print("Resultado de Adicionar Cliente:")
    # print(json.dumps(add_result, indent=2))

    print(f"\n--- Testando Listar Clientes para {test_user} ---")
    # list_result = client_service.get_clients_by_user(test_user)
    # print("Resultado de Listar Clientes:")
    # print(json.dumps(list_result, indent=2))
    
    print("\nLembre-se de descomentar as chamadas de API no if __name__ para testes reais.")
    print("--- Testes Concluídos (simulados) ---")
