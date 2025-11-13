from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao, EstadoVeiculo
from Pedido import Pedido, PrioridadePedido
from AlgoritmosDeProcura import a_star_search
from datetime import datetime, timedelta

# Estes pesos (W) definem a estratégia da empresa.
# Podes (e deves!) ajustá-los para testar diferentes
# otimizações.
PESOS_ESTRATEGIA = {
    'W_TEMPO_ESPERA': 1.5,  # Prioriza a satisfação do cliente
    'W_CUSTO_OPER': 1.0,  # Prioriza o custo para a empresa
    'W_KM_SEM_PAX': 0.8,  # Penaliza ineficiência
    'PENALIZACAO_AMBIENTAL': 50.0, # Custo "fictício" alto
    'PENALIZACAO_PRIORIDADE': 3.0  # Multiplicador para pedidos urgentes
}


class GestorDeFrota:
    """
    O cérebro da TaxiGreen.
    Mantém o estado da frota e do mapa, e toma as decisões
    de alocação de veículos a pedidos.
    """
    
    def __init__(self, grafo: Grafo):
        self.grafo = grafo
        self.frota = {} # Dicionário {id_veiculo: Objeto Taxi}
        self.pedidos_pendentes = []

    def add_taxi(self, taxi: Taxi):
        """Adiciona um novo táxi à frota gerida."""
        self.frota[taxi.id_veiculo] = taxi
        print(f"INFO: Taxi {taxi.id_veiculo} adicionado à frota.")

    def decidir_alocacao(self, pedido: Pedido):
        """
        Método de decisão. Apenas encontra o melhor táxi.
        Não altera o estado de nenhum objeto.
        Usado pelo Simulador.
        """
        
        melhor_taxi, melhor_custo, detalhes_caminho = self._encontrar_melhor_taxi(pedido)
        
        # Retorna o plano para o simulador executar
        return melhor_taxi, melhor_custo, detalhes_caminho

    def _processar_e_alocar(self, pedido: Pedido):
        """
        Função original (agora interna ou para testes simples).
        Decide E aloca imediatamente.
        """
        print(f"\n--- A processar Pedido {pedido.id_pedido} ---")
        print(f"De: {pedido.origem} Para: {pedido.destino} ({pedido.num_passageiros} pax)")
        
        melhor_taxi, melhor_custo, detalhes_caminho = self._encontrar_melhor_taxi(pedido)
        
        if melhor_taxi:
            (caminho_pickup, caminho_viagem) = detalhes_caminho
            tempo_espera_min = self._get_tempo_caminho(caminho_pickup)
            
            # --- AÇÃO: Alocar o táxi ---
            hora_recolha = datetime.now() + timedelta(minutes=tempo_espera_min)
            pedido.alocar(melhor_taxi.id_veiculo, hora_recolha)
            melhor_taxi.alocar_para_servico()
            
            print(f"SUCESSO: Alocado Taxi {melhor_taxi.id_veiculo}...")
        else:
            pedido.rejeitar()
            print(f"FALHA: Pedido {pedido.id_pedido} rejeitado.")

    def _encontrar_melhor_taxi(self, pedido: Pedido) -> (Taxi, float, tuple):
        """
        Itera por todos os táxis LIVRES e calcula o seu "custo de alocação".
        Retorna o táxi com o menor custo.
        """
        melhor_custo_global = float('inf')
        melhor_taxi_escolhido = None
        melhores_caminhos = None
        
        # Iterar por todos os táxis da frota
        for id_taxi, taxi in self.frota.items():
            
            # 1. Filtro rápido de viabilidade
            if taxi.estado != EstadoVeiculo.LIVRE:
                continue # Táxi ocupado
            if taxi.capacidade_passageiros < pedido.num_passageiros:
                continue # Não cabem os passageiros
                
            # 2. Calcular o custo de alocação (o "cérebro")
            custo, caminhos = self._calcular_custo_alocacao(taxi, pedido)
            
            if custo < melhor_custo_global:
                melhor_custo_global = custo
                melhor_taxi_escolhido = taxi
                melhores_caminhos = caminhos
                
        return melhor_taxi_escolhido, melhor_custo_global, melhores_caminhos

    def _calcular_custo_alocacao(self, taxi: Taxi, pedido: Pedido) -> (float, tuple):
        """
        A "Função de Custo" da Tarefa 1.
        Calcula o custo de alocar este 'taxi' específico a este 'pedido'.
        Retorna (custo_total, (caminho_pickup, caminho_viagem))
        """
        
        # --- PASSO 1: Calcular os caminhos via A* ---
        
        # Otimizamos os caminhos por TEMPO, pois é o que
        # afeta diretamente o cliente e a operação.
        
        # Caminho 1: Localização atual do táxi -> Origem do Pedido
        caminho_pickup, tempo_espera = a_star_search(
            self.grafo, taxi.localizacao_atual, pedido.origem, 'tempo'
        )
        if not caminho_pickup:
            return float('inf'), None # Não há caminho do táxi ao cliente

        # Caminho 2: Origem do Pedido -> Destino do Pedido
        caminho_viagem, tempo_viagem = a_star_search(
            self.grafo, pedido.origem, pedido.destino, 'tempo'
        )
        if not caminho_viagem:
            return float('inf'), None # Não há caminho da origem ao destino
            
        # --- PASSO 2: Obter métricas secundárias (distância) ---
        dist_pickup = self._get_dist_caminho(caminho_pickup)
        dist_viagem = self._get_dist_caminho(caminho_viagem)
        dist_total = dist_pickup + dist_viagem
        
        # --- PASSO 3: Verificar viabilidade de autonomia ---
        if not taxi.pode_aceitar_pedido(pedido.num_passageiros, dist_total):
            return float('inf'), None # Não tem autonomia suficiente

        # --- PASSO 4: Calcular os componentes de custo ---
        C_espera = tempo_espera # Tempo que o cliente espera
        C_oper = dist_total * taxi.custo_por_km # Custo monetário total
        C_vazio = dist_pickup * taxi.custo_por_km # Custo da "ineficiência"
        
        C_amb = 0.0 # Custo ambiental
        if pedido.pref_ambiental and taxi.tipo == TipoMotorizacao.COMBUSTAO:
            C_amb = PESOS_ESTRATEGIA['PENALIZACAO_AMBIENTAL']
            
        # Ponderar o tempo de espera pela prioridade do pedido
        W_espera = PESOS_ESTRATEGIA['W_TEMPO_ESPERA']
        if pedido.prioridade == PrioridadePedido.URGENTE:
            W_espera *= PESOS_ESTRATEGIA['PENALIZACAO_PRIORIDADE']
            
        # --- PASSO 5: Função de Custo Final Ponderada ---
        custo_final = (
            (W_espera * C_espera) +
            (PESOS_ESTRATEGIA['W_CUSTO_OPER'] * C_oper) +
            (PESOS_ESTRATEGIA['W_KM_SEM_PAX'] * C_vazio) +
            C_amb
        )
        
        return custo_final, (caminho_pickup, caminho_viagem)

    # --- Funções Auxiliares de Cálculo de Caminho ---
    
    def _get_dist_caminho(self, caminho: list) -> float:
        """Calcula a distância total de um caminho (lista de nós)."""
        dist_total = 0.0
        for i in range(len(caminho) - 1):
            dist, _ = self.grafo.get_custo_aresta(caminho[i], caminho[i+1])
            dist_total += dist
        return dist_total

    def _get_tempo_caminho(self, caminho: list) -> float:
        """Calcula o tempo total de um caminho (lista de nós)."""
        tempo_total = 0.0
        for i in range(len(caminho) - 1):
            _, tempo = self.grafo.get_custo_aresta(caminho[i], caminho[i+1])
            tempo_total += tempo
        return tempo_total


