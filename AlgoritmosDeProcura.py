import heapq
from collections import deque
from Grafo import Grafo 
from Config import cfg

# Cache para parâmetros da heurística
_heuristic_cache = {
    'graph_id': None,
    'max_speed': 1.0,
    'min_dist_ratio': 1.0
}

def _update_heuristic_cache(grafo: Grafo):
    # Identificador simples para o grafo (usando id do objeto)
    graph_id = id(grafo)
    
    if _heuristic_cache['graph_id'] == graph_id:
        return _heuristic_cache['max_speed'], _heuristic_cache['min_dist_ratio']
        
    # --- CÁLCULO DA VELOCIDADE MÁXIMA E FATOR DE CORREÇÃO ---
    max_speed_kmh = 1.0
    min_dist_ratio = 1.0
    
    for u, vizinhos in grafo.arestas.items():
        for v, dados in vizinhos.items():
            dist_aresta = dados['distancia_km']
            tempo_min = dados['tempo_base_min'] / 60.0 # horas
            
            if tempo_min > 0:
                speed = dist_aresta / tempo_min
                if speed > max_speed_kmh:
                    max_speed_kmh = speed
            
            dist_hav = grafo.get_distancia_heuristica(u, v)
            if dist_hav > 0:
                ratio = dist_aresta / dist_hav
                if ratio < min_dist_ratio:
                    min_dist_ratio = ratio

    max_speed_kmh *= 1.05 # Margem de segurança
    
    _heuristic_cache['graph_id'] = graph_id
    _heuristic_cache['max_speed'] = max_speed_kmh
    _heuristic_cache['min_dist_ratio'] = min_dist_ratio
    
    return max_speed_kmh, min_dist_ratio

def a_star_search(grafo: Grafo, inicio: str, objetivo: str, 
                  cost_type: str = 'distancia', use_heuristic: bool = True):
    """
    Implementação do algoritmo A* com Heurística Otimizada.
    """
    
    g_costs = {no: float('inf') for no in grafo.nos}
    g_costs[inicio] = 0
    
    max_speed_kmh, min_dist_ratio = _update_heuristic_cache(grafo)

    def heuristic(no_atual):
        if not use_heuristic:
            return 0 
            
        # Distância em linha reta (km)
        h_dist_raw = grafo.get_distancia_heuristica(no_atual, objetivo)
        
        # Aplicar correção geométrica para garantir h(n) <= custo_real
        h_dist = h_dist_raw * min_dist_ratio
        
        if cost_type == 'distancia':
            return h_dist
        else: # cost_type == 'tempo'
            # Usamos a velocidade máxima para estimar o tempo mínimo
            h_tempo_horas = h_dist / max_speed_kmh
            h_tempo_min = h_tempo_horas * 60
            
            return h_tempo_min
            
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
    velocidade_media = cfg.get('simulacao.velocidade_media_cidade_kmh', 40.0)

    def heuristic(no_atual):
        h_dist = grafo.get_distancia_heuristica(no_atual, objetivo)
        if cost_type == 'distancia':
            return h_dist
        else:
            # Gulosa usa a estimativa simples sem considerar trânsito
            return (h_dist / velocidade_media) * 60
            
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