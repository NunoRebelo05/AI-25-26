import heapq
from collections import deque
from Grafo import Grafo 

# --- CONFIGURAÇÃO DA HEURÍSTICA ---
# Velocidade média em cidade (mais realista que 80)
VELOCIDADE_MEDIA_CIDADE_KMH = 40.0 

def a_star_search(grafo: Grafo, inicio: str, objetivo: str, 
                  cost_type: str = 'distancia', use_heuristic: bool = True):
    """
    Implementação do algoritmo A* com Heurística Dinâmica.
    """
    
    g_costs = {no: float('inf') for no in grafo.nos}
    g_costs[inicio] = 0
    
    # --- CÁLCULO DO FATOR DE TRÂNSITO GLOBAL ---
    # Calcula a média de trânsito atual na cidade para ajustar a heurística.
    # Isto torna o A* "consciente" do estado geral da rede.
    fator_transito = 1.0
    if cost_type == 'tempo' and grafo.condicoes_transito:
        soma_transito = sum(grafo.condicoes_transito.values())
        fator_transito = soma_transito / len(grafo.condicoes_transito)
        # (Opcional) Forçar um mínimo de 1.0
        fator_transito = max(1.0, fator_transito)
    # -------------------------------------------
    
    def heuristic(no_atual):
        if not use_heuristic:
            return 0 
            
        # Distância em linha reta (km)
        h_dist = grafo.get_distancia_heuristica(no_atual, objetivo)
        
        if cost_type == 'distancia':
            # Tie-breaker simples
            return h_dist * 1.001 
        else: # cost_type == 'tempo'
            # 1. Converter distância em tempo base (usando velocidade realista)
            h_tempo_horas = h_dist / VELOCIDADE_MEDIA_CIDADE_KMH
            h_tempo_min = h_tempo_horas * 60
            
            # 2. Aplicar o Fator de Trânsito Global
            # Se a cidade está lenta, a estimativa de tempo aumenta
            h_final = h_tempo_min * fator_transito
            
            return h_final * 1.001 # Tie-breaker
            
    frontier = [(heuristic(inicio), 0, inicio, [inicio])]
    heapq.heapify(frontier)
    
    # Dicionário para rastrear o melhor custo encontrado para um nó
    visited_costs = {inicio: 0}

    while frontier:
        f_cost_atual, g_cost_atual, no_atual, caminho = heapq.heappop(frontier)
        
        if no_atual in visited_costs and g_cost_atual > visited_costs[no_atual]:
            continue
            
        if no_atual == objetivo:
            return caminho, g_cost_atual

        for vizinho in grafo.get_vizinhos(no_atual):
            dist, tempo = grafo.get_custo_aresta(no_atual, vizinho)
            custo_aresta = dist if cost_type == 'distancia' else tempo
            
            novo_g_cost = g_cost_atual + custo_aresta
            
            if vizinho not in visited_costs or novo_g_cost < visited_costs[vizinho]:
                visited_costs[vizinho] = novo_g_cost
                g_costs[vizinho] = novo_g_cost
                
                h_val = heuristic(vizinho)
                novo_f_cost = novo_g_cost + h_val
                
                heapq.heappush(frontier, (novo_f_cost, novo_g_cost, vizinho, caminho + [vizinho]))

    return None, float('inf')


def greedy_search(grafo: Grafo, inicio: str, objetivo: str, 
                  cost_type: str = 'distancia'):
    """
    Implementação do algoritmo Guloso.
    (Mantemos a heurística simples aqui para destacar a superioridade do A*)
    """
    def heuristic(no_atual):
        h_dist = grafo.get_distancia_heuristica(no_atual, objetivo)
        if cost_type == 'distancia':
            return h_dist
        else:
            # Gulosa usa a estimativa simples sem considerar trânsito
            return (h_dist / VELOCIDADE_MEDIA_CIDADE_KMH) * 60
            
    frontier = [(heuristic(inicio), inicio, [inicio])]
    heapq.heapify(frontier)
    visited = set()

    while frontier:
        h_val, no_atual, caminho = heapq.heappop(frontier)
        
        if no_atual in visited:
            continue
            
        if no_atual == objetivo:
            custo_real = 0.0
            for i in range(len(caminho) - 1):
                d, t = grafo.get_custo_aresta(caminho[i], caminho[i+1])
                custo_real += d if cost_type == 'distancia' else t
            return caminho, custo_real

        visited.add(no_atual)

        for vizinho in grafo.get_vizinhos(no_atual):
            if vizinho not in visited:
                h_new = heuristic(vizinho)
                heapq.heappush(frontier, (h_new, vizinho, caminho + [vizinho]))

    return None, float('inf')


def dfs_search(grafo: Grafo, inicio: str, objetivo: str, cost_type: str = 'tempo'):
    """
    Implementação do algoritmo DFS.
    """
    frontier = [(inicio, [inicio], 0.0)]
    visited = set()

    while frontier:
        no_atual, caminho, custo_atual = frontier.pop()
        
        if no_atual == objetivo:
            return caminho, custo_atual
        
        if no_atual not in visited:
            visited.add(no_atual)
            vizinhos = grafo.get_vizinhos(no_atual)
            for vizinho in vizinhos:
                if vizinho not in visited:
                    d, t = grafo.get_custo_aresta(no_atual, vizinho)
                    c_aresta = d if cost_type == 'distancia' else t
                    frontier.append((vizinho, caminho + [vizinho], custo_atual + c_aresta))

    return None, float('inf')


def bfs_search(grafo: Grafo, inicio: str, objetivo: str, cost_type: str = 'tempo'):
    """
    Implementação do algoritmo BFS.
    """
    frontier = deque([(inicio, [inicio], 0.0)])
    visited = {inicio}

    while frontier:
        no_atual, caminho, custo_atual = frontier.popleft()
        
        if no_atual == objetivo:
            return caminho, custo_atual

        for vizinho in grafo.get_vizinhos(no_atual):
            if vizinho not in visited:
                visited.add(vizinho)
                d, t = grafo.get_custo_aresta(no_atual, vizinho)
                c_aresta = d if cost_type == 'distancia' else t
                frontier.append((vizinho, caminho + [vizinho], custo_atual + c_aresta))

    return None, float('inf')