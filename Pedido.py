import uuid
from enum import Enum, auto
from datetime import datetime

# Enum para o estado do pedido (útil para a simulação)
class EstadoPedido(Enum):
    PENDENTE = auto()       # Acabou de chegar
    EM_CURSO = auto()       # Um táxi foi alocado
    CONCLUIDO = auto()      # O passageiro chegou ao destino
    REJEITADO = auto()      # Não foi possível alocar (ex: falta de táxis)

# Enum para a prioridade do pedido
class PrioridadePedido(Enum):
    BAIXA = 1
    NORMAL = 2
    URGENTE = 3             # Ex: Clientes premium ou urgências

class Pedido:
    """
    Representa um único pedido de transporte feito por um cliente.
    """
    
    def __init__(self, 
                 origem: str, 
                 destino: str, 
                 num_passageiros: int, 
                 pref_ambiental: bool,
                 horario_pretendido: datetime = None,
                 prioridade: PrioridadePedido = PrioridadePedido.NORMAL):

        # Informação do Pedido (baseado na fonte 13)
        self.id_pedido = str(uuid.uuid4().hex[:8]) # Um ID único mais curto
        self.origem = origem
        self.destino = destino
        self.num_passageiros = num_passageiros
        self.pref_ambiental = pref_ambiental
        self.prioridade = prioridade
        
        # Se o horário for None, assume-se que é um pedido imediato
        self.horario_pretendido = horario_pretendido if horario_pretendido else datetime.now()
        
        # Gestão de Estado e Métricas
        self.estado = EstadoPedido.PENDENTE
        self.id_veiculo_alocado = None
        self.hora_criacao = datetime.now()
        self.hora_recolha_estimada = None
        self.hora_conclusao = None

    def __repr__(self):
        """Representação textual do objeto para debugging."""
        return (f"Pedido(ID: {self.id_pedido}, De: {self.origem}, Para: {self.destino}, "
                f"Pax: {self.num_passageiros}, Estado: {self.estado.name}, "
                f"Prioridade: {self.prioridade.name})")

    # --- Métodos de Atualização de Estado ---

    def alocar(self, id_veiculo: str, hora_recolha_estimada: datetime):
        """Aloca um veículo ao pedido."""
        if self.estado == EstadoPedido.PENDENTE:
            self.estado = EstadoPedido.EM_CURSO
            self.id_veiculo_alocado = id_veiculo
            self.hora_recolha_estimada = hora_recolha_estimada
            print(f"INFO: Pedido {self.id_pedido} alocado ao Taxi {id_veiculo}.")
        else:
            print(f"AVISO: Tentativa de alocar pedido {self.id_pedido} que não está PENDENTE.")

    def concluir(self):
        """Marca o pedido como concluído."""
        self.estado = EstadoPedido.CONCLUIDO
        self.hora_conclusao = datetime.now()
        print(f"INFO: Pedido {self.id_pedido} concluído.")

    def rejeitar(self):
        """Marca o pedido como rejeitado (não foi possível atender)."""
        self.estado = EstadoPedido.REJEITADO
        print(f"INFO: Pedido {self.id_pedido} rejeitado.")
        
    def get_tempo_espera_total(self) -> float:
        """
        Calcula o tempo total de espera do cliente, desde a criação até à recolha.
        Retorna 0 se ainda não foi recolhido.
        """
        if self.hora_recolha_estimada:
            delta = self.hora_recolha_estimada - self.hora_criacao
            return delta.total_seconds() / 60.0 # Em minutos
        return 0.0


# --- Exemplo de utilização (para testar o ficheiro) ---
if __name__ == "__main__":

    print("--- Criar Pedidos ---")
    
    # Pedido 1: Imediato, normal, sem preferência ambiental
    pedido_1 = Pedido(
        origem="Centro",
        destino="Aeroporto",
        num_passageiros=2,
        pref_ambiental=False
    )
    
    # Pedido 2: Imediato, urgente, com preferência ambiental [cite: 13, 28]
    pedido_2 = Pedido(
        origem="Hospital",
        destino="Estacao_CP",
        num_passageiros=1,
        pref_ambiental=True,
        prioridade=PrioridadePedido.URGENTE
    )
    
    # Pedido 3: Agendado para daqui a 2 horas
    from datetime import timedelta
    hora_agendada = datetime.now() + timedelta(hours=2)
    pedido_3 = Pedido(
        origem="Universidade",
        destino="Centro",
        num_passageiros=4,
        pref_ambiental=True,
        horario_pretendido=hora_agendada
    )

    print(pedido_1)
    print(pedido_2)
    print(pedido_3)
    
    print("\n--- Simular Alocação ---")
    print(f"Estado inicial P1: {pedido_1.estado.name}")
    
    # Simular que um táxi "EV01" foi alocado e demora 5 minutos a chegar
    hora_recolha_est = datetime.now() + timedelta(minutes=5)
    pedido_1.alocar("EV01", hora_recolha_est)
    
    print(f"Estado P1 pós-alocação: {pedido_1.estado.name}")
    print(f"Tempo de espera (min): {pedido_1.get_tempo_espera_total():.2f}")
    
    pedido_1.concluir()
    print(f"Estado P1 pós-conclusão: {pedido_1.estado.name}")