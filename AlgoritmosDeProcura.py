import heapq
from collections import deque
from Grafo import Grafo # Importamos a classe do mapa

# Constante para a heurística de tempo do A*
# Assumimos uma "velocidade máxima" no grafo (ex: 80 km/h) para
# converter a distância em linha reta (km) numa heurística de tempo (minutos)
VELOCIDADE_MAXIMA_ASSUMIDA_KMH = 80.0

def a_star_search(grafo: Grafo, inicio: str, objetivo: str, 
                  cost_type: str = 'distancia', use_heuristic: bool = True):
    """
    Implementação do algoritmo A* (e UCS).
    
    Encontra o caminho de menor custo do 'inicio' ao 'objetivo' num 'grafo'.
    
    :param grafo: O objeto Grafo da cidade.
    :param inicio: ID do nó de partida.
    :param objetivo: ID do nó de destino.
    :param cost_type: 'distancia' ou 'tempo' - O que estamos a otimizar.
    :param use_heuristic: Se True, atua como A*. 
                          Se False, atua como UCS (Dijkstra).
    :return: Uma tupla (caminho, custo_total) ou (None, float('inf')) se
             não houver caminho.
    """
    
    # g_costs: Armazena o custo (g(n)) do início até cada nó.
    g_costs = {no: float('inf') for no in grafo.nos}
    g_costs[inicio] = 0
    
    # f_costs: Armazena o custo estimado (f(n) = g(n) + h(n)).
    # Apenas usado internamente pela fila de prioridade.
    
    #
    # h(n): A nossa função heurística
    def heuristic(no_atual):
        if not use_heuristic:
            return 0 # h(n) = 0 -> A* transforma-se em UCS (Dijkstra)
            
        # Heurística de distância (admissível)
        h_dist = grafo.get_distancia_heuristica(no_atual, objetivo)
        
        if cost_type == 'distancia':
            return h_dist # h(n) é a distância em linha reta
        else: # cost_type == 'tempo'
            # h(n) é a distância em linha reta / velocidade máxima
            # (Converte distância em tempo mínimo)
            h_tempo_horas = h_dist / VELOCIDADE_MAXIMA_ASSUMIDA_KMH
            return h_tempo_horas * 60 # Converter para minutos
            
    # Frontier (Fila de Prioridade)
    # Formato: (f_cost, g_cost, no_atual, caminho_ate_aqui)
    frontier = [(heuristic(inicio), 0, inicio, [inicio])]
    heapq.heapify(frontier)
    
    # Visited (ou Closed Set)
    # Armazena nós para os quais já encontrámos o caminho ótimo.
    visited = set()

    while frontier:
        # 1. Retirar o nó com menor f_cost da fronteira
        f_cost_atual, g_cost_atual, no_atual, caminho = heapq.heappop(frontier)
        
        # 2. Se já o visitámos, é um caminho mais caro. Ignorar.
        if no_atual in visited:
            continue
            
        # 3. Se é o objetivo, encontrámos o caminho!
        if no_atual == objetivo:
            return caminho, g_cost_atual # Retorna o caminho e o seu custo real (g)

        # 4. Marcar o nó como visitado
        visited.add(no_atual)

        # 5. Explorar vizinhos
        for vizinho in grafo.get_vizinhos(no_atual):
            if vizinho in visited:
                continue
                
            # Obter custo real da aresta
            dist, tempo = grafo.get_custo_aresta(no_atual, vizinho)
            
            # Escolher o custo com base no que estamos a otimizar
            if cost_type == 'distancia':
                custo_aresta = dist
            else: # 'tempo'
                custo_aresta = tempo
                
            # 6. Calcular novo custo g(n) para o vizinho
            novo_g_cost = g_cost_atual + custo_aresta
            
            # 7. Se este é um caminho melhor para o vizinho...
            if novo_g_cost < g_costs[vizinho]:
                g_costs[vizinho] = novo_g_cost
                
                # Calcular o f_cost para o vizinho
                h_cost_vizinho = heuristic(vizinho)
                novo_f_cost = novo_g_cost + h_cost_vizinho
                
                # 8. Adicionar o vizinho à fronteira
                heapq.heappush(frontier, (novo_f_cost, novo_g_cost, vizinho, caminho + [vizinho]))

    # Se a fronteira ficar vazia e não encontrámos o objetivo
    return None, float('inf')


