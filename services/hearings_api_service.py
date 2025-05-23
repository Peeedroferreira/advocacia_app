# advocacia_app/services/hearings_api_service.py

import requests
import json
from typing import Optional, List, Dict, Any

# A URL base da API Gateway deve ser centralizada em constants.py
# Por enquanto, vamos definir aqui, mas o ideal é importar de config.constants
# Supondo que os endpoints de audiências estarão sob a mesma API Gateway
API_GATEWAY_BASE_URL = "https://p55kko7yc6.execute-api.sa-east-1.amazonaws.com/dev" 

class HearingsApiService:
    def __init__(self, auth_token: Optional[str] = None):
        self.auth_token = auth_token
        self.base_url = API_GATEWAY_BASE_URL # Poderia ser injetado ou importado
        print(f"HearingsApiService: Instanciado com token: {'Sim' if auth_token else 'Não'}")

    def _get_auth_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _handle_api_error(self, http_err: requests.exceptions.HTTPError, operation_name: str) -> Dict[str, Any]:
        """Lida com erros HTTP e tenta parsear a resposta da Lambda."""
        print(f"HearingsApiService: Erro HTTP em '{operation_name}': Status {http_err.response.status_code} - Resposta: {http_err.response.text}")
        try:
            error_body = http_err.response.json()
            # Se o corpo do erro for uma string JSON (comum com proxy Lambda), parseie-o
            if isinstance(error_body, str):
                try:
                    error_body = json.loads(error_body)
                except json.JSONDecodeError:
                    # Mantém como string se não for JSON válido, mas loga
                    print(f"HearingsApiService: Corpo do erro HTTP não era JSON decodificável: {error_body}")
            return error_body # Pode ser um dict com 'success': False, 'message': '...' ou a resposta direta do API Gateway
        except json.JSONDecodeError: # Se a resposta de erro em si não for JSON
            return {"success": False, "message": f"Erro HTTP {http_err.response.status_code} em '{operation_name}'. Resposta não JSON: {http_err.response.text}"}
        except Exception as e: # Outro erro ao processar a resposta de erro
            return {"success": False, "message": f"Erro HTTP {http_err.response.status_code} em '{operation_name}'. Erro ao processar resposta de erro: {str(e)}"}

    def _make_request(self, method: str, endpoint: str, operation_name: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Método genérico para fazer requisições."""
        url = f"{self.base_url}{endpoint}"
        print(f"HearingsApiService ({operation_name}): Chamando {method} URL: {url}")
        if params: print(f"HearingsApiService ({operation_name}): Params: {params}")
        if data: print(f"HearingsApiService ({operation_name}): Data: {json.dumps(data)}")

        try:
            response = requests.request(method, url, headers=self._get_auth_headers(), params=params, json=data, timeout=15)
            print(f"HearingsApiService ({operation_name}): Resposta bruta status: {response.status_code}, texto: {response.text[:500]}...") # Limita o log do texto
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            return self._handle_api_error(http_err, operation_name)
        except requests.exceptions.RequestException as req_err:
            print(f"HearingsApiService ({operation_name}): Erro de requisição: {req_err}")
            return {"success": False, "message": f"Erro de comunicação ao {operation_name}: {str(req_err)}"}
        except Exception as e: # Captura outros erros inesperados
            print(f"HearingsApiService ({operation_name}): Erro inesperado: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"Erro inesperado em {operation_name}: {str(e)}"}

    def add_hearing(self, user_id: str, hearing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Adiciona uma nova audiência."""
        endpoint = f"/users/{user_id}/hearings"
        return self._make_request("POST", endpoint, "adicionar audiência", data=hearing_data)

    def get_hearings_by_user(self, user_id: str, process_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Busca audiências por usuário, opcionalmente filtrando por ID do processo ou intervalo de datas."""
        endpoint = f"/users/{user_id}/hearings"
        params = {}
        if process_id:
            params['process_id'] = process_id
        if start_date:
            params['start_date'] = start_date # Formato esperado: YYYY-MM-DD
        if end_date:
            params['end_date'] = end_date   # Formato esperado: YYYY-MM-DD
        
        response = self._make_request("GET", endpoint, "buscar audiências", params=params)
        if "hearings" not in response: # Garante que a chave 'hearings' sempre exista
            response["hearings"] = []
        return response

    def get_hearing_details(self, user_id: str, hearing_id: str) -> Dict[str, Any]:
        """Busca detalhes de uma audiência específica."""
        endpoint = f"/users/{user_id}/hearings/{hearing_id}"
        return self._make_request("GET", endpoint, "buscar detalhes da audiência")

    def update_hearing(self, user_id: str, hearing_id: str, hearing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza uma audiência existente."""
        endpoint = f"/users/{user_id}/hearings/{hearing_id}"
        return self._make_request("PUT", endpoint, "atualizar audiência", data=hearing_data)

    def delete_hearing(self, user_id: str, hearing_id: str) -> Dict[str, Any]:
        """Remove uma audiência."""
        endpoint = f"/users/{user_id}/hearings/{hearing_id}"
        return self._make_request("DELETE", endpoint, "remover audiência")

if __name__ == '__main__':
    # Exemplo de uso (requer um token válido e API configurada para testes reais)
    print("--- Testando HearingsApiService (simulação) ---")
    # Para testes reais, você precisaria de um token de autenticação válido
    # test_auth_token = "seu_token_jwt_aqui" 
    # hearings_service = HearingsApiService(auth_token=test_auth_token)
    hearings_service = HearingsApiService(auth_token="dummy-token-if-needed") # Para testes sem chamadas reais

    test_user_id = "test_user_hearings"
    
    # Simular adição de audiência
    new_hearing_data = {
        "process_id": "processo_uuid_123",
        "data_hora": "2025-07-15T14:30:00", # Formato ISO 8601
        "local": "Fórum Central, Sala 101",
        "vara": "1ª Vara Cível",
        "tipo": "Instrução e Julgamento",
        "notas": "Levar todas as provas documentais."
    }
    # print(f"\nTentando adicionar audiência para {test_user_id}:")
    # add_response = hearings_service.add_hearing(test_user_id, new_hearing_data)
    # print(f"Resposta (Adicionar Audiência): {json.dumps(add_response, indent=2)}")

    # Simular busca de audiências
    # print(f"\nTentando buscar audiências para {test_user_id}:")
    # get_response = hearings_service.get_hearings_by_user(test_user_id, start_date="2025-07-01", end_date="2025-07-31")
    # print(f"Resposta (Buscar Audiências): {json.dumps(get_response, indent=2)}")

    print("\nLembre-se de que estes são testes simulados ou que requerem uma API funcional.")
    print("Descomente as chamadas e forneça um token válido para interagir com a API real.")
