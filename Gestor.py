from enum import Enum, auto
from datetime import datetime, timedelta

from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao, EstadoVeiculo
from Pedido import Pedido, PrioridadePedido
from Config import cfg

from AlgoritmosDeProcura import a_star_search, greedy_search, dfs_search, bfs_search

class EstrategiaProcura(Enum):
    A_STAR = auto()
    GULOSA = auto()
    UCS = auto()
    DFS = auto()
    BFS = auto()

class GestorDeFrota:
    def __init__(self, grafo: Grafo):
        self.grafo = grafo
        self.frota = {} 
        self.pedidos_pendentes = []
        self.estrategia_procura = EstrategiaProcura.A_STAR

    def definir_estrategia(self, estrategia: EstrategiaProcura):
        print(f"\n--- Estratégia de Procura alterada para: {estrategia.name} ---")
        self.estrategia_procura = estrategia

    def add_taxi(self, taxi: Taxi):
        self.frota[taxi.id_veiculo] = taxi

    def get_caminho(self, origem: str, destino: str) -> (list, float):
        """Calcula o caminho entre dois pontos usando a estratégia definida."""
        tipo_otimizacao = 'tempo'
        
        if self.estrategia_procura == EstrategiaProcura.A_STAR:
            return a_star_search(self.grafo, origem, destino, tipo_otimizacao, use_heuristic=True)
        elif self.estrategia_procura == EstrategiaProcura.UCS:
            return a_star_search(self.grafo, origem, destino, tipo_otimizacao, use_heuristic=False)
        elif self.estrategia_procura == EstrategiaProcura.GULOSA:
            return greedy_search(self.grafo, origem, destino, tipo_otimizacao)
        elif self.estrategia_procura == EstrategiaProcura.DFS:
            return dfs_search(self.grafo, origem, destino, tipo_otimizacao)
        elif self.estrategia_procura == EstrategiaProcura.BFS:
            return bfs_search(self.grafo, origem, destino, tipo_otimizacao)
            
        return None, float('inf')

    def decidir_alocacao(self, pedido: Pedido):
        melhor_taxi, melhor_custo, detalhes_caminho = self._encontrar_melhor_taxi(pedido)
        return melhor_taxi, melhor_custo, detalhes_caminho

    def _encontrar_melhor_taxi(self, pedido: Pedido) -> (Taxi, float, tuple):
        melhor_custo_global = float('inf')
        melhor_taxi_escolhido = None
        melhores_caminhos = None
        
        for id_taxi, taxi in self.frota.items():
            if taxi.estado != EstadoVeiculo.LIVRE: continue
            if taxi.capacidade_passageiros < pedido.num_passageiros: continue
                
            custo, caminhos = self._calcular_custo_alocacao(taxi, pedido)
            
            if custo < melhor_custo_global:
                melhor_custo_global = custo
                melhor_taxi_escolhido = taxi
                melhores_caminhos = caminhos
                
        return melhor_taxi_escolhido, melhor_custo_global, melhores_caminhos

    def _calcular_custo_alocacao(self, taxi: Taxi, pedido: Pedido) -> (float, tuple):
        caminho_pickup, tempo_espera = self.get_caminho(taxi.localizacao_atual, pedido.origem)
        caminho_viagem, tempo_viagem = self.get_caminho(pedido.origem, pedido.destino)
            
        if not caminho_pickup or not caminho_viagem:
            return float('inf'), None

        dist_pickup = self._get_dist_caminho(caminho_pickup)
        dist_viagem = self._get_dist_caminho(caminho_viagem)
        dist_total_servico = dist_pickup + dist_viagem
        
        # --- REGRA DE SEGURANÇA ---
        margem_seguranca = cfg.get('simulacao.margem_seguranca_bateria', 1.2)
        distancia_necessaria = dist_total_servico * margem_seguranca
        
        if not taxi.pode_aceitar_pedido(pedido.num_passageiros, distancia_necessaria):
            return float('inf'), None 
        # --------------------------------

        # Cálculo do Custo (Score)
        C_espera = tempo_espera
        C_oper = dist_total_servico * taxi.custo_por_km
        C_vazio = dist_pickup * taxi.custo_por_km
        
        C_amb = 0.0
        if pedido.pref_ambiental and taxi.tipo == TipoMotorizacao.COMBUSTAO:
            C_amb = cfg.get('pesos_estrategia.PENALIZACAO_AMBIENTAL')
            
        W_espera = cfg.get('pesos_estrategia.W_TEMPO_ESPERA')
        if pedido.prioridade == PrioridadePedido.URGENTE:
            W_espera *= cfg.get('pesos_estrategia.PENALIZACAO_PRIORIDADE')
            
        custo_final = (
            (W_espera * C_espera) +
            (cfg.get('pesos_estrategia.W_CUSTO_OPER') * C_oper) +
            (cfg.get('pesos_estrategia.W_KM_SEM_PAX') * C_vazio) +
            C_amb
        )
        
        return custo_final, (caminho_pickup, caminho_viagem)

    def _get_dist_caminho(self, caminho: list) -> float:
        dist_total = 0.0
        if not caminho: return 0.0
        for i in range(len(caminho) - 1):
            dist, _ = self.grafo.get_custo_aresta(caminho[i], caminho[i+1])
            if dist != float('inf'):
                dist_total += dist
        return dist_total

    def _get_tempo_caminho(self, caminho: list) -> float:
        tempo_total = 0.0
        if not caminho: return 0.0
        for i in range(len(caminho) - 1):
            _, tempo = self.grafo.get_custo_aresta(caminho[i], caminho[i+1])
            if tempo != float('inf'):
                tempo_total += tempo
        return tempo_total