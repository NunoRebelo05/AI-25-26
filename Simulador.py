import random
import time
from datetime import datetime, timedelta

# Importar todas as nossas classes
from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao, EstadoVeiculo
from Pedido import Pedido, PrioridadePedido, EstadoPedido
from Gestor import GestorDeFrota

# --- Constantes da Simulação ---
PROB_NOVO_PEDIDO_POR_MINUTO = 0.15
LIMIAR_RECARGA_ELETTRICO = 0.25

class Simulador:
    """
    Orquestra a simulação dinâmica (versão simplificada, sem visualização).
    """
    
    def __init__(self, gestor: GestorDeFrota, hora_inicio: datetime, 
                 duracao_sim_horas: int):
        
        self.gestor = gestor
        self.grafo = gestor.grafo
        
        self.active_services = []
        self.active_charging = []
        self.pedidos_gerados = [] 

        self.hora_inicio = hora_inicio
        self.current_time = hora_inicio
        self.end_time = hora_inicio + timedelta(hours=duracao_sim_horas)
        self.time_step = timedelta(minutes=1) 
        
        # Constantes de trânsito
        self.HORAS_DE_PONTA = [8, 9, 17, 18]
        self.MULTIPLICADOR_TRANSITO = 1.75
        
        print(f"Simulador iniciado. A correr de {hora_inicio} até {self.end_time}.")

    def run(self):
        """Corre a simulação inteira, minuto a minuto."""
        while self.current_time <= self.end_time:
            
            if self.current_time.minute == 0:
                 print(f"--- {self.current_time} ---")
                 self._update_traffic()
                 
            self.step()
            self.current_time += self.time_step
            
        print("\nSimulação Concluída. A gerar relatório final...")
        
        # --- ALTERAÇÃO AQUI ---
        # Devolve os resultados para o main.py
        return self.print_summary()

    def step(self):
        """Executa um único "tick" (1 minuto) da simulação."""
        self._generate_new_request()
        self._update_active_services()
        self._update_charging_taxis()
        self._manage_idle_taxis()

    def _generate_new_request(self):
        if random.random() < PROB_NOVO_PEDIDO_POR_MINUTO:
            n_recolha = [n for n, d in self.grafo.nos.items() if d.get('tipo') != 'EstacaoRecarga']
            if len(n_recolha) < 2: return 
            
            origem, destino = random.sample(n_recolha, 2)
            
            novo_pedido = Pedido(
                origem=origem,
                destino=destino,
                num_passageiros=random.randint(1, 4),
                pref_ambiental=random.choice([True, False]),
                hora_criacao = self.current_time,
                prioridade=random.choices(
                    [p for p in PrioridadePedido], [0.6, 0.3, 0.1]
                )[0]
            )
            
            print(f"TEMPO: {self.current_time} - NOVO PEDIDO {novo_pedido.id_pedido} ({origem} -> {destino})")
            self.pedidos_gerados.append(novo_pedido)
            
            taxi_escolhido, custo, caminhos = self.gestor.decidir_alocacao(novo_pedido)
            
            if taxi_escolhido:
                (caminho_pickup, caminho_viagem) = caminhos
                
                tempo_pickup = self.gestor._get_tempo_caminho(caminho_pickup)
                tempo_viagem = self.gestor._get_tempo_caminho(caminho_viagem)
                dist_pickup = self.gestor._get_dist_caminho(caminho_pickup)
                dist_viagem = self.gestor._get_dist_caminho(caminho_viagem)
                
                hora_recolha = self.current_time + timedelta(minutes=tempo_pickup)
                novo_pedido.alocar(taxi_escolhido.id_veiculo, hora_recolha)
                taxi_escolhido.alocar_para_servico()
                
                servico = {
                    'taxi': taxi_escolhido,
                    'pedido': novo_pedido,
                    'estado_servico': 'PICKUP',
                    'tempo_restante_etapa': tempo_pickup,
                    'dist_etapa_total': dist_pickup,
                    'etapa_viagem': (tempo_viagem, dist_viagem) 
                }
                self.active_services.append(servico)
            else:
                novo_pedido.rejeitar()

    def _update_active_services(self):
        for servico in self.active_services[:]:
            servico['tempo_restante_etapa'] -= 1 
            
            if servico['tempo_restante_etapa'] <= 0:
                taxi = servico['taxi']
                pedido = servico['pedido']
                
                if servico['estado_servico'] == 'PICKUP':
                    print(f"TEMPO: {self.current_time} - Taxi {taxi.id_veiculo} recolheu Pedido {pedido.id_pedido}")
                    taxi.mover_e_consumir(servico['dist_etapa_total'], pedido.origem)
                    servico['estado_servico'] = 'VIAGEM'
                    servico['tempo_restante_etapa'] = servico['etapa_viagem'][0]
                    servico['dist_etapa_total'] = servico['etapa_viagem'][1]
                    
                elif servico['estado_servico'] == 'VIAGEM':
                    print(f"TEMPO: {self.current_time} - Taxi {taxi.id_veiculo} concluiu Pedido {pedido.id_pedido}")
                    taxi.mover_e_consumir(servico['dist_etapa_total'], pedido.destino)
                    taxi.libertar_no_destino(pedido.destino)
                    pedido.concluir()
                    self.active_services.remove(servico)
            
    def _manage_idle_taxis(self):
        for taxi in self.gestor.frota.values():
            if taxi.estado == EstadoVeiculo.LIVRE:
                if taxi.tipo == TipoMotorizacao.ELETRICO and \
                   taxi.precisa_recarregar(LIMIAR_RECARGA_ELETTRICO):
                    
                    estacao, caminho = self._find_nearest_station(taxi.localizacao_atual, 'EstacaoRecarga')
                    
                    if estacao:
                        print(f"TEMPO: {self.current_time} - Taxi {taxi.id_veiculo} (elétrico) está baixo de bateria. A ir para {estacao} carregar.")
                        tempo_viagem = self.gestor._get_tempo_caminho(caminho)
                        dist_viagem = self.gestor._get_dist_caminho(caminho)
                        taxi.iniciar_carregamento()
                        carga = {
                            'taxi': taxi,
                            'destino_estacao': estacao,
                            'tempo_ate_estacao': tempo_viagem,
                            'dist_viagem': dist_viagem,
                            'tempo_restante_carga': -1 
                        }
                        self.active_charging.append(carga)

    def _update_charging_taxis(self):
        TEMPO_RECARGA_ELETRICO_MIN = 45
        
        for carga in self.active_charging[:]:
            taxi = carga['taxi']
            
            if carga['tempo_restante_carga'] == -1: 
                carga['tempo_ate_estacao'] -= 1
                if carga['tempo_ate_estacao'] <= 0:
                    taxi.mover_e_consumir(carga['dist_viagem'], carga['destino_estacao'])
                    print(f"TEMPO: {self.current_time} - Taxi {taxi.id_veiculo} chegou a {carga['destino_estacao']}. A carregar...")
                    carga['tempo_restante_carga'] = TEMPO_RECARGA_ELETRICO_MIN
            else:
                carga['tempo_restante_carga'] -= 1
                if carga['tempo_restante_carga'] <= 0:
                    taxi.terminar_carregamento()
                    print(f"TEMPO: {self.current_time} - Taxi {taxi.id_veiculo} terminou carregamento.")
                    self.active_charging.remove(carga)

    def _find_nearest_station(self, origem: str, tipo_estacao: str) -> (str, list):
        estacoes = [n for n, d in self.grafo.nos.items() if d.get('tipo') == tipo_estacao]
        if not estacoes:
            return None, None
            
        melhor_estacao = None
        melhor_caminho = None
        menor_tempo = float('inf')
        
        for estacao in estacoes:
            caminho, tempo = self.gestor.a_star_search(self.grafo, origem, estacao, 'tempo')
            if caminho and tempo < menor_tempo:
                menor_tempo = tempo
                melhor_estacao = estacao
                melhor_caminho = caminho
                
        return melhor_estacao, melhor_caminho

    def _update_traffic(self):
        """Simula mudanças de trânsito (Tarefa 6)."""
        hora_atual = self.current_time.hour
        
        multiplicador = self.MULTIPLICADOR_TRANSITO if hora_atual in self.HORAS_DE_PONTA else 1.0
        
        primeira_aresta = list(self.grafo.condicoes_transito.keys())[0]
        if self.grafo.condicoes_transito[primeira_aresta] == multiplicador:
            return
            
        if multiplicador > 1.0:
            print(f"TEMPO: {self.current_time} - 🚦 HORA DE PONTA INICIADA.")
        else:
            print(f"TEMPO: {self.current_time} - 🚗 Trânsito normalizado.")

        for aresta in self.grafo.condicoes_transito:
            self.grafo.atualizar_transito(aresta[0], aresta[1], multiplicador)

    def print_summary(self):
        """Imprime as métricas de avaliação (Tarefa 5) e retorna os resultados."""
        
        concluidos = [p for p in self.pedidos_gerados if p.estado == EstadoPedido.CONCLUIDO]
        rejeitados = [p for p in self.pedidos_gerados if p.estado == EstadoPedido.REJEITADO]
        
        total_pedidos = len(self.pedidos_gerados)
        
        # --- Valores Padrão ---
        taxa_rejeicao = 0.0
        tempo_medio_espera = 0.0

        if total_pedidos == 0:
            print("\nSimulação terminada. Nenhum pedido foi gerado.")
            # Retorna um dicionário vazio/default
            return {
                "total_pedidos": 0, "concluidos": 0, "rejeitados": 0,
                "taxa_rejeicao": 0.0, "tempo_espera": 0.0
            }

        # --- Cálculos Seguros ---
        if total_pedidos > 0:
            taxa_rejeicao = (len(rejeitados) / total_pedidos) * 100
        
        if len(concluidos) > 0:
            tempos_espera = [p.get_tempo_espera_total() for p in concluidos]
            tempo_medio_espera = sum(tempos_espera) / len(concluidos)

        # --- Impressão (como antes) ---
        print("\n" + "="*40)
        print("--- 🏁 Relatório Final da Simulação 🏁 ---")
        print(f"Período Simulado: {self.end_time - self.hora_inicio} (HH:MM:SS)")
        
        print("\n### Métricas de Pedidos")
        print(f"Total Pedidos Gerados: {total_pedidos}")
        print(f"  - Concluídos: {len(concluidos)}")
        print(f"  - Rejeitados: {len(rejeitados)} ({taxa_rejeicao:.1f}%)")

        if concluidos:
            print(f"\nTempo Médio de Espera (Cliente): {tempo_medio_espera:.2f} minutos")
        
        print("\n### Métricas da Frota (Autonomia Restante)")
        for taxi in self.gestor.frota.values():
            print(f"  - Taxi {taxi.id_veiculo} ({taxi.tipo.name}): {taxi.autonomia_atual:.1f}/{taxi.autonomia_maxima:.1f} km")
        print("="*40)


        return {
            "total_pedidos": total_pedidos,
            "concluidos": len(concluidos),
            "rejeitados": len(rejeitados),
            "taxa_rejeicao": taxa_rejeicao,
            "tempo_espera": tempo_medio_espera
        }