import json
import os

class Config:
    """
    Gerenciador de configurações da aplicação (Singleton).
    
    Responsável por carregar, armazenar e fornecer acesso às configurações
    do sistema, permitindo o uso de um arquivo JSON externo ou valores padrão.
    """
    _instance = None

    def __new__(cls):
        """
        Implementação do padrão Singleton para garantir apenas uma instância de configuração.
        """
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance.dados = {}
            cls._instance.carregar()
        return cls._instance

    def carregar(self, caminho="config.json"):
        """
        Carrega as configurações a partir de um arquivo JSON.
        
        Se o arquivo não for encontrado ou ocorrer erro na leitura,
        carrega as configurações padrão.
        
        Args:
            caminho (str): Caminho para o arquivo de configuração.
        """
        if not os.path.exists(caminho):
            print(f"AVISO: Ficheiro de configuração '{caminho}' não encontrado. A usar predefinições.")
            self.dados = self._get_defaults()
            return

        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                self.dados = json.load(f)
            print(f"INFO: Configuração carregada de '{caminho}'.")
        except Exception as e:
            print(f"ERRO: Falha ao ler config: {e}. A usar predefinições.")
            self.dados = self._get_defaults()

    def get(self, chave, default=None):
        """
        Acede a valores de configuração usando notação de ponto para chaves aninhadas.
        
        Exemplo: cfg.get('simulacao.duracao_horas')
        
        Args:
            chave (str): Chave de acesso (ex: 'categoria.subcategoria.item').
            default (any, optional): Valor a retornar se a chave não existir.
            
        Returns:
            any: O valor da configuração ou o valor default.
        """
        chaves = chave.split('.')
        valor = self.dados
        try:
            for k in chaves:
                valor = valor[k]
            return valor
        except (KeyError, TypeError):
            return default

    def _get_defaults(self):
        """
        Retorna o dicionário com as configurações padrão do sistema.
        
        Returns:
            dict: Configurações padrão.
        """
        return {
            "simulacao": {
                "duracao_horas": 12,
                "prob_pedido": 0.15,
                "horas_ponta": [8, 9, 17, 18],
                "velocidade_media_cidade_kmh": 40.0,
                "multiplicador_transito_ponta": 1.75,
                "limiar_recarga_eletrico": 0.25,
                "margem_seguranca_bateria": 1.2
            },
            "frota": {
                "num_eletricos": 2,
                "num_combustao": 2,
                "specs_eletrico": {"capacidade": 4, "custo_km": 0.15, "autonomia": 250.0, "tempo_recarga_min": 30},
                "specs_combustao": {"capacidade": 4, "custo_km": 0.25, "autonomia": 600.0, "tempo_abastecimento_min": 5}
            },
            "pesos_estrategia": {
                "W_TEMPO_ESPERA": 1.5,
                "W_CUSTO_OPER": 1.0,
                "W_KM_SEM_PAX": 0.8,
                "PENALIZACAO_AMBIENTAL": 50.0,
                "PENALIZACAO_PRIORIDADE": 3.0
            },
            "pedidos_estaticos": {
                "usar_estaticos": False,
                "lista": []
            }
        }

# Instância global para acesso fácil em toda a aplicação
cfg = Config()
