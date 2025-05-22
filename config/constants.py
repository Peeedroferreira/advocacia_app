# advocacia_app/config/constants.py

# --- Versão da Aplicação ---
# Esta é a versão atual da sua aplicação cliente.
# Você DEVE ATUALIZAR esta string a cada nova versão que você compila e distribui.
CURRENT_APPLICATION_VERSION = "1.0.0"

# --- Configurações de Atualização ---
# URL RAW do seu ficheiro latest_version.json no GitHub.
# SUBSTITUA 'SEU_USUARIO_GITHUB' e 'SEU_REPOSITORIO' pelos seus valores reais.
# Exemplo: "https://raw.githubusercontent.com/seu_usuario/seu_projeto_advocacia/main/updates/latest_version.json"
VERSION_INFO_URL = "https://raw.githubusercontent.com/Peeedroferreira/EasyLaw/refs/heads/main/updates/latest_version.json"

# --- Configurações do Ficheiro de Configuração Local (app_config.ini) ---
CONFIG_FILE_NAME = "app_config.ini"        # Nome do ficheiro de configuração local
CONFIG_SECTION_UPDATE = "UpdateSettings"   # Nome da seção para configurações de atualização
CONFIG_KEY_LAST_CHECK = "last_update_check_timestamp" # Chave para o timestamp da última verificação

# --- Outras Constantes (Exemplos) ---
# COMPANY_NAME = "Meu Escritório de Advocacia Digital"
# CONTACT_EMAIL = "suporte@meuescritorio.com"

# Adicione quaisquer outras constantes globais que sua aplicação possa precisar.
