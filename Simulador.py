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
        
        # Listas de Estado
        self.pedidos_gerados = [] 
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
        self.delay = 0.2 if self.gui else 0.0 # Rápido se não houver GUI

        print(f"Simulador iniciado ({self.hora_inicio} -> {self.end_time}).")

    def run(self):
        print(f"\n--- INÍCIO DA SIMULAÇÃO ({'Modo Visual' if self.gui else 'Modo Rápido'}) ---")
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
        
        # 1. Tentar esvaziar a fila de espera (Prioritário)
        self._processar_fila_espera()
        
        # 2. Só depois é que vemos se os livres vão carregar
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
            
            print(f"TEMPO: {self.current_time} - NOVO PEDIDO {novo_pedido.id_pedido} ({origem} -> {destino})")
            self.pedidos_gerados.append(novo_pedido)
            
            # Tenta alocar imediatamente
            self._tenta_alocar_pedido(novo_pedido)

    def _processar_fila_espera(self):
        """Gere a fila: remove expirados e tenta alocar pendentes."""
        
        # AUMENTADO PARA 60 MINUTOS (para lidar com trânsito)
        MAX_ESPERA = 60 
        
        # 1. Verificar Timeouts
        for pedido in self.gestor.pedidos_pendentes[:]:
            tempo_passado = (self.current_time - pedido.hora_criacao).total_seconds() / 60
            
            if tempo_passado > MAX_ESPERA:
                print(f"TEMPO: {self.current_time} - Pedido {pedido.id_pedido} EXPIROU (esperou {tempo_passado:.0f} min). Rejeitado.")
                pedido.rejeitar()
                self.gestor.pedidos_pendentes.remove(pedido)

        # 2. Tentar alocar (Ordenado por Prioridade DESC, depois Tempo Espera DESC)
        # Isto garante que urgentes e antigos vão primeiro
        fila_ordenada = sorted(self.gestor.pedidos_pendentes, 
                               key=lambda p: (p.prioridade.value, p.hora_criacao), 
                               reverse=True)

        for pedido in fila_ordenada:
            if self._tenta_alocar_pedido(pedido, vindo_da_fila=True):
                # Se alocou, o loop continua para o próximo, 
                # mas a lista original no Gestor já foi atualizada pelo método _tenta_alocar
                pass

    def _tenta_alocar_pedido(self, pedido, vindo_da_fila=False):
        """Tenta alocar um pedido. Retorna True se sucesso."""
        taxi, custo, caminhos = self.gestor.decidir_alocacao(pedido)
        
        if taxi:
            if vindo_da_fila:
                self.gestor.pedidos_pendentes.remove(pedido)
                print(f"TEMPO: {self.current_time} - Pedido {pedido.id_pedido} saiu da fila -> {taxi.id_veiculo}")
            else:
                print(f"TEMPO: {self.current_time} - Pedido {pedido.id_pedido} alocado a {taxi.id_veiculo}")

            c_pickup, c_viagem = caminhos
            t_pickup = self.gestor._get_tempo_caminho(c_pickup)
            
            novo_horario = self.current_time + timedelta(minutes=t_pickup)
            pedido.alocar(taxi.id_veiculo, novo_horario)
            taxi.alocar_para_servico()
            
            self._iniciar_movimento(taxi, c_pickup, "PICKUP", pedido, c_viagem)
            return True
        else:
            if not vindo_da_fila:
                if pedido not in self.gestor.pedidos_pendentes:
                    self.gestor.pedidos_pendentes.append(pedido)
                    print(f"INFO: Pedido {pedido.id_pedido} entrou na FILA DE ESPERA.")
            return False

    def _iniciar_movimento(self, taxi, caminho, tipo, pedido=None, proximo_caminho=None):
        if not caminho or len(caminho) < 2:
            tempo_prox, prox_no_idx = 0, 0
        else:
            prox_no_idx = 1
            d, tempo_prox = self.grafo.get_custo_aresta(caminho[0], caminho[1])
            if d == float('inf'): return
        
        self.movimentos_ativos[taxi.id_veiculo] = {
            'taxi': taxi, 'pedido': pedido, 'tipo': tipo, 'caminho': caminho,
            'idx_prox_no': prox_no_idx, 'tempo_restante_aresta': tempo_prox,
            'proximo_caminho': proximo_caminho 
        }

    def _processar_movimentos(self):
        ids = list(self.movimentos_ativos.keys())
        for tid in ids:
            mov = self.movimentos_ativos[tid]
            taxi = mov['taxi']
            mov['tempo_restante_aresta'] -= 1
            
            if mov['tempo_restante_aresta'] <= 0:
                if mov['idx_prox_no'] < len(mov['caminho']):
                    dest = mov['caminho'][mov['idx_prox_no']]
                    dist, _ = self.grafo.get_custo_aresta(taxi.localizacao_atual, dest)
                    
                    if dist == float('inf'): 
                        del self.movimentos_ativos[tid]
                        continue

                    taxi.mover_e_consumir(dist, dest)
                    mov['idx_prox_no'] += 1
                    
                    if mov['idx_prox_no'] < len(mov['caminho']):
                        prox = mov['caminho'][mov['idx_prox_no']]
                        _, t = self.grafo.get_custo_aresta(taxi.localizacao_atual, prox)
                        mov['tempo_restante_aresta'] = t
                    else:
                        self._concluir_segmento(mov)
                else:
                    self._concluir_segmento(mov)

    def _concluir_segmento(self, mov):
        taxi, tipo, pedido = mov['taxi'], mov['tipo'], mov.get('pedido')
        
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
            print(f"TEMPO: {self.current_time} - {taxi.id_veiculo} chegou. {msg}...")
            taxi.iniciar_carregamento()
            
            # REDUZIDO PARA 30 MINUTOS (Fast Charging)
            t_carga = 30 if taxi.tipo == TipoMotorizacao.ELETRICO else 5 
            
            self.movimentos_ativos[taxi.id_veiculo] = {
                'taxi': taxi, 'tipo': "EM_CARGA", 'caminho': [], 'idx_prox_no': 0, 
                'tempo_restante_aresta': t_carga, 'pedido': None
            }
            
        elif tipo == "EM_CARGA":
            print(f"TEMPO: {self.current_time} - {taxi.id_veiculo} pronto (100%).")
            taxi.terminar_carregamento()
            del self.movimentos_ativos[taxi.id_veiculo]

    def _manage_idle_taxis(self):
        for taxi in self.gestor.frota.values():
            if taxi.estado == EstadoVeiculo.LIVRE and taxi.id_veiculo not in self.movimentos_ativos:
                
                # Verifica se tem autonomia crítica
                if taxi.precisa_recarregar(self.LIMIAR_RECARGA_ELETTRICO):
                    estacao, caminho = self._find_nearest_charger(taxi.localizacao_atual)
                    if estacao:
                        # Só vai se tiver autonomia para chegar
                        dist_ate = self.gestor._get_dist_caminho(caminho)
                        if taxi.autonomia_atual >= dist_ate:
                            acao = "A_CARREGAR" if taxi.tipo == TipoMotorizacao.ELETRICO else "A_ABASTECER"
                            msg = "Bateria fraca" if taxi.tipo == TipoMotorizacao.ELETRICO else "Combustível"
                            print(f"TEMPO: {self.current_time} - {taxi.id_veiculo} ({msg}). A ir para {estacao}...")
                            self._iniciar_movimento(taxi, caminho, acao)
                        else:
                            print(f"ALERTA: {taxi.id_veiculo} sem autonomia para chegar à estação!")
                            taxi.estado = EstadoVeiculo.EM_FALHA

    def _find_nearest_charger(self, origem):
        estacoes = [n for n, d in self.grafo.nos.items() if d.get('pode_carregar')]
        best, min_t, best_path = None, float('inf'), None
        for st in estacoes:
            path, t = self.gestor.get_caminho(origem, st)
            if path and t < min_t: min_t, best, best_path = t, st, path
        return best, best_path

    def _update_traffic(self):
        hora = self.current_time.hour
        mult = self.MULTIPLICADOR_TRANSITO if hora in self.HORAS_DE_PONTA else 1.0
        first = list(self.grafo.condicoes_transito.keys())[0]
        
        mudou = False
        for u, v in list(self.grafo.condicoes_transito.keys()):
             if random.random() < 0.3:
                novo_mult = mult if random.random() > 0.3 else 1.0
                if self.grafo.condicoes_transito[(u,v)] != novo_mult:
                    self.grafo.atualizar_transito(u, v, novo_mult)
                    mudou = True
        return mudou

    def _atualizar_descricoes_gui(self):
        self.status_descricoes.clear()
        for t_id, taxi in self.gestor.frota.items():
            if taxi.estado == EstadoVeiculo.EM_FALHA:
                 self.status_descricoes[t_id] = "FALHA"
                 continue
            if t_id in self.movimentos_ativos:
                mov = self.movimentos_ativos[t_id]
                tipo = mov['tipo']
                if tipo == "PICKUP": txt = f"Busca ({mov['pedido'].origem})"
                elif tipo == "VIAGEM": txt = f"Leva ({mov['pedido'].destino})"
                elif tipo in ["A_CARREGAR", "A_ABASTECER"]: txt = "Vai Abast."
                elif tipo == "EM_CARGA": txt = "A Abast."
                else: txt = tipo
                self.status_descricoes[t_id] = txt
            else: self.status_descricoes[t_id] = "Livre"

    def print_summary(self):
        concluidos = [p for p in self.pedidos_gerados if p.estado == EstadoPedido.CONCLUIDO]
        rejeitados = [p for p in self.pedidos_gerados if p.estado == EstadoPedido.REJEITADO]
        total = len(self.pedidos_gerados)
        
        taxa = (len(rejeitados)/total)*100 if total > 0 else 0
        wait = sum([p.get_tempo_espera_total() for p in concluidos])/len(concluidos) if concluidos else 0
        
        print("\n" + "="*40)
        print(f"Total: {total} | OK: {len(concluidos)} | NOK: {len(rejeitados)} ({taxa:.1f}%)")
        print(f"Espera Média: {wait:.2f} min")
        print("="*40)
        
        return {
            "total_pedidos": total,
            "concluidos": len(concluidos),
            "rejeitados": len(rejeitados),
            "taxa_rejeicao": taxa,
            "tempo_espera": wait
        }