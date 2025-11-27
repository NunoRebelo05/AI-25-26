import math
import json
import os

class Grafo:
    """
    Representa a cidade (mapa) como um grafo ponderado e dirigido.
    
    Armazena os nós (localizações) e as arestas (caminhos),
    juntamente com os custos dinâmicos (distância e tempo).
    """
    
    @staticmethod
    def carregar_de_json(caminho_ficheiro: str) -> 'Grafo':
        """
        Carrega um grafo a partir de um ficheiro JSON.
        
        Centraliza a lógica de carregamento e tratamento de erros.
        
        Args:
            caminho_ficheiro (str): Caminho para o ficheiro JSON do mapa.
            
        Returns:
            Grafo: Instância do grafo carregado ou None em caso de erro.
        """
        if not os.path.exists(caminho_ficheiro):
            print(f"ERRO CRÍTICO: Ficheiro de mapa '{caminho_ficheiro}' não encontrado.")
            return None

        mapa = Grafo()
        try:
            with open(caminho_ficheiro, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Validar estrutura básica
                if 'nos' not in data or 'arestas' not in data:
                    raise ValueError("JSON mal formatado: chaves 'nos' ou 'arestas' em falta.")

                for no in data['nos']:
                    mapa.add_no(no['id'], no['lat'], no['lon'], no.get('tipo', 'PontoInteresse'))
                    if no.get('pode_carregar'):
                        mapa.nos[no['id']]['pode_carregar'] = True
                
                for aresta in data['arestas']:
                    mapa.add_aresta(aresta['origem'], aresta['destino'], aresta['distancia_km'], aresta['tempo_base_min'])
                
                print(f"INFO: Grafo carregado com sucesso de '{caminho_ficheiro}'. ({len(mapa.nos)} nós)")
                return mapa
                
        except json.JSONDecodeError:
            print(f"ERRO: Ficheiro '{caminho_ficheiro}' não é um JSON válido.")
        except Exception as e:
            print(f"ERRO: Falha ao carregar mapa: {e}")
        
        return None

    def __init__(self):
        """Inicializa um grafo vazio."""
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
        
        Args:
            id_no (str): Identificador único do nó.
            lat (float): Latitude.
            lon (float): Longitude.
            tipo (str, optional): Tipo de local ('Recolha', 'EstacaoRecarga', etc.).
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
        
        Args:
            origem (str): ID do nó de origem.
            destino (str): ID do nó de destino.
            distancia_km (float): Distância da aresta em km.
            tempo_base_min (float): Tempo base de percurso em minutos (sem trânsito).
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
        """
        Retorna uma lista de IDs dos nós vizinhos (destinos).
        
        Args:
            id_no (str): ID do nó.
            
        Returns:
            list: Lista de IDs dos nós adjacentes.
        """
        if id_no in self.arestas:
            return list(self.arestas[id_no].keys())
        return []

    def get_custo_aresta(self, origem: str, destino: str) -> (float, float):
        """
        Retorna o custo atual de uma aresta, considerando o trânsito.
        
        Args:
            origem (str): ID do nó de origem.
            destino (str): ID do nó de destino.
            
        Returns:
            tuple: (distancia_km, tempo_viagem_min)
                   Retorna (inf, inf) se a aresta não existir.
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
        Simula a mudança nas condições de trânsito numa aresta específica.
        
        Args:
            origem (str): ID do nó de origem.
            destino (str): ID do nó de destino.
            multiplicador (float): Fator de trânsito (1.0 = normal, >1.0 = lento).
        """
        if (origem, destino) in self.condicoes_transito:
            self.condicoes_transito[(origem, destino)] = multiplicador
        else:
            print(f"Aviso: Aresta ({origem}, {destino}) não existe para atualizar trânsito.")

    def get_distancia_heuristica(self, no_atual: str, no_objetivo: str) -> float:
        """
        Calcula a distância em linha reta (Haversine) entre dois nós.
        
        Utilizada como heurística 'h(n)' para o algoritmo A*.
        
        Args:
            no_atual (str): ID do nó atual.
            no_objetivo (str): ID do nó objetivo.
            
        Returns:
            float: Distância em km.
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
    # Teste rápido do carregamento
    print("--- Teste de Carregamento ---")
    mapa = Grafo.carregar_de_json("braga_mapa.json")
    if mapa:
        print(mapa)