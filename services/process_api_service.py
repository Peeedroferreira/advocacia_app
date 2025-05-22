import requests
import json
from typing import List, Dict, Optional, Any, Tuple

# URL base do seu API Gateway (mesma do client_api_service, se for a mesma API)
API_GATEWAY_PROCESSES_BASE_URL = "https://p55kko7yc6.execute-api.sa-east-1.amazonaws.com/dev" # Ajuste se necessário

class ProcessApiService:
    def __init__(self, auth_token: Optional[str] = None):
        self.auth_token = auth_token
        print(f"ProcessApiService: Instanciado com token: {'Sim' if auth_token else 'Não'}")

    def _get_auth_headers(self) -> Dict[str, str]:
        headers = {} # Não define Content-Type por defeito, pois pode variar (JSON vs multipart)
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _handle_api_error(self, http_err: requests.exceptions.HTTPError, operation_name: str) -> Dict[str, Any]:
        print(f"ProcessApiService: Erro HTTP em '{operation_name}': Status {http_err.response.status_code} - Resposta: {http_err.response.text}")
        try:
            error_body = http_err.response.json()
            if isinstance(error_body, str):
                try: error_body = json.loads(error_body)
                except json.JSONDecodeError: pass # Mantém como string se não for JSON
            return error_body 
        except json.JSONDecodeError:
            return {"success": False, "message": f"Erro HTTP {http_err.response.status_code} em '{operation_name}'. Resposta não JSON."}
        except Exception as e:
            return {"success": False, "message": f"Erro HTTP {http_err.response.status_code} em '{operation_name}'. Erro ao processar resposta: {str(e)}"}

    def add_process(self, user_id: str, process_data: Dict[str, Any], files_to_upload: Optional[List[Tuple[str, Any]]] = None) -> Dict[str, Any]:
        operation_name = "adicionar processo"
        url = f"{API_GATEWAY_PROCESSES_BASE_URL}/users/{user_id}/processes"
        
        headers = self._get_auth_headers()
        # Se houver ficheiros, não defina Content-Type: application/json.
        # A biblioteca `requests` definirá o Content-Type correto para multipart/form-data.
        # O payload JSON dos dados do processo será enviado como um campo 'process_data' no multipart.
        
        request_files = None
        data_payload = None

        if files_to_upload:
            # `requests` espera uma lista de tuplos para 'files': (fieldname, (filename, fileobject, content_type))
            request_files = files_to_upload # Já deve estar no formato correto
            # Envia os dados do processo como um campo de formulário JSON
            data_payload = {'process_data_json': json.dumps(process_data)}
            # Não definir Content-Type nos headers, requests fará isso para multipart
            if 'Content-Type' in headers:
                del headers['Content-Type'] 
            print(f"ProcessApiService ({operation_name}): Enviando com multipart/form-data.")
        else:
            # Sem ficheiros, envia como JSON normal
            headers["Content-Type"] = "application/json"
            data_payload = json.dumps(process_data)
            print(f"ProcessApiService ({operation_name}): Enviando com application/json.")

        print(f"ProcessApiService ({operation_name}): Chamando URL: {url}")
        print(f"ProcessApiService ({operation_name}): User ID: {user_id}")
        if files_to_upload:
            print(f"ProcessApiService ({operation_name}): Dados do processo (como form field): {data_payload}")
            print(f"ProcessApiService ({operation_name}): {len(files_to_upload)} ficheiros a serem enviados.")
        else:
            print(f"ProcessApiService ({operation_name}): Payload JSON: {data_payload}")
        
        try:
            if files_to_upload:
                response = requests.post(url, headers=headers, data=data_payload, files=request_files, timeout=60) # Timeout maior para uploads
            else:
                response = requests.post(url, headers=headers, data=data_payload, timeout=15)
                
            print(f"ProcessApiService ({operation_name}): Resposta bruta status: {response.status_code}, texto: {response.text}")
            response.raise_for_status()
            return response.json() 
        except requests.exceptions.HTTPError as http_err:
            return self._handle_api_error(http_err, operation_name)
        except requests.exceptions.RequestException as req_err:
            print(f"ProcessApiService ({operation_name}): Erro de requisição: {req_err}")
            return {"success": False, "message": f"Erro de comunicação ao {operation_name}: {str(req_err)}"}
        except Exception as e:
            print(f"ProcessApiService ({operation_name}): Erro inesperado: {e}")
            return {"success": False, "message": f"Erro inesperado em {operation_name}: {str(e)}"}

    def get_processes_by_user(self, user_id: str, search_term: Optional[str] = None) -> Dict[str, Any]:
        operation_name = "buscar processos por utilizador"
        url = f"{API_GATEWAY_PROCESSES_BASE_URL}/users/{user_id}/processes"
        params = {}
        if search_term:
            params['q'] = search_term # Exemplo de parâmetro de query para busca

        print(f"ProcessApiService ({operation_name}): Chamando URL: {url} com params: {params}")
        try:
            headers = self._get_auth_headers()
            headers["Content-Type"] = "application/json" # GET não tem corpo, mas é bom ser explícito
            response = requests.get(url, headers=headers, params=params, timeout=15)
            print(f"ProcessApiService ({operation_name}): Resposta bruta status: {response.status_code}, texto: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            error_response = self._handle_api_error(http_err, operation_name)
            if "processes" not in error_response: error_response["processes"] = []
            return error_response
        except requests.exceptions.RequestException as req_err:
            print(f"ProcessApiService ({operation_name}): Erro de requisição: {req_err}")
            return {"success": False, "message": f"Erro de comunicação: {str(req_err)}", "processes": []}
        except Exception as e:
            print(f"ProcessApiService ({operation_name}): Erro inesperado: {e}")
            return {"success": False, "message": f"Erro inesperado: {str(e)}", "processes": []}

    def get_process_details(self, user_id: str, process_id: str) -> Dict[str, Any]:
        operation_name = "buscar detalhes do processo"
        url = f"{API_GATEWAY_PROCESSES_BASE_URL}/users/{user_id}/processes/{process_id}"
        print(f"ProcessApiService ({operation_name}): Chamando URL: {url}")
        try:
            headers = self._get_auth_headers()
            headers["Content-Type"] = "application/json"
            response = requests.get(url, headers=headers, timeout=15)
            print(f"ProcessApiService ({operation_name}): Resposta bruta status: {response.status_code}, texto: {response.text}")
            response.raise_for_status()
            # Espera-se {'success': True, 'process': {...}, 'documents': [...]}
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            return self._handle_api_error(http_err, operation_name)
        except requests.exceptions.RequestException as req_err:
            print(f"ProcessApiService ({operation_name}): Erro de requisição: {req_err}")
            return {"success": False, "message": f"Erro de comunicação: {str(req_err)}"}
        except Exception as e:
            print(f"ProcessApiService ({operation_name}): Erro inesperado: {e}")
            return {"success": False, "message": f"Erro inesperado: {str(e)}"}

    def update_process(self, user_id: str, process_id: str, process_data: Dict[str, Any], files_to_upload: Optional[List[Tuple[str, Any]]] = None) -> Dict[str, Any]:
        operation_name = "atualizar processo"
        url = f"{API_GATEWAY_PROCESSES_BASE_URL}/users/{user_id}/processes/{process_id}"
        
        headers = self._get_auth_headers()
        request_files = None
        data_payload = None

        if files_to_upload:
            request_files = files_to_upload
            data_payload = {'process_data_json': json.dumps(process_data)}
            if 'Content-Type' in headers: del headers['Content-Type']
            print(f"ProcessApiService ({operation_name}): Enviando com multipart/form-data (PUT).")
        else:
            headers["Content-Type"] = "application/json"
            data_payload = json.dumps(process_data)
            print(f"ProcessApiService ({operation_name}): Enviando com application/json (PUT).")

        print(f"ProcessApiService ({operation_name}): Chamando URL: {url}")
        try:
            if files_to_upload:
                response = requests.put(url, headers=headers, data=data_payload, files=request_files, timeout=60)
            else:
                response = requests.put(url, headers=headers, data=data_payload, timeout=15)
            print(f"ProcessApiService ({operation_name}): Resposta bruta status: {response.status_code}, texto: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            return self._handle_api_error(http_err, operation_name)
        except requests.exceptions.RequestException as req_err:
            print(f"ProcessApiService ({operation_name}): Erro de requisição: {req_err}")
            return {"success": False, "message": f"Erro de comunicação: {str(req_err)}"}
        except Exception as e:
            print(f"ProcessApiService ({operation_name}): Erro inesperado: {e}")
            return {"success": False, "message": f"Erro inesperado: {str(e)}"}

    def delete_process(self, user_id: str, process_id: str) -> Dict[str, Any]:
        operation_name = "remover processo"
        url = f"{API_GATEWAY_PROCESSES_BASE_URL}/users/{user_id}/processes/{process_id}"
        print(f"ProcessApiService ({operation_name}): Chamando URL: {url}")
        try:
            headers = self._get_auth_headers()
            headers["Content-Type"] = "application/json" 
            response = requests.delete(url, headers=headers, timeout=15)
            print(f"ProcessApiService ({operation_name}): Resposta bruta status: {response.status_code}, texto: {response.text}")
            response.raise_for_status()
            return response.json() 
        except requests.exceptions.HTTPError as http_err:
            return self._handle_api_error(http_err, operation_name)
        except requests.exceptions.RequestException as req_err:
            print(f"ProcessApiService ({operation_name}): Erro de requisição: {req_err}")
            return {"success": False, "message": f"Erro de comunicação: {str(req_err)}"}
        except Exception as e:
            print(f"ProcessApiService ({operation_name}): Erro inesperado: {e}")
            return {"success": False, "message": f"Erro inesperado: {str(e)}"}
