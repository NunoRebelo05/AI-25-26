import random
import time
from datetime import datetime, timedelta

from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao, EstadoVeiculo
from Pedido import Pedido, PrioridadePedido, EstadoPedido
from Gestor import GestorDeFrota
from Config import cfg

class Simulador:
    """
    Motor principal da simulação.
    
    Gerencia o relógio da simulação, a geração de pedidos, o movimento dos táxis
    e a interação com o gestor de frota e a interface gráfica.
    """
    
    def __init__(self, gestor: GestorDeFrota, hora_inicio: datetime, 
                 duracao_sim_horas: int,
                 horas_ponta: list = None,        
                 prob_pedido: float = 0.15,        
                 gui_interface = None,
                 usar_estaticos: bool = None):
        """
        Inicializa o simulador.
        
        Args:
            gestor (GestorDeFrota): O gestor que controla a frota.
            hora_inicio (datetime): Hora inicial da simulação.
            duracao_sim_horas (int): Duração total em horas.
            horas_ponta (list, optional): Lista de horas consideradas de ponta.
            prob_pedido (float, optional): Probabilidade de gerar um novo pedido a cada minuto.
            gui_interface (VisualizadorGUI, optional): Referência para a GUI (para atualizações visuais).
            usar_estaticos (bool, optional): Se True, usa lista pré-definida de pedidos.
        """
        
        self.gestor = gestor
        self.grafo = gestor.grafo
        self.gui = gui_interface
        
        # Listas de Estado
        self.pedidos_gerados = [] 
        self.movimentos_ativos = {} 
        
        self.hora_inicio = hora_inicio
        self.current_time = hora_inicio
        self.end_time = hora_inicio + timedelta(hours=duracao_sim_horas)
        self.time_step = timedelta(seconds=1) 
        
        # Configurações
        self.HORAS_DE_PONTA = horas_ponta if horas_ponta is not None else cfg.get('simulacao.horas_ponta')
        self.PROB_NOVO_PEDIDO = prob_pedido
        self.LIMIAR_RECARGA_ELETTRICO = cfg.get('simulacao.limiar_recarga_eletrico')
        self.MULTIPLICADOR_TRANSITO = cfg.get('simulacao.multiplicador_transito_ponta')
        self.CORES_PEDIDOS = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0']
        
        self.status_descricoes = {}
        self.paused = False
        self.running = True # Control flag
        self.delay = 0.03 if self.gui else 0.0 # ~30 FPS para estabilidade
        self.steps_per_update = 1 # Quantos passos de simulação por frame de GUI

        # Static Requests
        if usar_estaticos is not None:
            self.usar_estaticos = usar_estaticos
        else:
            self.usar_estaticos = cfg.get('pedidos_estaticos.usar_estaticos', False)
            
        self.lista_estaticos = cfg.get('pedidos_estaticos.lista', [])
        # Ordenar estáticos por minuto para eficiência
        self.lista_estaticos.sort(key=lambda x: x['minuto_simulacao'])

        print(f"Simulador iniciado ({self.hora_inicio} -> {self.end_time}). Modo Estático: {self.usar_estaticos}")

    def run(self):
        """
        Executa o loop principal da simulação.
        
        Avança o tempo passo a passo, processa movimentos, gera pedidos e atualiza a GUI.
        Termina quando o tempo acaba e não há mais atividades pendentes.
        """
        print(f"\n--- INÍCIO DA SIMULAÇÃO ({'Modo Visual' if self.gui else 'Modo Rápido'}) ---")
        
        # Loop continua se:
        # 1. Ainda não chegamos ao fim do tempo
        # 2. OU existem movimentos ativos (táxis a andar)
        # 3. OU existem pedidos na fila de espera
        # 4. E a flag self.running for True
        while self.running and (self.current_time <= self.end_time or self.movimentos_ativos or self.gestor.pedidos_pendentes):
            
            while self.paused and self.running: 
                time.sleep(0.1)
                # Se tiver GUI, precisamos de atualizar a janela para não bloquear
                if self.gui: self.gui.update()

            if not self.running: break

            # Executar múltiplos passos de simulação por frame (Fast Forward)
            for _ in range(self.steps_per_update):
                if not (self.current_time <= self.end_time or self.movimentos_ativos or self.gestor.pedidos_pendentes):
                    break

                if self.current_time.minute % 30 == 0 and self.current_time.second == 0:
                     if self._update_traffic() and self.gui:
                         self.gui.desenhar_mapa_base()

                self.step()
                self.current_time += self.time_step
            
            if self.gui:
                self._atualizar_descricoes_gui()
                pedidos_ativos = [p for p in self.pedidos_gerados if p.estado in [EstadoPedido.PENDENTE, EstadoPedido.EM_CURSO]]
                self.gui.atualizar_estado(self.gestor.frota, pedidos_ativos, self.current_time, self.status_descricoes)
                time.sleep(self.delay)
            
        print("Simulação Concluída.")
        return self.print_summary()

    def stop(self):
        """Para a simulação forçadamente."""
        self.running = False
        print("Simulação parada pelo utilizador.")

    def toggle_pause(self):
        """Alterna o estado de pausa da simulação."""
        self.paused = not self.paused
        return self.paused

    def set_speed(self, speed_level):
        """
        Define a velocidade da simulação.
        
        Args:
            speed_level (int): Nível de 1 a 20.
        """
        # Nível 1-10: Controla o delay (steps=1)
        # Nível 11-20: Controla steps_per_update (delay=0)
        
        if speed_level <= 10:
            self.steps_per_update = 1
            # Delay de 0.1s (lento) a 0.0s (rápido)
            # speed 1 -> 0.1
            # speed 10 -> 0.0
            self.delay = 0.1 - ((speed_level - 1) * (0.1 / 9))
        else:
            self.delay = 0.0
            # Steps de 1 a 60 (ou mais)
            # speed 11 -> 2 steps
            # speed 20 -> 60 steps
            factor = speed_level - 10
            self.steps_per_update = int(1 + (factor * 6)) # 1 -> 7 -> 13 ... -> 61
            
        # Garantir mínimo de delay para GUI não bloquear se steps for baixo
        if self.gui and self.delay < 0.001 and self.steps_per_update < 5:
             self.delay = 0.001
             
        print(f"Velocidade ajustada: Nível {speed_level} -> Delay {self.delay:.4f}s, Steps {self.steps_per_update}")

    def set_delay(self, delay):
        """Legacy: Mantido para compatibilidade, mas idealmente usar set_speed."""
        self.delay = delay

    def step(self):
        """
        Executa um único passo da simulação (1 minuto).
        
        1. Gera novos pedidos (se aplicável).
        2. Atualiza posições dos táxis em movimento.
        3. Tenta alocar pedidos em espera.
        4. Gere táxis livres (ex: recarga).
        """
        # Só gera novos pedidos se ainda estivermos dentro do horário normal
        # E apenas no início de cada minuto para manter a probabilidade correta
        if self.current_time <= self.end_time and self.current_time.second == 0:
            self._generate_new_request()

        self._processar_movimentos()
        
        # 1. Tentar esvaziar a fila de espera (Prioritário)
        self._processar_fila_espera()
        
        # 2. Só depois é que vemos se os livres vão carregar
        self._manage_idle_taxis()

    def _generate_new_request(self):
        """Gera novos pedidos, seja a partir da lista estática ou aleatoriamente."""
        # 1. Verificar Pedidos Estáticos
        if self.usar_estaticos:
            minutos_passados = int((self.current_time - self.hora_inicio).total_seconds() / 60)
            
            # Encontrar pedidos para este minuto
            for req in self.lista_estaticos:
                if req['minuto_simulacao'] == minutos_passados:
                    self._criar_pedido_especifico(req)
            return

        # 2. Geração Aleatória (se não for estático)
        if random.random() < self.PROB_NOVO_PEDIDO:
            n_validos = list(self.grafo.nos.keys())
            if len(n_validos) < 2: return
            
            origem, destino = random.sample(n_validos, 2)
            
            novo_pedido = Pedido(
                origem=origem, destino=destino, num_passageiros=random.randint(1, 4),
                pref_ambiental=random.choice([True, False]), hora_criacao=self.current_time,
                prioridade=random.choice(list(PrioridadePedido))
            )
            self._registar_pedido(novo_pedido)

    def _criar_pedido_especifico(self, req_data):
        """Cria um pedido específico a partir de dados de configuração."""
        origem = req_data['origem']
        destino = req_data['destino']
        
        if origem not in self.grafo.nos or destino not in self.grafo.nos:
            print(f"ERRO: Pedido Estático ignorado. Nó inválido: {origem} -> {destino}")
            return

        try:
            prioridade = PrioridadePedido[req_data['prioridade']]
        except:
            prioridade = PrioridadePedido.NORMAL

        novo_pedido = Pedido(
            origem=origem,
            destino=destino,
            num_passageiros=req_data['passageiros'],
            pref_ambiental=req_data['ambiental'],
            hora_criacao=self.current_time,
            prioridade=prioridade
        )
        print(f"PEDIDO ESTÁTICO GERADO: {novo_pedido}")
        self._registar_pedido(novo_pedido)

    def _registar_pedido(self, pedido):
        """Regista um novo pedido no sistema e tenta alocação imediata."""
        pedido.cor_mapa = random.choice(self.CORES_PEDIDOS)
        print(f"TEMPO: {self.current_time} - NOVO PEDIDO {pedido.id_pedido} ({pedido.origem} -> {pedido.destino})")
        self.pedidos_gerados.append(pedido)
        self._tenta_alocar_pedido(pedido)

    def _processar_fila_espera(self):
        """
        Gere a fila de espera:
        1. Remove pedidos expirados (timeout).
        2. Tenta alocar pedidos pendentes, ordenados por prioridade e antiguidade.
        """
        
        MAX_ESPERA = 60 
        
        # 1. Verificar Timeouts
        for pedido in self.gestor.pedidos_pendentes[:]:
            tempo_passado = (self.current_time - pedido.hora_criacao).total_seconds() / 60
            
            if tempo_passado > MAX_ESPERA:
                print(f"TEMPO: {self.current_time} - Pedido {pedido.id_pedido} EXPIROU (esperou {tempo_passado:.0f} min). Rejeitado.")
                pedido.rejeitar()
                self.gestor.pedidos_pendentes.remove(pedido)

        # 2. Tentar alocar (Ordenado por Prioridade DESC, depois Tempo Espera DESC)
        fila_ordenada = sorted(self.gestor.pedidos_pendentes, 
                               key=lambda p: (p.prioridade.value, p.hora_criacao), 
                               reverse=True)

        for pedido in fila_ordenada:
            if self._tenta_alocar_pedido(pedido, vindo_da_fila=True):
                pass

    def _tenta_alocar_pedido(self, pedido, vindo_da_fila=False):
        """
        Solicita ao gestor a alocação de um táxi para o pedido.
        
        Se alocado com sucesso, inicia o movimento do táxi.
        Se falhar, coloca (ou mantém) o pedido na fila de espera.
        
        Returns:
            bool: True se alocado com sucesso, False caso contrário.
        """
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
            
            if not self._iniciar_movimento(taxi, c_pickup, "PICKUP", pedido, c_viagem):
                print(f"ERRO CRÍTICO: Falha ao iniciar movimento para {taxi.id_veiculo}. Revertendo estado.")
                taxi.estado = EstadoVeiculo.LIVRE
                # Devolver pedido à fila (ou rejeitar se for crítico)
                if pedido not in self.gestor.pedidos_pendentes:
                    pedido.estado = EstadoPedido.PENDENTE
                    self.gestor.pedidos_pendentes.append(pedido)
                return False
                
            return True
        else:
            if not vindo_da_fila:
                if pedido not in self.gestor.pedidos_pendentes:
                    self.gestor.pedidos_pendentes.append(pedido)
                    print(f"INFO: Pedido {pedido.id_pedido} entrou na FILA DE ESPERA.")
            return False

    def _iniciar_movimento(self, taxi, caminho, tipo, pedido=None, proximo_caminho=None):
        """
        Configura o estado de movimento de um táxi.
        
        Args:
            taxi (Taxi): O táxi a mover.
            caminho (list): Lista de nós a percorrer.
            tipo (str): Tipo de movimento ('PICKUP', 'VIAGEM', 'A_CARREGAR', etc.).
            pedido (Pedido, optional): Pedido associado.
            proximo_caminho (list, optional): Caminho seguinte (ex: viagem após pickup).
        """
        if not caminho or len(caminho) < 2:
            tempo_prox, prox_no_idx = 0, 0
        else:
            prox_no_idx = 1
            
        if not caminho:
            print(f"ERRO: Caminho vazio para {taxi.id_veiculo} no movimento {tipo}.")
            return False

        origem = caminho[0]
        destino = caminho[1] if len(caminho) > 1 else origem
        
        dist, tempo = self.grafo.get_custo_aresta(origem, destino)
        
        if dist == float('inf'):
            print(f"ERRO: Caminho inválido ou desconectado para {taxi.id_veiculo} de {origem} para {destino}.")
            return False

        taxi.estado = EstadoVeiculo.OCUPADO
        taxi.localizacao_atual = origem
        
        self.movimentos_ativos[taxi.id_veiculo] = {
            'taxi': taxi,
            'caminho': caminho,
            'idx_prox_no': prox_no_idx,
            'tempo_restante_aresta': tempo * 60, # Converter para segundos
            'tempo_total_aresta': tempo * 60,    # Converter para segundos
            'tipo': tipo,
            'pedido': pedido,
            'proximo_caminho': proximo_caminho
        }
        
        if tipo == "PICKUP":
            print(f"TEMPO: {self.current_time} - {taxi.id_veiculo} a caminho de {pedido.origem} para pickup.")
        elif tipo == "VIAGEM":
            print(f"TEMPO: {self.current_time} - {taxi.id_veiculo} a levar {pedido.id_pedido} de {pedido.origem} para {pedido.destino}.")
        elif tipo in ["A_CARREGAR", "A_ABASTECER"]:
            msg = "carregar" if tipo == "A_CARREGAR" else "abastecer"
            print(f"TEMPO: {self.current_time} - {taxi.id_veiculo} a caminho para {msg} em {caminho[-1]}.")
            
        return True

    def _processar_movimentos(self):
        """
        Decrementa o tempo restante na aresta atual. Se chegar a zero,
        move o táxi para o próximo nó ou conclui o segmento.
        """
        ids = list(self.movimentos_ativos.keys())
        for tid in ids:
            mov = self.movimentos_ativos[tid]
            taxi = mov['taxi']
            mov['tempo_restante_aresta'] -= 1
            
            if mov['tempo_restante_aresta'] <= 0:
                # Chegou ao próximo nó
                taxi.localizacao_atual = mov['caminho'][mov['idx_prox_no']]
                taxi.autonomia_atual -= self.grafo.get_custo_aresta(mov['caminho'][mov['idx_prox_no']-1], taxi.localizacao_atual)[0]
                
                if mov['idx_prox_no'] < len(mov['caminho']) - 1:
                    # Ainda há mais nós no caminho atual
                    mov['idx_prox_no'] += 1
                    origem = taxi.localizacao_atual
                    destino = mov['caminho'][mov['idx_prox_no']]
                    
                    dist, tempo = self.grafo.get_custo_aresta(origem, destino)
                    if dist == float('inf'): 
                        print(f"ERRO: Perda de conexão durante movimento de {taxi.id_veiculo} para {destino}")
                        del self.movimentos_ativos[tid]
                        
                        # RECUPERAÇÃO DE FALHA
                        print(f"RECUPERAÇÃO: Taxi {taxi.id_veiculo} reiniciado para estado LIVRE.")
                        taxi.estado = EstadoVeiculo.LIVRE
                        
                        # Tratar do pedido afetado
                        pedido = mov.get('pedido')
                        if pedido:
                            print(f"RECUPERAÇÃO: Pedido {pedido.id_pedido} devolvido à fila.")
                            pedido.estado = EstadoPedido.PENDENTE
                            pedido.id_veiculo_alocado = None
                            if pedido not in self.gestor.pedidos_pendentes:
                                self.gestor.pedidos_pendentes.append(pedido)
                        continue # Passa para o próximo táxi
                    
                    mov['tempo_restante_aresta'] = tempo * 60
                    mov['tempo_total_aresta'] = tempo * 60
                else:
                    # Chegou ao final do caminho atual
                    self._concluir_segmento_movimento(mov)

    def _concluir_segmento_movimento(self, mov):
        """
        Chamado quando um táxi termina o seu caminho atual.
        
        Gere a transição de estados (ex: PICKUP -> VIAGEM, VIAGEM -> LIVRE, etc.).
        """
        taxi, tipo, pedido = mov['taxi'], mov['tipo'], mov.get('pedido')
        
        if tipo == "PICKUP":
            if not self._iniciar_movimento(taxi, mov['proximo_caminho'], "VIAGEM", pedido):
                 print(f"ERRO: Falha ao iniciar VIAGEM para {taxi.id_veiculo}. Abortando.")
                 
                 # RECUPERAÇÃO DE FALHA
                 print(f"RECUPERAÇÃO: Taxi {taxi.id_veiculo} reiniciado para estado LIVRE.")
                 taxi.estado = EstadoVeiculo.LIVRE
                 
                 if pedido: 
                     print(f"RECUPERAÇÃO: Pedido {pedido.id_pedido} devolvido à fila.")
                     pedido.estado = EstadoPedido.PENDENTE
                     pedido.id_veiculo_alocado = None
                     if pedido not in self.gestor.pedidos_pendentes:
                        self.gestor.pedidos_pendentes.append(pedido)
                 
                 if taxi.id_veiculo in self.movimentos_ativos:
                    del self.movimentos_ativos[taxi.id_veiculo]
            else:
                print(f"TEMPO: {self.current_time} - {taxi.id_veiculo} fez pickup de {pedido.id_pedido} em {pedido.origem}.")
            
        elif tipo == "VIAGEM":
            taxi.libertar_no_destino(taxi.localizacao_atual)
            if pedido: pedido.concluir()
            del self.movimentos_ativos[taxi.id_veiculo]
            print(f"TEMPO: {self.current_time} - {taxi.id_veiculo} concluiu viagem de {pedido.id_pedido} em {pedido.destino}.")
            
        elif tipo in ["A_CARREGAR", "A_ABASTECER"]:
            msg = "a carregar" if tipo == "A_CARREGAR" else "a abastecer"
            print(f"TEMPO: {self.current_time} - {taxi.id_veiculo} chegou. {msg}...")
            taxi.iniciar_carregamento()
            
            # Inicia o movimento de carregamento/abastecimento
            self.movimentos_ativos[taxi.id_veiculo] = {
                'taxi': taxi,
                'caminho': [taxi.localizacao_atual], # Fica parado
                'idx_prox_no': 0,
                'tempo_restante_aresta': taxi.tempo_carregamento_restante * 60, # Tempo para carregar (min -> seg)
                'tempo_total_aresta': taxi.tempo_carregamento_restante * 60,
                'tipo': "EM_CARGA" if tipo == "A_CARREGAR" else "EM_ABASTECIMENTO",
                'pedido': None,
                'proximo_caminho': None
            }
        elif tipo in ["EM_CARGA", "EM_ABASTECIMENTO"]:
            taxi.concluir_carregamento()
            del self.movimentos_ativos[taxi.id_veiculo]
            msg = "carregado" if tipo == "EM_CARGA" else "abastecido"
            print(f"TEMPO: {self.current_time} - {taxi.id_veiculo} totalmente {msg}. LIVRE.")

    def _manage_idle_taxis(self):
        """
        Verifica táxis livres e envia-os para recarga/abastecimento se necessário.
        """
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
        """Encontra a estação de recarga mais próxima (em tempo)."""
        estacoes = [n for n, d in self.grafo.nos.items() if d.get('pode_carregar')]
        best, min_t, best_path = None, float('inf'), None
        for st in estacoes:
            path, t = self.gestor.get_caminho(origem, st)
            if path and t < min_t: min_t, best, best_path = t, st, path
        return best, best_path

    def _update_traffic(self):
        """
        Atualiza aleatoriamente as condições de trânsito nas horas de ponta.
        Returns: True se houve alterações.
        """
        hora = self.current_time.hour
        mult = self.MULTIPLICADOR_TRANSITO if hora in self.HORAS_DE_PONTA else 1.0
        
        mudou = False
        for u, v in list(self.grafo.condicoes_transito.keys()):
             if random.random() < 0.3:
                novo_mult = mult if random.random() > 0.3 else 1.0
                if self.grafo.condicoes_transito[(u,v)] != novo_mult:
                    self.grafo.atualizar_transito(u, v, novo_mult)
                    mudou = True
        return mudou

    def _atualizar_descricoes_gui(self):
        """Atualiza o dicionario de descricoes de estado para a GUI."""
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
        """Imprime e retorna um resumo estatistico da simulacao."""
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