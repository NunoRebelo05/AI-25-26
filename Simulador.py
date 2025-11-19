import random
import time
from datetime import datetime, timedelta

from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao, EstadoVeiculo
from Pedido import Pedido, PrioridadePedido, EstadoPedido
from Gestor import GestorDeFrota

class Simulador:
    def __init__(self, gestor: GestorDeFrota, hora_inicio: datetime, 
                 duracao_sim_horas: int,
                 horas_ponta: list = None,        
                 prob_pedido: float = 0.15,        
                 limiar_recarga: float = 0.25,
                 gui_interface = None):
        
        self.gestor = gestor
        self.grafo = gestor.grafo
        self.gui = gui_interface
        
        self.pedidos_gerados = [] 
        
        # Dicionário para gerir TODOS os movimentos
        self.movimentos_ativos = {} 

        self.hora_inicio = hora_inicio
        self.current_time = hora_inicio
        self.end_time = hora_inicio + timedelta(hours=duracao_sim_horas)
        self.time_step = timedelta(minutes=1) 
        
        # Configurações
        self.HORAS_DE_PONTA = horas_ponta if horas_ponta is not None else [8, 9, 17, 18]
        self.PROB_NOVO_PEDIDO = prob_pedido
        self.LIMIAR_RECARGA_ELETTRICO = limiar_recarga
        self.MULTIPLICADOR_TRANSITO = 1.75
        self.CORES_PEDIDOS = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0']
        
        self.status_descricoes = {}
        self.paused = False
        self.delay = 0.2

        print(f"Simulador iniciado ({self.hora_inicio} -> {self.end_time}).")

    def run(self):
        print("\n--- INÍCIO DA SIMULAÇÃO ---")
        while self.current_time <= self.end_time:
            
            while self.paused: time.sleep(0.1)

            if self.current_time.minute % 30 == 0:
                 if self._update_traffic() and self.gui:
                     self.gui.desenhar_mapa_base()

            self.step()
            
            if self.gui:
                self._atualizar_descricoes_gui()
                pedidos_ativos = [p for p in self.pedidos_gerados if p.estado in [EstadoPedido.PENDENTE, EstadoPedido.EM_CURSO]]
                self.gui.atualizar_estado(self.gestor.frota, pedidos_ativos, self.current_time, self.status_descricoes)
                time.sleep(self.delay)

            self.current_time += self.time_step
            
        print("Simulação Concluída.")
        return self.print_summary()

    def toggle_pause(self):
        self.paused = not self.paused
        return self.paused

    def set_delay(self, delay):
        self.delay = delay

    def step(self):
        self._generate_new_request()
        self._processar_movimentos()
        self._manage_idle_taxis()

    def _generate_new_request(self):
        if random.random() < self.PROB_NOVO_PEDIDO:
            n_validos = list(self.grafo.nos.keys())
            if len(n_validos) < 2: return
            
            origem, destino = random.sample(n_validos, 2)
            
            novo_pedido = Pedido(
                origem=origem, destino=destino, num_passageiros=random.randint(1, 4),
                pref_ambiental=random.choice([True, False]), hora_criacao=self.current_time,
                prioridade=random.choice(list(PrioridadePedido))
            )
            novo_pedido.cor_mapa = random.choice(self.CORES_PEDIDOS)
            
            # print(f"TEMPO: {self.current_time} - NOVO PEDIDO {novo_pedido.id_pedido} ({origem} -> {destino})")
            self.pedidos_gerados.append(novo_pedido)
            
            taxi, custo, caminhos = self.gestor.decidir_alocacao(novo_pedido)
            
            if taxi:
                (c_pickup, c_viagem) = caminhos
                t_pickup = self.gestor._get_tempo_caminho(c_pickup)
                novo_pedido.alocar(taxi.id_veiculo, self.current_time + timedelta(minutes=t_pickup))
                taxi.alocar_para_servico()
                
                self._iniciar_movimento(taxi, c_pickup, "PICKUP", novo_pedido, c_viagem)
                print(f"TEMPO: {self.current_time} - Pedido {novo_pedido.id_pedido} alocado a {taxi.id_veiculo}")
            else:
                novo_pedido.rejeitar()

    def _iniciar_movimento(self, taxi, caminho, tipo, pedido=None, proximo_caminho=None):
        if not caminho or len(caminho) < 2:
            tempo_prox = 0
            prox_no_idx = 0
        else:
            prox_no_idx = 1
            d, tempo_prox = self.grafo.get_custo_aresta(caminho[0], caminho[1])
            if d == float('inf'):
                print(f"AVISO: Aresta inválida {caminho[0]}->{caminho[1]}. Movimento abortado.")
                return

        self.movimentos_ativos[taxi.id_veiculo] = {
            'taxi': taxi, 'pedido': pedido, 'tipo': tipo, 'caminho': caminho,
            'idx_prox_no': prox_no_idx, 'tempo_restante_aresta': tempo_prox,
            'proximo_caminho': proximo_caminho 
        }

    def _processar_movimentos(self):
        ids_taxis = list(self.movimentos_ativos.keys())
        for tid in ids_taxis:
            mov = self.movimentos_ativos[tid]
            taxi = mov['taxi']
            mov['tempo_restante_aresta'] -= 1
            
            if mov['tempo_restante_aresta'] <= 0:
                if mov['idx_prox_no'] < len(mov['caminho']):
                    destino_imediato = mov['caminho'][mov['idx_prox_no']]
                    dist, _ = self.grafo.get_custo_aresta(taxi.localizacao_atual, destino_imediato)
                    
                    if dist == float('inf'):
                        del self.movimentos_ativos[tid]
                        continue

                    taxi.mover_e_consumir(dist, destino_imediato)
                    mov['idx_prox_no'] += 1
                    
                    if mov['idx_prox_no'] < len(mov['caminho']):
                        prox = mov['caminho'][mov['idx_prox_no']]
                        _, t_prox = self.grafo.get_custo_aresta(taxi.localizacao_atual, prox)
                        mov['tempo_restante_aresta'] = t_prox
                    else:
                        self._concluir_segmento(mov)
                else:
                    self._concluir_segmento(mov)

    def _concluir_segmento(self, mov):
        # Recupera as variáveis com segurança
        taxi = mov['taxi']
        tipo = mov['tipo']
        pedido = mov.get('pedido') # Usa .get() para evitar erro se não existir
        
        if tipo == "PICKUP":
            # print(f"TEMPO: {self.current_time} - {taxi.id_veiculo} chegou ao cliente.")
            self._iniciar_movimento(taxi, mov['proximo_caminho'], "VIAGEM", pedido)
            
        elif tipo == "VIAGEM":
            # print(f"TEMPO: {self.current_time} - {taxi.id_veiculo} entregou cliente.")
            taxi.libertar_no_destino(taxi.localizacao_atual)
            if pedido: pedido.concluir()
            del self.movimentos_ativos[taxi.id_veiculo]
            
        elif tipo in ["A_CARREGAR", "A_ABASTECER"]:
            msg = "a carregar" if tipo == "A_CARREGAR" else "a abastecer"
            print(f"TEMPO: {self.current_time} - {taxi.id_veiculo} chegou a {taxi.localizacao_atual}. {msg}...")
            taxi.iniciar_carregamento()
            t_carga = 45 if taxi.tipo == TipoMotorizacao.ELETRICO else 10
            
            # --- CORREÇÃO AQUI: Adicionado 'pedido': None ---
            self.movimentos_ativos[taxi.id_veiculo] = {
                'taxi': taxi, 
                'tipo': "EM_CARGA", 
                'caminho': [], 
                'idx_prox_no': 0, 
                'tempo_restante_aresta': t_carga,
                'pedido': None # Evita o KeyError quando este segmento terminar
            }
            
        elif tipo == "EM_CARGA":
            print(f"TEMPO: {self.current_time} - {taxi.id_veiculo} pronto (100%).")
            taxi.terminar_carregamento()
            del self.movimentos_ativos[taxi.id_veiculo]

    def _manage_idle_taxis(self):
        for taxi in self.gestor.frota.values():
            # Verifica se está LIVRE e se não está já num movimento
            if taxi.estado == EstadoVeiculo.LIVRE and taxi.id_veiculo not in self.movimentos_ativos:
                
                # Verifica necessidade de energia (Elétrico ou Combustão)
                if taxi.precisa_recarregar(self.LIMIAR_RECARGA_ELETTRICO):
                    
                    estacao, caminho = self._find_nearest_charger(taxi.localizacao_atual)
                    
                    if estacao:
                        # Verifica se tem autonomia para chegar lá
                        dist_ate = self.gestor._get_dist_caminho(caminho)
                        if taxi.autonomia_atual >= dist_ate:
                            acao = "A_CARREGAR" if taxi.tipo == TipoMotorizacao.ELETRICO else "A_ABASTECER"
                            msg = "Bateria fraca" if taxi.tipo == TipoMotorizacao.ELETRICO else "Combustível baixo"
                            print(f"TEMPO: {self.current_time} - {taxi.id_veiculo} ({msg}). A ir para {estacao}...")
                            self._iniciar_movimento(taxi, caminho, acao)
                        else:
                            print(f"ALERTA: {taxi.id_veiculo} sem autonomia para chegar à estação!")
                            taxi.estado = EstadoVeiculo.EM_FALHA

    def _find_nearest_charger(self, origem):
        estacoes = [n for n, d in self.grafo.nos.items() if d.get('pode_carregar')]
        best_st, best_path, min_t = None, None, float('inf')
        for st in estacoes:
            path, t = self.gestor.get_caminho(origem, st)
            if path and t < min_t:
                min_t, best_st, best_path = t, st, path
        return best_st, best_path

    def _update_traffic(self):
        hora = self.current_time.hour
        is_ponta = hora in self.HORAS_DE_PONTA
        prob_transito = 0.6 if is_ponta else 0.1
        max_mult = self.MULTIPLICADOR_TRANSITO if is_ponta else 1.2

        mudou_algo = False
        for origem, destino in list(self.grafo.condicoes_transito.keys()):
            if random.random() < 0.3:
                novo_mult = 1.0
                if random.random() < prob_transito:
                    novo_mult = 1.0 + random.random() * (max_mult - 1.0)
                novo_mult = round(novo_mult, 1)
                
                if self.grafo.condicoes_transito.get((origem, destino), 1.0) != novo_mult:
                    self.grafo.atualizar_transito(origem, destino, novo_mult)
                    mudou_algo = True
        return mudou_algo

    def _atualizar_descricoes_gui(self):
        self.status_descricoes.clear()
        for t_id, taxi in self.gestor.frota.items():
            if taxi.estado == EstadoVeiculo.EM_FALHA:
                 self.status_descricoes[t_id] = "FALHA: SEM ENERGIA"
                 continue

            if t_id in self.movimentos_ativos:
                mov = self.movimentos_ativos[t_id]
                tipo = mov['tipo']
                if tipo == "PICKUP": txt = f"A ir buscar ({mov['pedido'].origem})"
                elif tipo == "VIAGEM": txt = f"A levar ({mov['pedido'].destino})"
                elif tipo in ["A_CARREGAR", "A_ABASTECER"]: txt = f"A ir abastecer"
                elif tipo == "EM_CARGA": txt = f"A abastecer ({mov['tempo_restante_aresta']}m)"
                else: txt = tipo
                
                if tipo != "EM_CARGA" and mov['idx_prox_no'] < len(mov['caminho']):
                     prox = mov['caminho'][mov['idx_prox_no']]
                     txt += f"\n-> {prox}"
            else:
                txt = f"Livre em {taxi.localizacao_atual}"
            self.status_descricoes[t_id] = txt

    def print_summary(self):
        concluidos = [p for p in self.pedidos_gerados if p.estado == EstadoPedido.CONCLUIDO]
        rejeitados = [p for p in self.pedidos_gerados if p.estado == EstadoPedido.REJEITADO]
        total = len(self.pedidos_gerados)
        taxa = (len(rejeitados)/total)*100 if total > 0 else 0
        wait = sum([p.get_tempo_espera_total() for p in concluidos])/len(concluidos) if concluidos else 0
        print("\n" + "="*40)
        print(f"Total: {total} | OK: {len(concluidos)} | NOK: {len(rejeitados)} ({taxa:.1f}%)")
        print(f"Espera: {wait:.2f} min")
        return {'total': total, 'rejeitados': len(rejeitados)}