def bfs_search(grafo: Grafo, inicio: str, objetivo: str):
    """
    Implementação do algoritmo BFS (Busca em Largura).
    
    Encontra o caminho com o *menor número de "saltos" (arestas)*,
    ignorando completamente os custos (distância/tempo).
    
    :return: Uma lista (caminho) ou None se não houver caminho.
    """
    
    # Frontier (Fila normal)
    # Formato: (no_atual, caminho_ate_aqui)
    frontier = deque([(inicio, [inicio])])
    
    # Visited
    # Em BFS, marcamos como visitado ao *adicionar* à fila,
    # para evitar adicionar o mesmo nó várias vezes.
    visited = {inicio}

    while frontier:
        # 1. Retirar o nó mais antigo da fila (FIFO)
        no_atual, caminho = frontier.popleft()
        
        # 2. Se é o objetivo, encontrámos o caminho!
        if no_atual == objetivo:
            return caminho # Retorna apenas o caminho

        # 3. Explorar vizinhos
        for vizinho in grafo.get_vizinhos(no_atual):
            if vizinho not in visited:
                # 4. Marcar como visitado e adicionar à fila
                visited.add(vizinho)
                frontier.append((vizinho, caminho + [vizinho]))

    # Se a fronteira ficar vazia
    return None

# --- Exemplo de utilização (para testar o ficheiro) ---

def _criar_grafo_teste():
    """Função local para criar o nosso grafo de Braga."""
    mapa_braga = Grafo()
    mapa_braga.add_no("Centro", 41.5518, -8.4231)
    mapa_braga.add_no("UMinho_Gualtar", 41.5623, -8.3952)
    mapa_braga.add_no("Estacao_CP", 41.5471, -8.4326)
    mapa_braga.add_no("Estacao_Recarga_Eletrica", 41.5580, -8.4100)
    
    # Caminhos
    mapa_braga.add_aresta("Centro", "UMinho_Gualtar", 4.5, 10.0) # 10 min
    mapa_braga.add_aresta("UMinho_Gualtar", "Centro", 4.2, 9.0)
    
    mapa_braga.add_aresta("Centro", "Estacao_CP", 1.8, 5.0) # 5 min
    mapa_braga.add_aresta("Estacao_CP", "Centro", 2.0, 6.0)

    # Um caminho mais "curto" em nós, mas mais longo em distância/tempo
    mapa_braga.add_aresta("Centro", "Estacao_Recarga_Eletrica", 3.0, 7.0)
    mapa_braga.add_aresta("Estacao_Recarga_Eletrica", "UMinho_Gualtar", 2.2, 5.0)

    return mapa_braga

if __name__ == "__main__":
    
    mapa_braga = _criar_grafo_teste()
    
    INICIO = "Estacao_CP"
    FIM = "UMinho_Gualtar"

    print(f"--- A* Otimizado por DISTÂNCIA ({INICIO} -> {FIM}) ---")
    caminho_a_dist, custo_a_dist = a_star_search(mapa_braga, INICIO, FIM, 
                                                 cost_type='distancia')
    if caminho_a_dist:
        print(f"Caminho: {' -> '.join(caminho_a_dist)}")
        print(f"Custo (km): {custo_a_dist:.2f} km")
    else:
        print("Caminho não encontrado.")

    print(f"\n--- A* Otimizado por TEMPO ({INICIO} -> {FIM}) ---")
    caminho_a_tempo, custo_a_tempo = a_star_search(mapa_braga, INICIO, FIM, 
                                                   cost_type='tempo')
    if caminho_a_tempo:
        print(f"Caminho: {' -> '.join(caminho_a_tempo)}")
        print(f"Custo (min): {custo_a_tempo:.2f} min")
    else:
        print("Caminho não encontrado.")
        
    print(f"\n--- BFS (Menos 'Paragens') ({INICIO} -> {FIM}) ---")
    caminho_bfs = bfs_search(mapa_braga, INICIO, FIM)
    if caminho_bfs:
        print(f"Caminho: {' -> '.join(caminho_bfs)}")
        print(f"(Nota: Custo é ignorado, foca-se no nº de arestas)")
    else:
        print("Caminho não encontrado.")

    print("\n--- NOTA IMPORTANTE: BFS vs. UCS ---")
    print("O BFS encontra o caminho com menos 'saltos'.")
    print("Para o teu projeto, que foca em CUSTOS (distância, tempo),  "
          "a 'procura não informada' correta é o Uniform Cost Search (UCS).")
    print("O UCS é apenas o A* com uma heurística h(n) = 0.")
    print("Podes correr o UCS assim:\n")

    print(f"--- UCS Otimizado por DISTÂNCIA ({INICIO} -> {FIM}) ---")
    caminho_ucs, custo_ucs = a_star_search(mapa_braga, INICIO, FIM, 
                                           cost_type='distancia', 
                                           use_heuristic=False) # <- A magia está aqui
    if caminho_ucs:
        print(f"Caminho: {' -> '.join(caminho_ucs)}")
        print(f"Custo (km): {custo_ucs:.2f} km")