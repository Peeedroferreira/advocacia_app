import boto3
from botocore.exceptions import ClientError
from decimal import Decimal 
import json
from typing import Optional, List, Dict, Any # Adicionado Optional, List, Dict, Any para type hinting

# Configuração do DynamoDB
DYNAMODB_CLIENTS_TABLE_NAME = "ClientesAdvocacia" 
DYNAMODB_REGION = "sa-east-1" 

USER_ID_NOME_COMPLETO_INDEX = "UserIdNomeCompletoIndex"


class DynamoDBClientHandler:
    def __init__(self, region_name=DYNAMODB_REGION):
        try:
            self.dynamodb_client = boto3.client('dynamodb', region_name=region_name)
            self.dynamodb_resource = boto3.resource('dynamodb', region_name=region_name) # Adicionado resource para Table API
            self.clients_table = self.dynamodb_resource.Table(DYNAMODB_CLIENTS_TABLE_NAME)
            print(f"DynamoDBClientHandler inicializado para a tabela: {DYNAMODB_CLIENTS_TABLE_NAME} na região {region_name}")
        except Exception as e:
            print(f"Erro ao inicializar o cliente/recurso DynamoDB: {e}")
            self.dynamodb_client = None
            self.clients_table = None

    def _serialize_item(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        # Remove chaves com valores vazios para não armazená-las no DynamoDB,
        # a menos que sejam explicitamente permitidas (ex: booleano False).
        # Para strings vazias, geralmente é melhor não as armazenar se não forem significativas.
        serialized = {}
        for k, v in client_data.items():
            if isinstance(v, float): # Converte float para Decimal
                serialized[k] = Decimal(str(v))
            elif v is not None and v != "": # Não adiciona None ou strings vazias
                serialized[k] = v
            elif isinstance(v, bool): # Mantém booleanos
                 serialized[k] = v
        return serialized


    def add_client(self, user_id: str, client_data: Dict[str, Any]) -> bool:
        if not self.clients_table:
            print("Erro: Tabela de clientes não inicializada.")
            return False
        
        client_cpf = client_data.get('client_cpf')
        if not user_id or not client_cpf:
            print("Erro: user_id e client_cpf são obrigatórios para adicionar cliente.")
            return False

        item_to_add = self._serialize_item(client_data.copy())
        item_to_add['user_id'] = user_id
        # client_cpf já está em item_to_add através de client_data

        try:
            print(f"Adicionando cliente ao DynamoDB: {item_to_add}")
            self.clients_table.put_item(
                Item=item_to_add,
                # Garante que não sobrescreve um item existente com a mesma chave composta
                ConditionExpression="attribute_not_exists(user_id) AND attribute_not_exists(client_cpf)"
            )
            print("Cliente adicionado com sucesso.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                print(f"Erro: Cliente com CPF {client_cpf} já existe para este usuário ({user_id}).")
            else:
                print(f"Erro do Boto3 ao adicionar cliente: {e.response['Error']['Message']}")
        except Exception as e:
            print(f"Erro inesperado ao adicionar cliente: {e}")
        return False

    def get_client(self, user_id: str, client_cpf: str) -> Optional[Dict[str, Any]]: # <--- TIPO DE RETORNO CORRIGIDO
        if not self.clients_table: return None
        try:
            response = self.clients_table.get_item(
                Key={'user_id': user_id, 'client_cpf': client_cpf}
            )
            item = response.get('Item')
            if item:
                # DynamoDB retorna números como Decimal, converter de volta para float/int se necessário para a aplicação
                # ou deixar como Decimal se a aplicação souber lidar.
                # Para este exemplo, vamos retornar o item como está (com Decimals).
                pass
            return item
        except ClientError as e:
            print(f"Erro do Boto3 ao buscar cliente: {e.response['Error']['Message']}")
        except Exception as e:
            print(f"Erro inesperado ao buscar cliente: {e}")
        return None

    def get_clients_by_user(self, user_id: str) -> List[Dict[str, Any]]: # <--- TIPO DE RETORNO CORRIGIDO
        if not self.clients_table: return []
        try:
            response = self.clients_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"Erro do Boto3 ao listar clientes por usuário: {e.response['Error']['Message']}")
        except Exception as e:
            print(f"Erro inesperado ao listar clientes: {e}")
        return []

    def update_client(self, user_id: str, client_cpf: str, update_data: Dict[str, Any]) -> bool:
        if not self.clients_table: return False
        
        update_data_copy = self._serialize_item(update_data.copy())
        update_data_copy.pop('user_id', None)
        update_data_copy.pop('client_cpf', None)

        if not update_data_copy:
            print("Nenhum dado válido para atualizar após serialização.")
            return False

        update_expression_parts = []
        expression_attribute_values = {}
        expression_attribute_names = {} 
        
        i = 0
        for key, value in update_data_copy.items():
            attr_name_placeholder = f"#attr{i}"
            attr_value_placeholder = f":val{i}"
            
            update_expression_parts.append(f"{attr_name_placeholder} = {attr_value_placeholder}")
            expression_attribute_names[attr_name_placeholder] = key
            expression_attribute_values[attr_value_placeholder] = value
            i += 1
        
        if not update_expression_parts:
            print("Nenhuma expressão de atualização válida gerada.")
            return False

        update_expression = "SET " + ", ".join(update_expression_parts)

        try:
            print(f"Atualizando cliente {client_cpf} para usuário {user_id}")
            # print(f"UpdateExpression: {update_expression}")
            # print(f"ExpressionAttributeNames: {expression_attribute_names}")
            # print(f"ExpressionAttributeValues: {expression_attribute_values}")

            self.clients_table.update_item(
                Key={'user_id': user_id, 'client_cpf': client_cpf},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ConditionExpression="attribute_exists(user_id) AND attribute_exists(client_cpf)",
                ReturnValues="NONE" 
            )
            print("Cliente atualizado com sucesso.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                print(f"Erro: Cliente com CPF {client_cpf} não encontrado para este usuário ({user_id}) para atualização.")
            else:
                print(f"Erro do Boto3 ao atualizar cliente: {e.response['Error']['Message']}")
        except Exception as e:
            print(f"Erro inesperado ao atualizar cliente: {e}")
        return False

    def delete_client(self, user_id: str, client_cpf: str) -> bool:
        if not self.clients_table: return False
        try:
            self.clients_table.delete_item(
                Key={'user_id': user_id, 'client_cpf': client_cpf},
                ConditionExpression="attribute_exists(user_id) AND attribute_exists(client_cpf)"
            )
            print(f"Cliente com CPF {client_cpf} removido para o usuário {user_id}.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                print(f"Erro: Cliente com CPF {client_cpf} não encontrado para este usuário ({user_id}) para remoção.")
            else:
                print(f"Erro do Boto3 ao remover cliente: {e.response['Error']['Message']}")
        except Exception as e:
            print(f"Erro inesperado ao remover cliente: {e}")
        return False

if __name__ == '__main__':
    handler = DynamoDBClientHandler()
    if handler.clients_table:
        test_user_id = "test_advogado_pyside" # Use um ID de usuário diferente para testes
        
        # Limpar dados de teste anteriores para este user_id (opcional)
        # existing_clients = handler.get_clients_by_user(test_user_id)
        # for client in existing_clients:
        #     handler.delete_client(test_user_id, client['client_cpf'])
        # print(f"Dados de teste anteriores para {test_user_id} limpos.")

        client_data_1 = {
            "client_cpf": "11122233301", "nome_completo": "Ana Paula PySide",
            "nacionalidade": "Brasileira", "estado_civil": "Solteira", "profissao": "Desenvolvedora",
            "data_nascimento": "1995-07-20", "rg": "10203040 SSP/BA",
            "telefone_celular": "(71) 99999-0001", "email": "ana.pyside@example.com",
            "filhos_nomes": ["Hugo", "Maria Clara"]
        }
        if handler.add_client(test_user_id, client_data_1):
            print(f"Cliente {client_data_1['nome_completo']} adicionado.")
        else:
            print(f"Falha ao adicionar cliente {client_data_1['nome_completo']}.")


        client_data_2 = {
            "client_cpf": "77788899901", "nome_completo": "Bruno Costa PySide",
            "telefone_celular": "(11) 98888-0002", "email": "bruno.costa.ps@example.com",
        }
        if handler.add_client(test_user_id, client_data_2):
            print(f"Cliente {client_data_2['nome_completo']} adicionado.")
        else:
            print(f"Falha ao adicionar cliente {client_data_2['nome_completo']}.")


        print(f"\nClientes de {test_user_id}:")
        clients = handler.get_clients_by_user(test_user_id)
        for client in clients:
            print(f"  CPF: {client.get('client_cpf')}, Nome: {client.get('nome_completo')}, Filhos: {client.get('filhos_nomes')}")

        specific_client = handler.get_client(test_user_id, "11122233301")
        if specific_client:
            print(f"\nCliente específico (11122233301): {specific_client.get('nome_completo')}")

        update_info = {"profissao": "Arquiteta de Software", "email": "ana.paula.pyside.updated@example.com"}
        if handler.update_client(test_user_id, "11122233301", update_info):
             print(f"\nCliente 11122233301 atualizado.")
             updated_client = handler.get_client(test_user_id, "11122233301")
             if updated_client: print(f"Dados atualizados: Profissão - {updated_client.get('profissao')}, Email - {updated_client.get('email')}")
        else:
            print(f"\nFalha ao atualizar cliente 11122233301.")
        
    else:
        print("Falha ao inicializar o DynamoDBClientHandler. Verifique as configurações e credenciais AWS.")

