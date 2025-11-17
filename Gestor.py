from enum import Enum, auto
from datetime import datetime, timedelta

from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao, EstadoVeiculo
from Pedido import Pedido, PrioridadePedido

# Importar TODOS os algoritmos de procura
from AlgoritmosDeProcura import a_star_search, greedy_search, dfs_search, bfs_search

# Estes pesos (W) definem a estratégia da empresa.
PESOS_ESTRATEGIA = {
    'W_TEMPO_ESPERA': 1.5,
    'W_CUSTO_OPER': 1.0,
    'W_KM_SEM_PAX': 0.8,
    'PENALIZACAO_AMBIENTAL': 50.0,
    'PENALIZACAO_PRIORIDADE': 3.0
}

# Enum de Estratégias
class EstrategiaProcura(Enum):
    A_STAR = auto()   # Informada, Ótima
    GULOSA = auto()   # Informada, Não-Ótima
    UCS = auto()      # Não-Informada, Ótima
    DFS = auto()      # Não-Informada, Não-Ótima
    BFS = auto()      # Não-Informada, Não-Ótima (em custo)

class GestorDeFrota:
    
    def __init__(self, grafo: Grafo):
        self.grafo = grafo
        self.frota = {} 
        self.pedidos_pendentes = []
        self.estrategia_procura = EstrategiaProcura.A_STAR

    def definir_estrategia(self, estrategia: EstrategiaProcura):
        """Permite ao 'main' mudar a estratégia de procura."""
        print(f"\n--- ⚠️  Estratégia de Procura alterada para: {estrategia.name} ---")
        self.estrategia_procura = estrategia

    def add_taxi(self, taxi: Taxi):
        self.frota[taxi.id_veiculo] = taxi
        print(f"INFO: Taxi {taxi.id_veiculo} adicionado à frota.")

    def decidir_alocacao(self, pedido: Pedido):
        melhor_taxi, melhor_custo, detalhes_caminho = self._encontrar_melhor_taxi(pedido)
        return melhor_taxi, melhor_custo, detalhes_caminho

    def _encontrar_melhor_taxi(self, pedido: Pedido) -> (Taxi, float, tuple):
        melhor_custo_global = float('inf')
        melhor_taxi_escolhido = None
        melhores_caminhos = None
        
        for id_taxi, taxi in self.frota.items():
            if taxi.estado != EstadoVeiculo.LIVRE:
                continue
            if taxi.capacidade_passageiros < pedido.num_passageiros:
                continue
                
            custo, caminhos = self._calcular_custo_alocacao(taxi, pedido)
            
            if custo < melhor_custo_global:
                melhor_custo_global = custo
                melhor_taxi_escolhido = taxi
                melhores_caminhos = caminhos
                
        return melhor_taxi_escolhido, melhor_custo_global, melhores_caminhos

    def _calcular_custo_alocacao(self, taxi: Taxi, pedido: Pedido) -> (float, tuple):
        """
        A "Função de Custo" da Tarefa 1.
        """
        
        # --- PASSO 1: Calcular os caminhos (LÓGICA ATUALIZADA) ---
        TIPO_OTIMIZACAO = 'tempo'
        
        if self.estrategia_procura == EstrategiaProcura.A_STAR:
            caminho_pickup, tempo_espera = a_star_search(
                self.grafo, taxi.localizacao_atual, pedido.origem, TIPO_OTIMIZACAO, use_heuristic=True
            )
            caminho_viagem, tempo_viagem = a_star_search(
                self.grafo, pedido.origem, pedido.destino, TIPO_OTIMIZACAO, use_heuristic=True
            )
        
        elif self.estrategia_procura == EstrategiaProcura.UCS:
            caminho_pickup, tempo_espera = a_star_search(
                self.grafo, taxi.localizacao_atual, pedido.origem, TIPO_OTIMIZACAO, use_heuristic=False
            )
            caminho_viagem, tempo_viagem = a_star_search(
                self.grafo, pedido.origem, pedido.destino, TIPO_OTIMIZACAO, use_heuristic=False
            )
            
        elif self.estrategia_procura == EstrategiaProcura.GULOSA:
            caminho_pickup, tempo_espera = greedy_search(
                self.grafo, taxi.localizacao_atual, pedido.origem, TIPO_OTIMIZACAO
            )
            caminho_viagem, tempo_viagem = greedy_search(
                self.grafo, pedido.origem, pedido.destino, TIPO_OTIMIZACAO
            )
            
        elif self.estrategia_procura == EstrategiaProcura.DFS:
            caminho_pickup, tempo_espera = dfs_search(
                self.grafo, taxi.localizacao_atual, pedido.origem, TIPO_OTIMIZACAO
            )
            caminho_viagem, tempo_viagem = dfs_search(
                self.grafo, pedido.origem, pedido.destino, TIPO_OTIMIZACAO
            )
        
        # --- NOVO BLOCO PARA BFS ---
        elif self.estrategia_procura == EstrategiaProcura.BFS:
            caminho_pickup, tempo_espera = bfs_search(
                self.grafo, taxi.localizacao_atual, pedido.origem, TIPO_OTIMIZACAO
            )
            caminho_viagem, tempo_viagem = bfs_search(
                self.grafo, pedido.origem, pedido.destino, TIPO_OTIMIZACAO
            )
        # --- FIM DA LÓGICA DE DECISÃO ---
            
        if not caminho_pickup or not caminho_viagem:
            return float('inf'), None # Não há caminho

        # --- (O resto da função continua igual) ---
        dist_pickup = self._get_dist_caminho(caminho_pickup)
        dist_viagem = self._get_dist_caminho(caminho_viagem)
        dist_total = dist_pickup + dist_viagem
        
        if not taxi.pode_aceitar_pedido(pedido.num_passageiros, dist_total):
            return float('inf'), None 

        C_espera = tempo_espera
        C_oper = dist_total * taxi.custo_por_km
        C_vazio = dist_pickup * taxi.custo_por_km
        
        C_amb = 0.0
        if pedido.pref_ambiental and taxi.tipo == TipoMotorizacao.COMBUSTAO:
            C_amb = PESOS_ESTRATEGIA['PENALIZACAO_AMBIENTAL']
            
        W_espera = PESOS_ESTRATEGIA['W_TEMPO_ESPERA']
        if pedido.prioridade == PrioridadePedido.URGENTE:
            W_espera *= PESOS_ESTRATEGIA['PENALIZACAO_PRIORIDADE']
            
        custo_final = (
            (W_espera * C_espera) +
            (PESOS_ESTRATEGIA['W_CUSTO_OPER'] * C_oper) +
            (PESOS_ESTRATEGIA['W_KM_SEM_PAX'] * C_vazio) +
            C_amb
        )
        
        return custo_final, (caminho_pickup, caminho_viagem)

    # --- (Funções _get_dist_caminho e _get_tempo_caminho ficam iguais) ---
    def _get_dist_caminho(self, caminho: list) -> float:
        dist_total = 0.0
        for i in range(len(caminho) - 1):
            dist, _ = self.grafo.get_custo_aresta(caminho[i], caminho[i+1])
            dist_total += dist
        return dist_total

    def _get_tempo_caminho(self, caminho: list) -> float:
        tempo_total = 0.0
        for i in range(len(caminho) - 1):
            _, tempo = self.grafo.get_custo_aresta(caminho[i], caminho[i+1])
            tempo_total += tempo
        return tempo_total
