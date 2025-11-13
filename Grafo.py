import math # Para a fórmula de Haversine

class Grafo:
    """
    Representa a cidade (mapa) como um grafo ponderado e dirigido.
    Armazena os nós (localizações) e as arestas (caminhos),
    juntamente com os custos dinâmicos (distância e tempo).
    """
    
    def __init__(self):
        # self.nos armazena dados sobre cada nó (ex: coordenadas, tipo)
        # Formato: { 'id_no': { 'lat': float, 'lon': float, 'tipo': str } }
        self.nos = {}
        
        # self.arestas armazena as ligações (vizinhança)
        # Formato: { 'origem': { 'destino': { 'distancia_km': float, 'tempo_base_min': float } } }
        # Usamos um grafo dirigido, pois o tempo A->B pode ser != B->A
        self.arestas = {}
        
        # self.transito armazena os multiplicadores de trânsito atuais
        # Formato: { ('origem', 'destino'): float_multiplicador }
        self.condicoes_transito = {}

    def __repr__(self):
        return f"Grafo com {len(self.nos)} nós e {len(self.arestas)} conjuntos de arestas."

    def add_no(self, id_no: str, lat: float, lon: float, tipo: str = 'PontoInteresse'):
        """
        Adiciona um nó (localização) ao grafo.
        'tipo' pode ser 'Recolha', 'EstacaoRecarga', 'PostoAbastecimento', etc. 
        """
        if id_no not in self.nos:
            self.nos[id_no] = {'lat': lat, 'lon': lon, 'tipo': tipo}
            self.arestas[id_no] = {} # Inicializa a lista de adjacências
        else:
            print(f"Aviso: Nó {id_no} já existe.")

    def add_aresta(self, origem: str, destino: str, distancia_km: float, tempo_base_min: float):
        """
        Adiciona uma aresta dirigida (caminho) entre dois nós.
        Permite que A->B e B->A tenham custos diferentes.
        """
        if origem not in self.nos or destino not in self.nos:
            print(f"Erro: Nós de origem ({origem}) ou destino ({destino}) não existem.")
            return
            
        self.arestas[origem][destino] = {
            'distancia_km': distancia_km,
            'tempo_base_min': tempo_base_min
        }
        # Inicializa o trânsito como normal (multiplicador 1.0)
        self.condicoes_transito[(origem, destino)] = 1.0

    def get_vizinhos(self, id_no: str) -> list:
        """Retorna uma lista de IDs dos nós vizinhos (destinos)."""
        if id_no in self.arestas:
            return list(self.arestas[id_no].keys())
        return []

    def get_custo_aresta(self, origem: str, destino: str) -> (float, float):
        """
        Retorna o custo atual de uma aresta.
        Retorna (distancia_km, tempo_viagem_min)
        O tempo de viagem é afetado pelo trânsito. 
        """
        if destino not in self.arestas.get(origem, {}):
            # Não há ligação direta
            return (float('inf'), float('inf'))
        
        dados_aresta = self.arestas[origem][destino]
        distancia = dados_aresta['distancia_km']
        
        # Custo dinâmico de tempo
        tempo_base = dados_aresta['tempo_base_min']
        multiplicador = self.condicoes_transito.get((origem, destino), 1.0)
        tempo_atual = tempo_base * multiplicador
        
        return (distancia, tempo_atual)

    def atualizar_transito(self, origem: str, destino: str, multiplicador: float):
        """
        Simula a mudança nas condições de trânsito. 
        (ex: 1.0 = normal, 1.5 = lento, 2.0 = muito lento)
        """
        if (origem, destino) in self.condicoes_transito:
            self.condicoes_transito[(origem, destino)] = multiplicador
        else:
            print(f"Aviso: Aresta ({origem}, {destino}) não existe para atualizar trânsito.")

    def get_distancia_heuristica(self, no_atual: str, no_objetivo: str) -> float:
        """
        Calcula a distância em linha reta (Haversine) entre dois nós.
        Esta será a nossa heurística 'h(n)' para o A*.
        Retorna a distância em km.
        """
        if no_atual not in self.nos or no_objetivo not in self.nos:
            return float('inf')
            
        pos1 = self.nos[no_atual]
        pos2 = self.nos[no_objetivo]
        
        R = 6371  # Raio da Terra em km
        
        lat1_rad = math.radians(pos1['lat'])
        lon1_rad = math.radians(pos1['lon'])
        lat2_rad = math.radians(pos2['lat'])
        lon2_rad = math.radians(pos2['lon'])
        
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distancia = R * c
        return distancia


# --- Exemplo de utilização (para testar o ficheiro) ---
if __name__ == "__main__":
    
    # Criar um grafo simples (simulando Braga)
    mapa_braga = Grafo()
    
    # Adicionar Nós (com coordenadas approx. de Braga)
    mapa_braga.add_no("Centro", 41.5518, -8.4231, tipo="ZonaRecolha")
    mapa_braga.add_no("UMinho_Gualtar", 41.5623, -8.3952, tipo="ZonaRecolha")
    mapa_braga.add_no("Estacao_CP", 41.5471, -8.4326, tipo="PontoInteresse")
    mapa_braga.add_no("Estacao_Recarga_Eletrica", 41.5580, -8.4100, tipo="EstacaoRecarga")

    # Adicionar Arestas (custos inventados para o exemplo)
    mapa_braga.add_aresta("Centro", "UMinho_Gualtar", 4.5, 8.0)
    mapa_braga.add_aresta("UMinho_Gualtar", "Centro", 4.2, 7.5)
    
    mapa_braga.add_aresta("Centro", "Estacao_CP", 1.8, 4.0)
    mapa_braga.add_aresta("Estacao_CP", "Centro", 2.0, 5.0)

    mapa_braga.add_aresta("Centro", "Estacao_Recarga_Eletrica", 2.5, 6.0)
    mapa_braga.add_aresta("UMinho_Gualtar", "Estacao_Recarga_Eletrica", 2.2, 5.0)

    print(mapa_braga)
    
    print("\n--- Teste de Custos ---")
    
    # Custo normal
    dist, tempo = mapa_braga.get_custo_aresta("Centro", "UMinho_Gualtar")
    print(f"Centro -> UMinho (Normal): {dist:.1f} km, {tempo:.1f} min")
    
    # Simular hora de ponta 
    mapa_braga.atualizar_transito("Centro", "UMinho_Gualtar", 2.0) # O dobro do tempo
    dist, tempo = mapa_braga.get_custo_aresta("Centro", "UMinho_Gualtar")
    print(f"Centro -> UMinho (Trânsito): {dist:.1f} km, {tempo:.1f} min")

    print("\n--- Teste de Heurística (A*) ---")
    
    # Distância real vs. heurística (linha reta)
    dist_real, _ = mapa_braga.get_custo_aresta("Centro", "Estacao_CP")
    dist_heuristica = mapa_braga.get_distancia_heuristica("Centro", "Estacao_CP")
    
    print(f"Custo real (distância) Centro -> Estacao_CP: {dist_real:.2f} km")
    print(f"Heurística (linha reta) Centro -> Estacao_CP: {dist_heuristica:.2f} km")
    # Nota: A heurística deve ser sempre <= ao custo real (admissível)