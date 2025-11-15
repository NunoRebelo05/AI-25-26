import random
from datetime import datetime, timedelta

# Importar todas as nossas classes
from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao, EstadoVeiculo
from Pedido import Pedido, PrioridadePedido, EstadoPedido
from Gestor import GestorDeFrota

# --- Constantes da Simulação ---

# Probabilidade de um novo pedido chegar a cada "tick" (minuto)
# Ajustar este valor muda a "carga" do sistema
PROB_NOVO_PEDIDO_POR_MINUTO = 0.15 # 15% de chance a cada minuto

# Limiar para um táxi elétrico decidir ir carregar
LIMIAR_RECARGA_ELETTRICO = 0.25 # 25% de autonomia

# --- Constantes de Trânsito (Tarefa 6) ---
HORAS_DE_PONTA = [8, 9, 17, 18] # 8h, 9h, 17h, 18h
MULTIPLICADOR_TRANSITO = 1.75   # O trânsito fica 75% mais lento

class Simulador:
    """
    Orquestra a simulação dinâmica.
    Mantém o relógio, gera eventos (pedidos) e atualiza o estado
    do mundo (movimento dos táxis).
    """
    
    def __init__(self, gestor: GestorDeFrota, hora_inicio: datetime, duracao_sim_horas: int):
        self.gestor = gestor
        self.grafo = gestor.grafo
        
        # Controlo do Tempo
        self.hora_inicio = hora_inicio
        self.current_time = hora_inicio
        self.end_time = hora_inicio + timedelta(hours=duracao_sim_horas)
        self.time_step = timedelta(minutes=1) # Cada "tick" da simulação é 1 minuto
        
        # Listas para gerir o estado
        self.active_services = [] # Serviços em curso (táxis em movimento)
        self.active_charging = [] # Táxis a carregar
        
        # Métricas (para Tarefa 5)
        self.pedidos_gerados = []
        
        print(f"Simulador iniciado. A correr de {hora_inicio} até {self.end_time}.")

    def run(self):
        """Corre a simulação inteira, minuto a minuto."""
        while self.current_time <= self.end_time:
            self.step()
            self.current_time += self.time_step
            
            if self.current_time.minute == 0: # Imprime a hora a cada hora
                 print(f"--- {self.current_time} ---")
                 self._update_traffic()
                 
        self.print_summary()

    def step(self):
        """Executa um único "tick" (1 minuto) da simulação."""
        
        # 1. Gerar novos pedidos (aleatoriamente) 
        self._generate_new_request()
        
        # 2. Atualizar táxis em serviço (movimento) 
        self._update_active_services()
        
        # 3. Atualizar táxis a carregar 
        self._update_charging_taxis()
        
        # 4. Gerir táxis livres (ex: ir carregar) 
        self._manage_idle_taxis()
        

    def _generate_new_request(self):
        """Gera um novo pedido com base na probabilidade."""
        if random.random() < PROB_NOVO_PEDIDO_POR_MINUTO:
            # Lógica de criação de pedido aleatório
            
            # Escolher nós aleatórios (excluindo estações de recarga)
            n_recolha = [n for n, d in self.grafo.nos.items() if d.get('tipo') != 'EstacaoRecarga']
            if len(n_recolha) < 2: return # Grafo muito pequeno
            
            origem, destino = random.sample(n_recolha, 2)
            
            novo_pedido = Pedido(
                origem=origem,
                destino=destino,
                num_passageiros=random.randint(1, 4),
                pref_ambiental=random.choice([True, False]),
                prioridade=random.choices(
                    [p for p in PrioridadePedido], [0.6, 0.3, 0.1]
                )[0],
                hora_criacao = self.current_time
            )
            
            print(f"TEMPO: {self.current_time} - NOVO PEDIDO {novo_pedido.id_pedido} ({origem} -> {destino})")
            self.pedidos_gerados.append(novo_pedido)
            
            # Chamar o Gestor para DECIDIR
            taxi_escolhido, custo, caminhos = self.gestor.decidir_alocacao(novo_pedido)
            
            if taxi_escolhido:
                # O Simulador EXECUTA a decisão
                (caminho_pickup, caminho_viagem) = caminhos
                
                # Calcular tempos e distâncias dos caminhos
                tempo_pickup = self.gestor._get_tempo_caminho(caminho_pickup)
                tempo_viagem = self.gestor._get_tempo_caminho(caminho_viagem)
                dist_pickup = self.gestor._get_dist_caminho(caminho_pickup)
                dist_viagem = self.gestor._get_dist_caminho(caminho_viagem)
                
                # Alocar formalmente
                hora_recolha = self.current_time + timedelta(minutes=tempo_pickup)
                novo_pedido.alocar(taxi_escolhido.id_veiculo, hora_recolha)
                taxi_escolhido.alocar_para_servico()
                
                # Adicionar à lista de serviços ativos para o simulador gerir
                servico = {
                    'taxi': taxi_escolhido,
                    'pedido': novo_pedido,
                    'estado_servico': 'PICKUP', # Começa a ir buscar
                    'tempo_restante_etapa': tempo_pickup,
                    'dist_etapa_total': dist_pickup,
                    'etapa_viagem': (tempo_viagem, dist_viagem) # Guarda info da 2ª etapa
                }
                self.active_services.append(servico)
                
            else:
                # Nenhum táxi pôde ser alocado
                novo_pedido.rejeitar()

    def _update_active_services(self):
        """Atualiza todos os táxis que estão em serviço (PICKUP ou VIAGEM)."""
        
        # Iterar numa cópia, pois podemos modificar a lista
        for servico in self.active_services[:]:
            servico['tempo_restante_etapa'] -= 1 # 1 minuto de simulação
            
            if servico['tempo_restante_etapa'] <= 0:
                # A etapa (PICKUP ou VIAGEM) terminou
                taxi = servico['taxi']
                pedido = servico['pedido']
                
                if servico['estado_servico'] == 'PICKUP':
                    # Terminou o PICKUP, começou a VIAGEM
                    print(f"TEMPO: {self.current_time} - Taxi {taxi.id_veiculo} recolheu Pedido {pedido.id_pedido}")
                    
                    # Consumir autonomia e mover
                    taxi.mover_e_consumir(servico['dist_etapa_total'], pedido.origem)
                    
                    # Configurar próxima etapa (VIAGEM)
                    servico['estado_servico'] = 'VIAGEM'
                    servico['tempo_restante_etapa'] = servico['etapa_viagem'][0]
                    servico['dist_etapa_total'] = servico['etapa_viagem'][1]
                    
                elif servico['estado_servico'] == 'VIAGEM':
                    # Terminou a VIAGEM (serviço concluído)
                    print(f"TEMPO: {self.current_time} - Taxi {taxi.id_veiculo} concluiu Pedido {pedido.id_pedido}")
                    
                    # Consumir autonomia e mover
                    taxi.mover_e_consumir(servico['dist_etapa_total'], pedido.destino)
                    
                    # Libertar táxi e concluir pedido
                    taxi.libertar_no_destino(pedido.destino)
                    pedido.concluir()
                    
                    # Remover da lista de serviços ativos
                    self.active_services.remove(servico)
            
    def _manage_idle_taxis(self):
        """Verifica táxis LIVRES e decide se devem ir carregar."""
        for taxi in self.gestor.frota.values():
            if taxi.estado == EstadoVeiculo.LIVRE:
                
                # Aplicável apenas a elétricos que precisam de carregar 
                if taxi.tipo == TipoMotorizacao.ELETRICO and \
                   taxi.precisa_recarregar(LIMIAR_RECARGA_ELETTRICO):
                    
                    # Encontrar a estação de recarga mais próxima
                    estacao, caminho = self._find_nearest_station(taxi.localizacao_atual, 'EstacaoRecarga')
                    
                    if estacao:
                        print(f"TEMPO: {self.current_time} - Taxi {taxi.id_veiculo} (elétrico) está baixo de bateria. A ir para {estacao} carregar.")
                        
                        tempo_viagem = self.gestor._get_tempo_caminho(caminho)
                        dist_viagem = self.gestor._get_dist_caminho(caminho)
                        
                        # Alocar táxi para "carregamento"
                        taxi.iniciar_carregamento() # Muda estado para A_CARREGAR
                        
                        # Adicionar à lista de carregamento
                        carga = {
                            'taxi': taxi,
                            'destino_estacao': estacao,
                            'tempo_ate_estacao': tempo_viagem,
                            'dist_viagem': dist_viagem,
                            'tempo_restante_carga': -1 # -1 = em trânsito
                        }
                        self.active_charging.append(carga)

    def _update_charging_taxis(self):
        """Atualiza táxis a caminho ou em estações de recarga."""
        # [cite: 27] Tempo de recarga vs. tempo de reabastecimento
        TEMPO_RECARGA_ELETRICO_MIN = 45 #
        
        for carga in self.active_charging[:]:
            taxi = carga['taxi']
            
            if carga['tempo_restante_carga'] == -1: # Em trânsito para a estação
                carga['tempo_ate_estacao'] -= 1
                if carga['tempo_ate_estacao'] <= 0:
                    # Chegou à estação
                    taxi.mover_e_consumir(carga['dist_viagem'], carga['destino_estacao'])
                    print(f"TEMPO: {self.current_time} - Taxi {taxi.id_veiculo} chegou a {carga['destino_estacao']}. A carregar...")
                    carga['tempo_restante_carga'] = TEMPO_RECARGA_ELETRICO_MIN
            else:
                # A carregar
                carga['tempo_restante_carga'] -= 1
                if carga['tempo_restante_carga'] <= 0:
                    # Carregamento concluído
                    taxi.terminar_carregamento() # Enche autonomia e fica LIVRE
                    print(f"TEMPO: {self.current_time} - Taxi {taxi.id_veiculo} terminou carregamento.")
                    self.active_charging.remove(carga)

    def _find_nearest_station(self, origem: str, tipo_estacao: str) -> (str, list):
        """Encontra o nó do tipo 'tipo_estacao' mais próximo de 'origem'."""
        
        # Encontra todos os nós do tipo certo
        estacoes = [n for n, d in self.grafo.nos.items() if d.get('tipo') == tipo_estacao]
        if not estacoes:
            return None, None
            
        melhor_estacao = None
        melhor_caminho = None
        menor_tempo = float('inf')
        
        # A* para cada estação para encontrar a mais próxima em TEMPO
        for estacao in estacoes:
            caminho, tempo = self.gestor.a_star_search(self.grafo, origem, estacao, 'tempo')
            if caminho and tempo < menor_tempo:
                menor_tempo = tempo
                melhor_estacao = estacao
                melhor_caminho = caminho
                
        return melhor_estacao, melhor_caminho

    # Em Simulador.py

    def _update_traffic(self):
        """
        Simula mudanças de trânsito (Tarefa 6).
        É chamado a cada hora (quando o minuto == 0).
        """
        
        hora_atual = self.current_time.hour
        
        if hora_atual in HORAS_DE_PONTA:
            # É HORA DE PONTA: Aumentar o trânsito
            print(f"TEMPO: {self.current_time} - 🚦 HORA DE PONTA INICIADA.")
            
            # Itera por todas as arestas e aplica o multiplicador
            for origem, destinos in self.grafo.arestas.items():
                for destino in destinos:
                    # Verifica se o trânsito já está aplicado
                    if self.grafo.condicoes_transito.get((origem, destino), 1.0) == 1.0:
                        self.grafo.atualizar_transito(origem, destino, MULTIPLICADOR_TRANSITO)
                        
        else:
            # NÃO É HORA DE PONTA: Normalizar o trânsito
   
            foi_normalizado_algo = False
            
            for origem, destinos in self.grafo.arestas.items():
                for destino in destinos:
                    # Verifica se o trânsito estava aplicado
                    if self.grafo.condicoes_transito.get((origem, destino), 1.0) > 1.0:
                        self.grafo.atualizar_transito(origem, destino, 1.0)
                        foi_normalizado_algo = True # Marcamos que *algo* mudou
            
            
            if foi_normalizado_algo:
                 print(f"TEMPO: {self.current_time} - 🚗 Trânsito normalizado.")

    def print_summary(self):
        """Imprime as métricas de avaliação (Tarefa 5)."""
        
        concluidos = [p for p in self.pedidos_gerados if p.estado == EstadoPedido.CONCLUIDO]
        rejeitados = [p for p in self.pedidos_gerados if p.estado == EstadoPedido.REJEITADO]
        pendentes = [p for p in self.pedidos_gerados if p.estado == EstadoPedido.PENDENTE]
        
        total_pedidos = len(self.pedidos_gerados)
        if total_pedidos == 0:
            print("\nSimulação terminada. Nenhum pedido foi gerado.")
            return

        print("\n--- 🏁 Relatório Final da Simulação 🏁 ---")
        print(f"Período Simulado: {self.end_time - self.hora_inicio} (HH:MM:SS)")
        
        # --- Métricas de Pedidos ---
        print("\n### Métricas de Pedidos")
        taxa_rejeicao = (len(rejeitados) / total_pedidos) * 100
        print(f"Total Pedidos Gerados: {total_pedidos}")
        print(f"  - Concluídos: {len(concluidos)}")
        print(f"  - Rejeitados: {len(rejeitados)} ({taxa_rejeicao:.1f}%)")
        print(f"  - Pendentes (não alocados no fim): {len(pendentes)}")

        # --- Métricas de Tempo (Satisfação)  ---
        if concluidos:
            tempos_espera = [p.get_tempo_espera_total() for p in concluidos]
            tempo_medio_espera = sum(tempos_espera) / len(tempos_espera)
            print(f"\nTempo Médio de Espera (Cliente): {tempo_medio_espera:.2f} minutos")
        
        # --- Métricas da Frota (Eficiência)  ---
        print("\n### Métricas da Frota")
        dist_total_frota = 0
        dist_sem_pax = 0
        
        for taxi in self.gestor.frota.values():
            dist_percorrida = taxi.autonomia_maxima - taxi.autonomia_atual # Assumindo que começam cheios
            if dist_percorrida < 0: dist_percorrida = 0 # Caso tenha recarregado
            # (Nota: métrica de km real seria mais complexa)
            print(f"  - Taxi {taxi.id_veiculo} ({taxi.tipo.name}): {taxi.autonomia_atual:.1f}/{taxi.autonomia_maxima:.1f} km restantes")
        
        # (Para Km sem passageiros, teríamos que somar dist_pickup
        # em cada serviço concluído)
        # print(f"Km Totais (aprox): ...")
        # print(f"Km sem Passageiros (aprox): ...")