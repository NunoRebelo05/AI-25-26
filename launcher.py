import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
from datetime import datetime

from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao
from Gestor import GestorDeFrota, EstrategiaProcura
from Simulador import Simulador
from VisualizadorGUI import MapaVisualizador
from Config import cfg

def iniciar_simulacao(config_launch, app_gui):
    try:
        # 1. Configurar
        mapa = Grafo.carregar_de_json("braga_mapa.json")
        if not mapa: return
        gestor = GestorDeFrota(mapa)
        gestor.definir_estrategia(config_launch['estrategia'])
        
        # Setup Frota Dinâmica (baseado na config do launcher)
        locais = list(mapa.nos.keys())
        specs_ev = cfg.get('frota.specs_eletrico')
        specs_gas = cfg.get('frota.specs_combustao')

        for i in range(config_launch['num_eletricos']):
            local = locais[i % len(locais)]
            gestor.add_taxi(Taxi(f"EV{i+1:02d}", TipoMotorizacao.ELETRICO, local, 
                                 specs_ev['capacidade'], specs_ev['custo_km'], specs_ev['autonomia']))
            
        for i in range(config_launch['num_combustao']):
            local = locais[(i+3) % len(locais)]
            gestor.add_taxi(Taxi(f"GAS{i+1:02d}", TipoMotorizacao.COMBUSTAO, local, 
                                 specs_gas['capacidade'], specs_gas['custo_km'], specs_gas['autonomia']))

        # 2. Criar Janela de Visualização (Toplevel para ser independente do menu)
        janela_sim = tk.Toplevel()
        janela_sim.title(f"Simulação TaxiGreen - {config_launch['estrategia'].name}")
        
        gui_mapa = MapaVisualizador(janela_sim, mapa, largura=800, altura=600)
        gui_mapa.pack()

        # 3. Iniciar Simulador com a GUI
        simulador = Simulador(
            gestor=gestor,
            hora_inicio=datetime(2025, 10, 20, 8, 0, 0),
            duracao_sim_horas=config_launch['duracao_horas'],
            horas_ponta=config_launch['horas_ponta'],
            prob_pedido=config_launch['prob_pedido'],
            gui_interface=gui_mapa,
            usar_estaticos=config_launch['usar_estaticos']
        )
        gui_mapa.set_simulador(simulador)
        print("\nA iniciar a simulação...")
        simulador.run() 
        
        messagebox.showinfo("Sucesso", "Simulação concluída!")

    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        app_gui.reativar_botao()

class AppLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Configuração TaxiGreen")
        self.geometry("450x500") # Aumentei um pouco a altura
        
        # Carregar config inicial
        cfg.carregar()
        
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
        self.num_ev = tk.IntVar(value=cfg.get('frota.num_eletricos'))
        ttk.Spinbox(f_frota, from_=0, to=20, textvariable=self.num_ev, width=5).pack(side="left")
        ttk.Label(f_frota, text="Combustão:").pack(side="left", padx=5)
        self.num_gas = tk.IntVar(value=cfg.get('frota.num_combustao'))
        ttk.Spinbox(f_frota, from_=0, to=20, textvariable=self.num_gas, width=5).pack(side="left")

        # Simulação
        f_sim = ttk.LabelFrame(p, text="Parâmetros da Simulação")
        f_sim.pack(fill="x", pady=10, padx=5)
        ttk.Label(f_sim, text="Duração (horas):").pack(anchor="w")
        self.duracao = tk.IntVar(value=cfg.get('simulacao.duracao_horas'))
        ttk.Spinbox(f_sim, from_=1, to=48, textvariable=self.duracao).pack(fill="x", padx=5)
        
        ttk.Label(f_sim, text="Probabilidade Pedido/min (0.1 - 1.0):").pack(anchor="w")
        self.prob = tk.DoubleVar(value=cfg.get('simulacao.prob_pedido'))
        ttk.Scale(f_sim, from_=0.05, to=1.0, variable=self.prob).pack(fill="x", padx=5)
        
        # Checkbox para Pedidos Estáticos
        self.usar_estaticos = tk.BooleanVar(value=cfg.get('pedidos_estaticos.usar_estaticos'))
        ttk.Checkbutton(f_sim, text="Usar Pedidos Estáticos (Predefinidos)", variable=self.usar_estaticos).pack(anchor="w", padx=5, pady=5)

        ttk.Label(f_sim, text="Horas de Ponta (sep. por vírgula):").pack(anchor="w")
        
        horas_ponta_default = ",".join(map(str, cfg.get('simulacao.horas_ponta')))
        self.h_ponta = tk.StringVar(value=horas_ponta_default)
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
            'prob_pedido': self.prob.get(),
            'usar_estaticos': self.usar_estaticos.get()
        }
        threading.Thread(target=iniciar_simulacao, args=(config, self)).start()

    def reativar_botao(self):
        self.btn.config(state="normal", text="INICIAR SIMULAÇÃO")

if __name__ == "__main__":
    app = AppLauncher()
    app.mainloop()