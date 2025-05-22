import json
import boto3
import hashlib
import hmac # Para hmac.compare_digest
import os
import datetime # Para tempo de expiração do token
import jwt # Precisa da biblioteca PyJWT (pip install PyJWT)

# Nome da tabela DynamoDB para utilizadores
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', "UsuariosAdvocacia")

# Chave secreta para assinar o JWT.
# IMPORTANTE: Em produção, configure isto como uma variável de ambiente segura na sua Lambda.
# Nunca codifique chaves secretas diretamente no código em produção.
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 't8!nZ@sW3$pLqE7yH*vG1xU(bK0jF^cR9dM2oI&fA6hP4)sV5%eC')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_MINUTES = 60 # Token expira em 60 minutos

dynamodb_client = boto3.client('dynamodb')

def verify_password(stored_password_full_hash, provided_password):
    """Verifica a senha fornecida contra o hash armazenado."""
    try:
        parts = stored_password_full_hash.split('$')
        if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
            print("Formato de hash armazenado inválido.")
            return False

        algorithm, iterations_str, salt_hex, stored_hash_hex = parts
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        stored_hash_bytes = bytes.fromhex(stored_hash_hex)

        derived_key = hashlib.pbkdf2_hmac(
            'sha256',
            provided_password.encode('utf-8'),
            salt,
            iterations,
            dklen=len(stored_hash_bytes)
        )
        return hmac.compare_digest(stored_hash_bytes, derived_key)
    except Exception as e:
        print(f"Erro durante a verificação da senha: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def generate_jwt_token(username, role):
    """Gera um token JWT."""
    payload = {
        'username': username,
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=JWT_EXPIRATION_MINUTES),
        'iat': datetime.datetime.utcnow() # Issued at
    }
    try:
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        print(f"Token JWT gerado para o utilizador {username}")
        return token
    except Exception as e:
        print(f"Erro ao gerar token JWT: {e}")
        return None

def lambda_handler(event, context):
    print(f"FUNÇÃO DE LOGIN INVOCADA.")
    print(f"EVENTO COMPLETO RECEBIDO: {json.dumps(event)}") 

    body_content = None
    try:
        print("Dentro do bloco try principal da função de login.")
        event_body_str = event.get('body')
        
        print(f"Tipo de event.get('body'): {type(event_body_str)}")
        print(f"Conteúdo de event.get('body'): {event_body_str}")

        if event_body_str is not None and isinstance(event_body_str, str):
            try:
                body_content = json.loads(event_body_str)
                print(f"Corpo (body) após json.loads de event['body']: {body_content}")
            except json.JSONDecodeError as json_err:
                print(f"Erro de decodificação JSON em event['body']: {json_err}")
                return {'statusCode': 400, 'headers': {'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'success': False, 'message': 'Formato do corpo da requisição JSON inválido.'})}
        elif isinstance(event, dict) and 'username' in event and 'password' in event: # Para testes diretos da Lambda
            body_content = event
            print(f"Usando o próprio 'event' como corpo (body) - comum em testes diretos: {body_content}")
        else:
            print("Corpo (body) da requisição está ausente ou em formato inesperado para login.")
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'success': False, 'message': 'Corpo da requisição de login ausente ou formato inválido.'})
            }

        if body_content is None:
            print("Falha ao determinar o conteúdo do corpo para login.")
            return {'statusCode': 400, 'headers': {'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'success': False, 'message': 'Não foi possível processar o corpo da requisição de login.'})}

        username_attempt = body_content.get('username')
        password_attempt = body_content.get('password')

        print(f"Tentativa de login para username: {username_attempt}, Senha fornecida (comprimento): {len(password_attempt) if password_attempt else 0}")

        if not username_attempt or not password_attempt:
            print("Nome de utilizador ou senha ausentes no corpo processado para login.")
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'success': False, 'message': 'Nome de utilizador e senha são obrigatórios para o login.'})
            }

        print(f"Buscando utilizador '{username_attempt}' no DynamoDB...")
        try:
            response = dynamodb_client.get_item(
                TableName=DYNAMODB_TABLE_NAME,
                Key={'username': {'S': username_attempt}}
            )
        except Exception as e_db_get:
            print(f"Erro ao buscar utilizador '{username_attempt}' no DynamoDB: {e_db_get}")
            import traceback
            print(traceback.format_exc())
            return {'statusCode': 500, 'headers': {'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'success': False, 'message': 'Erro ao consultar o banco de dados.'})}

        item = response.get('Item')
        if not item:
            print(f"Utilizador '{username_attempt}' não encontrado no DynamoDB.")
            return {'statusCode': 401, 'headers': {'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'success': False, 'message': 'Utilizador ou senha inválidos.'})}

        stored_password_full_hash = item.get('password_hash', {}).get('S')
        if not stored_password_full_hash:
            print(f"Hash de senha não encontrado no DynamoDB para o utilizador: {username_attempt}")
            return {'statusCode': 500, 'headers': {'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'success': False, 'message': 'Erro interno: Configuração de utilizador inválida.'})}
        
        user_role = item.get('role', {}).get('S', 'user') # Pega a role do utilizador

        print(f"Verificando senha para '{username_attempt}'...")
        if verify_password(stored_password_full_hash, password_attempt):
            # Geração do Token JWT
            token = generate_jwt_token(username_attempt, user_role)
            if not token:
                print(f"Falha ao gerar token JWT para '{username_attempt}'.")
                return {'statusCode': 500, 'headers': {'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'success': False, 'message': 'Erro interno ao gerar token de autenticação.'})}

            # Inclui o token na resposta user_data
            user_data_response = {
                'username': username_attempt,
                'role': user_role,
                'token': token  # <<< TOKEN ADICIONADO AQUI
            }
            print(f"Login bem-sucedido para '{username_attempt}'. Token incluído na resposta.")
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'success': True, 'message': 'Login bem-sucedido!', 'user_data': user_data_response})
            }
        else:
            print(f"Senha inválida para '{username_attempt}'.")
            return {'statusCode': 401, 'headers': {'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'success': False, 'message': 'Utilizador ou senha inválidos.'})}

    except Exception as e: 
        print(f"Erro geral e inesperado na função de login: {e}")
        import traceback
        print(traceback.format_exc())
        return {'statusCode': 500, 'headers': {'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'success': False, 'message': f'Erro interno do servidor durante o login.'})}