# --- Exemplo de utilização (para testar o ficheiro) ---
if __name__ == "__main__":
    
    # 1. Criar o Grafo (do exemplo do Grafo.py)
    from Grafo import Grafo
    mapa_braga = Grafo()
    mapa_braga.add_no("Centro", 41.5518, -8.4231)
    mapa_braga.add_no("UMinho_Gualtar", 41.5623, -8.3952)
    mapa_braga.add_no("Estacao_CP", 41.5471, -8.4326)
    mapa_braga.add_no("Estacao_Recarga", 41.5580, -8.4100)
    mapa_braga.add_aresta("Centro", "UMinho_Gualtar", 4.5, 10.0) # 10 min
    mapa_braga.add_aresta("UMinho_Gualtar", "Centro", 4.2, 9.0)
    mapa_braga.add_aresta("Centro", "Estacao_CP", 1.8, 5.0) # 5 min
    mapa_braga.add_aresta("Estacao_CP", "Centro", 2.0, 6.0)
    mapa_braga.add_aresta("Centro", "Estacao_Recarga", 3.0, 7.0)
    mapa_braga.add_aresta("Estacao_Recarga", "UMinho_Gualtar", 2.2, 5.0)
    mapa_braga.add_aresta("Estacao_CP", "UMinho_Gualtar", 6.0, 18.0) # Caminho lento
    
    # 2. Criar os Taxis
    # Táxi Elétrico: Barato, mas está longe
    taxi_ev = Taxi("EV01", TipoMotorizacao.ELETRICO, "UMinho_Gualtar", 4, 0.15, 300)
    
    # Táxi Combustão: Caro, mas está perto
    taxi_gas = Taxi("GAS01", TipoMotorizacao.COMBUSTAO, "Estacao_CP", 4, 0.30, 600)

    # 3. Criar o Gestor e adicionar a frota
    gestor = GestorDeFrota(mapa_braga)
    gestor.add_taxi(taxi_ev)
    gestor.add_taxi(taxi_gas)
    
    # 4. Criar um Pedido (do Centro para a UMinho)
    pedido_1 = Pedido(
        origem="Centro",
        destino="UMinho_Gualtar",
        num_passageiros=2,
        pref_ambiental=False # Sem preferência
    )
    
    # 5. Processar o pedido
    gestor.processar_novo_pedido(pedido_1)
    
    # 6. Criar um Pedido com Preferência Ambiental
    pedido_2 = Pedido(
        origem="Estacao_CP",
        destino="Centro",
        num_passageiros=1,
        pref_ambiental=True # COM preferência
    )
    
    # 7. Processar o segundo pedido
    # (Nota: o táxi do pedido 1 já está "OCUPADO" no mundo real)
    # (Para este teste, vamos libertar o táxi que foi alocado)
    
    # gestor.frota['EV01'].libertar_no_destino("UMinho_Gualtar") # Reset
    gestor.frota[pedido_1.id_veiculo_alocado].libertar_no_destino("UMinho_Gualtar")
    
    gestor.processar_novo_pedido(pedido_2)