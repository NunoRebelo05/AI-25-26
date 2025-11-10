from enum import Enum, auto

class TipoMotorizacao(Enum):
    COMBUSTAO = auto()
    ELETRICO = auto()

class EstadoVeiculo(Enum):
    LIVRE = auto()
    OCUPADO = auto()        # Em serviço (a ir buscar ou a levar passageiro)
    A_CARREGAR = auto()     # Apenas elétricos, em estação
    A_ABASTECER = auto()    # Apenas combustão, em posto
    EM_FALHA = auto()       # Estado adicional para simular falhas

class Taxi:
    
    def __init__(self, 
                 id_veiculo: str, 
                 tipo: TipoMotorizacao, 
                 localizacao_atual: str,
                 capacidade_passageiros: int, 
                 custo_por_km: float, 
                 autonomia_maxima: float):
        
        self.id_veiculo = id_veiculo
        
        # Características fixas
        self.tipo = tipo                                       
        self.capacidade_passageiros = capacidade_passageiros   
        self.custo_por_km = custo_por_km                       
        self.autonomia_maxima = autonomia_maxima              

        # Características dinâmicas (estado)
        self.localizacao_atual = localizacao_atual            #  (ex: 'Nó_A', 'Centro')
        self.autonomia_atual = autonomia_maxima               #  (Assumindo que começa cheio)
        self.estado = EstadoVeiculo.LIVRE                      

    def __repr__(self):
        """Representação textual do objeto para debugging."""
        return (f"Taxi(ID: {self.id_veiculo}, Tipo: {self.tipo.name}, "
                f"Estado: {self.estado.name}, Loc: {self.localizacao_atual}, "
                f"Aut: {self.autonomia_atual:.1f}/{self.autonomia_maxima:.1f} km, "
                f"Cap: {self.capacidade_passageiros} pax)")

    # --- Métodos de Verificação ---

    def pode_aceitar_pedido(self, num_passageiros: int, distancia_total_estimada: float) -> bool:
        """
        Verifica se o táxi pode aceitar um pedido com base no seu estado atual.
        """
        if self.estado != EstadoVeiculo.LIVRE:
            return False
        if self.capacidade_passageiros < num_passageiros: # 
            return False
        if self.autonomia_atual < distancia_total_estimada: # 
            return False
        
        # Se for elétrico, pode ter regras mais estritas de autonomia mínima
        if self.tipo == TipoMotorizacao.ELETRICO:
            #Não aceita se a viagem o deixar com menos de 10% de autonomia
            if (self.autonomia_atual - distancia_total_estimada) < (self.autonomia_maxima * 0.1):
                return False
                
        return True

    def precisa_recarregar(self, limiar_percentagem: float = 0.20) -> bool:
        """Verifica se a autonomia está abaixo de um limiar crítico."""
        return (self.autonomia_atual / self.autonomia_maxima) < limiar_percentagem

    # --- Métodos de Atualização de Estado ---

    def alocar_para_servico(self):
        """Muda o estado do táxi para ocupado (ex: ao aceitar um pedido)."""
        if self.estado == EstadoVeiculo.LIVRE:
            self.estado = EstadoVeiculo.OCUPADO
        else:
            print(f"AVISO: Tentativa de alocar Taxi {self.id_veiculo} que não está LIVRE.")

    def mover_e_consumir(self, distancia_km: float, localizacao_destino: str):
        """Move o táxi, consome autonomia e atualiza a localização."""
        if self.autonomia_atual >= distancia_km:
            self.autonomia_atual -= distancia_km
            self.localizacao_atual = localizacao_destino
        else:
            # Esta situação deve ser evitada pela lógica de alocação
            print(f"ERRO: Taxi {self.id_veiculo} ficou sem autonomia em trânsito.")
            self.autonomia_atual = 0
            self.estado = EstadoVeiculo.EM_FALHA # Simula falha por falta de energia

    def iniciar_carregamento(self):
        """Muda o estado para carregar/abastecer."""
        if self.tipo == TipoMotorizacao.ELETRICO:
            self.estado = EstadoVeiculo.A_CARREGAR
        else:
            self.estado = EstadoVeiculo.A_ABASTECER

    def terminar_carregamento(self):
        """Completa o carregamento/abastecimento e liberta o táxi."""
        self.autonomia_atual = self.autonomia_maxima
        self.estado = EstadoVeiculo.LIVRE
        print(f"INFO: Taxi {self.id_veiculo} carregado e LIVRE.")
        
    def libertar_no_destino(self, localizacao_destino: str):
        """Termina um serviço, atualiza a localização e fica LIVRE."""
        self.localizacao_atual = localizacao_destino
        self.estado = EstadoVeiculo.LIVRE


# --- Exemplo e Teste de utilização ---
if __name__ == "__main__":
    
    # Criar um táxi elétrico
    taxi_eletrico = Taxi(
        id_veiculo="EV01",
        tipo=TipoMotorizacao.ELETRICO,
        localizacao_atual="Centro",
        capacidade_passageiros=4,
        custo_por_km=0.15, # 
        autonomia_maxima=300.0
    )

    # Criar um táxi a combustão
    taxi_combustao = Taxi(
        id_veiculo="GAS01",
        tipo=TipoMotorizacao.COMBUSTAO,
        localizacao_atual="Aeroporto",
        capacidade_passageiros=6,
        custo_por_km=0.25, # 
        autonomia_maxima=600.0
    )

    print("--- Frota Inicial ---")
    print(taxi_eletrico)
    print(taxi_combustao)

    print("\n--- Simulação de Pedido ---")
    
    # Um pedido chega: 3 passageiros, viagem de 50 km
    num_pax = 3
    dist_total = 50.0
    
    print(f"Pedido: {num_pax} passageiros, {dist_total} km.")
    
    if taxi_eletrico.pode_aceitar_pedido(num_pax, dist_total):
        print(f"Taxi {taxi_eletrico.id_veiculo} PODE aceitar.")
        taxi_eletrico.alocar_para_servico()
        
        # Simular a viagem (ir buscar + levar)
        dist_viagem_total = 60.0 # 10km para ir buscar + 50km de viagem
        local_destino = "Estacao_CP"
        taxi_eletrico.mover_e_consumir(dist_viagem_total, local_destino)
        taxi_eletrico.libertar_no_destino(local_destino)
        
        print(f"Serviço concluído por {taxi_eletrico.id_veiculo}.")
    else:
        print(f"Taxi {taxi_eletrico.id_veiculo} NÃO PODE aceitar.")

    print("\n--- Estado Pós-Serviço ---")
    print(taxi_eletrico)

    # Simular necessidade de recarga
    if taxi_eletrico.precisa_recarregar(limiar_percentagem=0.85): # Limiar alto para forçar
        print(f"Taxi {taxi_eletrico.id_veiculo} precisa de recarregar.")
        taxi_eletrico.iniciar_carregamento()
        print(taxi_eletrico)
        
        # Simular tempo de carregamento (na simulação real, isto demoraria tempo)
        taxi_eletrico.terminar_carregamento()
        print(taxi_eletrico)