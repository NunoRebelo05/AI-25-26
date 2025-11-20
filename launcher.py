import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
from datetime import datetime

from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao
from Gestor import GestorDeFrota, EstrategiaProcura
from Simulador import Simulador
# Importa a nova classe do visualizador
from VisualizadorGUI import MapaVisualizador 

def carregar_grafo_de_json(ficheiro_json: str) -> Grafo:
    mapa = Grafo()
    try:
        with open(ficheiro_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for no in data['nos']: 
                mapa.add_no(no['id'], no['lat'], no['lon'], no.get('tipo'))
                if no.get('pode_carregar'): mapa.nos[no['id']]['pode_carregar'] = True
            for aresta in data['arestas']:
                mapa.add_aresta(aresta['origem'], aresta['destino'], aresta['distancia_km'], aresta['tempo_base_min'])
            return mapa
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao carregar mapa: {e}")
        return None

def iniciar_simulacao(config, app_gui):
    try:
        # 1. Configurar
        mapa = carregar_grafo_de_json("braga_mapa.json")
        if not mapa: return
        gestor = GestorDeFrota(mapa)
        gestor.definir_estrategia(config['estrategia'])
        
        locais = list(mapa.nos.keys())
        for i in range(config['num_eletricos']):
            gestor.add_taxi(Taxi(f"EV{i+1}", TipoMotorizacao.ELETRICO, locais[i%len(locais)], 4, 0.15, 400))
        for i in range(config['num_combustao']):
            gestor.add_taxi(Taxi(f"GAS{i+1}", TipoMotorizacao.COMBUSTAO, locais[(i+3)%len(locais)], 4, 0.25, 600))

        # 2. Criar Janela de Visualização (Toplevel para ser independente do menu)
        janela_sim = tk.Toplevel()
        janela_sim.title(f"Simulação TaxiGreen - {config['estrategia'].name}")
        
        gui_mapa = MapaVisualizador(janela_sim, mapa, largura=800, altura=600)
        gui_mapa.pack()

        # 3. Iniciar Simulador com a GUI
        simulador = Simulador(
            gestor=gestor,
            hora_inicio=datetime(2025, 10, 20, 8, 0, 0),
            duracao_sim_horas=config['duracao_horas'],
            horas_ponta=config['horas_ponta'],
            prob_pedido=config['prob_pedido'],
            gui_interface=gui_mapa
        )
        gui_mapa.set_simulador(simulador)
        print("\nA iniciar a simulação...")
        simulador.run() # O run() agora tem um time.sleep() para se ver a animação
        
        messagebox.showinfo("Sucesso", "Simulação concluída!")

    except Exception as e:
        print(f"ERRO: {e}")
    finally:
        app_gui.reativar_botao()

class AppLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Configuração TaxiGreen")
        self.geometry("450x450")
        
        p = ttk.Frame(self, padding="10")
        p.pack(fill="both", expand=True)

        # Estratégia
        ttk.Label(p, text="Estratégia de Procura:").pack(anchor="w")
        self.strat_var = tk.StringVar(value=EstrategiaProcura.A_STAR.name)
        ttk.OptionMenu(p, self.strat_var, *[e.name for e in EstrategiaProcura]).pack(fill="x", pady=5)
        
        # Frota
        f_frota = ttk.LabelFrame(p, text="Frota")
        f_frota.pack(fill="x", pady=10, padx=5)
        ttk.Label(f_frota, text="Elétricos:").pack(side="left", padx=5)
        self.num_ev = tk.IntVar(value=2)
        ttk.Spinbox(f_frota, from_=0, to=20, textvariable=self.num_ev, width=5).pack(side="left")
        ttk.Label(f_frota, text="Combustão:").pack(side="left", padx=5)
        self.num_gas = tk.IntVar(value=2)
        ttk.Spinbox(f_frota, from_=0, to=20, textvariable=self.num_gas, width=5).pack(side="left")

        # Simulação
        f_sim = ttk.LabelFrame(p, text="Parâmetros da Simulação")
        f_sim.pack(fill="x", pady=10, padx=5)
        ttk.Label(f_sim, text="Duração (horas):").pack(anchor="w")
        self.duracao = tk.IntVar(value=12)
        ttk.Spinbox(f_sim, from_=1, to=48, textvariable=self.duracao).pack(fill="x", padx=5)
        ttk.Label(f_sim, text="Probabilidade Pedido/min (0.1 - 1.0):").pack(anchor="w")
        self.prob = tk.DoubleVar(value=0.15)
        ttk.Scale(f_sim, from_=0.05, to=1.0, variable=self.prob).pack(fill="x", padx=5)
        ttk.Label(f_sim, text="Horas de Ponta (sep. por vírgula):").pack(anchor="w")
        self.h_ponta = tk.StringVar(value="8,9,17,18")
        ttk.Entry(f_sim, textvariable=self.h_ponta).pack(fill="x", padx=5)

        # Botão
        self.btn = ttk.Button(p, text="INICIAR SIMULAÇÃO", command=self.on_start)
        self.btn.pack(side="bottom", fill="x", pady=20)

    def on_start(self):
        self.btn.config(state="disabled", text="A Executar...")
        try:
            h_ponta = [int(h.strip()) for h in self.h_ponta.get().split(',') if h.strip()]
        except:
            messagebox.showerror("Erro", "Horas de ponta inválidas.")
            self.reativar_botao()
            return

        config = {
            'estrategia': EstrategiaProcura[self.strat_var.get()],
            'num_eletricos': self.num_ev.get(),
            'num_combustao': self.num_gas.get(),
            'duracao_horas': self.duracao.get(),
            'horas_ponta': h_ponta,
            'prob_pedido': self.prob.get()
        }
        threading.Thread(target=iniciar_simulacao, args=(config, self)).start()

    def reativar_botao(self):
        self.btn.config(state="normal", text="INICIAR SIMULAÇÃO")

if __name__ == "__main__":
    app = AppLauncher()
    app.mainloop()