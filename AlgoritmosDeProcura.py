import heapq
from collections import deque
from Grafo import Grafo # Importamos a classe do mapa

# Constante para a heurística de tempo do A*
VELOCIDADE_MAXIMA_ASSUMIDA_KMH = 80.0

def a_star_search(grafo: Grafo, inicio: str, objetivo: str, 
                  cost_type: str = 'distancia', use_heuristic: bool = True):
    """
    Implementação do algoritmo A* (e UCS).
    """
    
    g_costs = {no: float('inf') for no in grafo.nos}
    g_costs[inicio] = 0
    
    def heuristic(no_atual):
        if not use_heuristic:
            return 0 # h(n) = 0 -> A* transforma-se em UCS (Dijkstra)
            
        h_dist = grafo.get_distancia_heuristica(no_atual, objetivo)
        
        if cost_type == 'distancia':
            return h_dist
        else: # cost_type == 'tempo'
            h_tempo_horas = h_dist / VELOCIDADE_MAXIMA_ASSUMIDA_KMH
            return h_tempo_horas * 60 # Converter para minutos
            
    frontier = [(heuristic(inicio), 0, inicio, [inicio])]
    heapq.heapify(frontier)
    visited = set()

    while frontier:
        f_cost_atual, g_cost_atual, no_atual, caminho = heapq.heappop(frontier)
        
        if no_atual in visited:
            continue
        if no_atual == objetivo:
            return caminho, g_cost_atual

        visited.add(no_atual)

        for vizinho in grafo.get_vizinhos(no_atual):
            if vizinho in visited:
                continue
                
            dist, tempo = grafo.get_custo_aresta(no_atual, vizinho)
            custo_aresta = dist if cost_type == 'distancia' else tempo
            novo_g_cost = g_cost_atual + custo_aresta
            
            if novo_g_cost < g_costs[vizinho]:
                g_costs[vizinho] = novo_g_cost
                h_cost_vizinho = heuristic(vizinho)
                novo_f_cost = novo_g_cost + h_cost_vizinho
                heapq.heappush(frontier, (novo_f_cost, novo_g_cost, vizinho, caminho + [vizinho]))

    return None, float('inf')


def greedy_search(grafo: Grafo, inicio: str, objetivo: str, 
                  cost_type: str = 'distancia'):
    """
    Implementação do algoritmo Guloso (Greedy Best-First Search).
    """
    
    def heuristic(no_atual):
        h_dist = grafo.get_distancia_heuristica(no_atual, objetivo)
        
        if cost_type == 'distancia':
            return h_dist
        else: # cost_type == 'tempo'
            h_tempo_horas = h_dist / VELOCIDADE_MAXIMA_ASSUMIDA_KMH
            return h_tempo_horas * 60
            
    frontier = [(heuristic(inicio), inicio, [inicio])]
    heapq.heapify(frontier)
    visited = set()

    while frontier:
        h_cost_atual, no_atual, caminho = heapq.heappop(frontier)
        
        if no_atual in visited:
            continue
            
        if no_atual == objetivo:
            # Calcular o custo *real* (g) do caminho encontrado
            custo_real_g = 0.0
            for i in range(len(caminho) - 1):
                dist, tempo = grafo.get_custo_aresta(caminho[i], caminho[i+1])
                custo_real_g += tempo if cost_type == 'tempo' else dist
            return caminho, custo_real_g

        visited.add(no_atual)

        for vizinho in grafo.get_vizinhos(no_atual):
            if vizinho in visited:
                continue
                
            h_cost_vizinho = heuristic(vizinho)
            heapq.heappush(frontier, (h_cost_vizinho, vizinho, caminho + [vizinho]))

    return None, float('inf') # Retorno em caso de falha


def dfs_search(grafo: Grafo, inicio: str, objetivo: str, cost_type: str = 'tempo'):
    """
    Implementação do algoritmo DFS (Busca em Profundidade).
    """
    
    frontier = [(inicio, [inicio])]  # Pilha (LIFO)
    visited = set()

    while frontier:
        no_atual, caminho = frontier.pop()
        
        if no_atual in visited:
            continue
            
        if no_atual == objetivo:
            # Encontrou *um* caminho. Calcular o seu custo.
            custo_real_g = 0.0
            for i in range(len(caminho) - 1):
                dist, tempo = grafo.get_custo_aresta(caminho[i], caminho[i+1])
                custo_real_g += tempo if cost_type == 'tempo' else dist
            return caminho, custo_real_g
        
        visited.add(no_atual)

        for vizinho in grafo.get_vizinhos(no_atual):
            if vizinho not in visited:
                frontier.append((vizinho, caminho + [vizinho]))

    return None, float('inf')


# --- FUNÇÃO BFS MODIFICADA ---
def bfs_search(grafo: Grafo, inicio: str, objetivo: str, cost_type: str = 'tempo'):
    """
    Implementação do algoritmo BFS (Busca em Largura).
    Encontra o caminho com o *menor número de "saltos"*.
    Modificado para retornar (caminho, custo_real) para ser compatível com o Gestor.
    """
    
    frontier = deque([(inicio, [inicio])]) # Fila (FIFO)
    visited = {inicio}

    while frontier:
        no_atual, caminho = frontier.popleft() # .popleft() (FIFO)
        
        if no_atual == objetivo:
            # --- CÁLCULO DE CUSTO ADICIONADO ---
            custo_real_g = 0.0
            for i in range(len(caminho) - 1):
                dist, tempo = grafo.get_custo_aresta(caminho[i], caminho[i+1])
                custo_real_g += tempo if cost_type == 'tempo' else dist
            return caminho, custo_real_g # <--- FIX: Retorna (caminho, custo)

        for vizinho in grafo.get_vizinhos(no_atual):
            if vizinho not in visited:
                visited.add(vizinho)
                frontier.append((vizinho, caminho + [vizinho]))

    return None, float('inf') 