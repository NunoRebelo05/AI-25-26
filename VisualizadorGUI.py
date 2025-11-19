import tkinter as tk
from tkinter import ttk
from Taxi import EstadoVeiculo, TipoMotorizacao

class MapaVisualizador(tk.Frame):
    def __init__(self, master, grafo, largura=800, altura=600):
        super().__init__(master)
        self.grafo = grafo
        self.largura = largura
        self.altura = altura
        self.margem = 50
        self.simulador = None 
        
        self.pack(fill="both", expand=True)
        
        # 1. Área do Mapa
        self.canvas = tk.Canvas(self, width=largura, height=altura, bg="white")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # 2. Painel
        self.painel_info = tk.Frame(self, width=300, bg="#f0f0f0", padx=10, pady=10)
        self.painel_info.pack(side="right", fill="y")
        self.painel_info.pack_propagate(False)
        
        # Controlos
        tk.Label(self.painel_info, text="Controlos", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=(0, 5))
        f_ctrl = tk.Frame(self.painel_info, bg="#f0f0f0", bd=2, relief="groove")
        f_ctrl.pack(fill="x", pady=(0, 20), ipadx=5, ipady=5)
        
        self.btn_pause = tk.Button(f_ctrl, text="⏸ PAUSA", bg="orange", fg="white", font=("Arial", 10, "bold"), command=self.toggle_pause)
        self.btn_pause.pack(fill="x", pady=5, padx=5)
        
        tk.Label(f_ctrl, text="Velocidade", bg="#f0f0f0", font=("Arial", 9)).pack()
        self.scale_speed = tk.Scale(f_ctrl, from_=1, to=20, orient="horizontal", bg="#f0f0f0", command=self.mudar_velocidade)
        self.scale_speed.set(5)
        self.scale_speed.pack(fill="x", padx=5)
        
        # Info
        self.lbl_hora = tk.Label(self.painel_info, text="00:00:00", font=("Arial", 16, "bold"), bg="#f0f0f0")
        self.lbl_hora.pack(pady=(0, 20))
        
        # Legendas
        lbl_legenda = tk.Label(self.painel_info, text="Legenda", font=("Arial", 10, "bold"), bg="#f0f0f0")
        lbl_legenda.pack(anchor="w")
        self._criar_item_legenda("green", "Livre")
        self._criar_item_legenda("red", "Ocupado")
        self._criar_item_legenda("blue", "A Carregar (Elétrico)")
        self._criar_item_legenda("purple", "A Abastecer (Combustão)")
        self._criar_item_legenda("#CCCCCC", "Sem Trânsito")
        self._criar_item_legenda("#FF0000", "Trânsito Intenso")
        
        tk.Label(self.painel_info, text="", bg="#f0f0f0").pack()
        
        # Frota
        tk.Label(self.painel_info, text="Estado da Frota", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(anchor="w", pady=(0, 10))
        self.items_frota = {} 
        
        # Limites
        lats = [n['lat'] for n in grafo.nos.values()]
        lons = [n['lon'] for n in grafo.nos.values()]
        self.min_lat, self.max_lat = min(lats), max(lats)
        self.min_lon, self.max_lon = min(lons), max(lons)
        
        self.desenhar_mapa_base()

    def set_simulador(self, sim):
        self.simulador = sim

    def toggle_pause(self):
        if self.simulador:
            is_paused = self.simulador.toggle_pause()
            if is_paused: self.btn_pause.config(text="▶ CONTINUAR", bg="green")
            else: self.btn_pause.config(text="⏸ PAUSA", bg="orange")

    def mudar_velocidade(self, val):
        if self.simulador: self.simulador.set_delay(1.0 / int(val))

    def _criar_item_legenda(self, cor, texto):
        f = tk.Frame(self.painel_info, bg="#f0f0f0")
        f.pack(anchor="w", pady=2)
        tk.Canvas(f, width=15, height=15, bg=cor, highlightthickness=0).pack(side="left", padx=5)
        tk.Label(f, text=texto, bg="#f0f0f0", font=("Arial", 9)).pack(side="left")

    def coords_para_pixel(self, lat, lon):
        if self.max_lat == self.min_lat: y_norm = 0.5
        else: y_norm = (lat - self.min_lat) / (self.max_lat - self.min_lat)
        if self.max_lon == self.min_lon: x_norm = 0.5
        else: x_norm = (lon - self.min_lon) / (self.max_lon - self.min_lon)
        x = self.margem + x_norm * (self.largura - 2 * self.margem)
        y = self.altura - (self.margem + y_norm * (self.altura - 2 * self.margem))
        return x, y

    def get_cor_transito(self, multiplicador):
        """Retorna uma cor em gradiente de cinza para vermelho."""
        if multiplicador <= 1.0: return "#CCCCCC"
        
        # Maximo de 1.75 -> Vermelho puro
        ratio = (multiplicador - 1.0) / (1.75 - 1.0)
        ratio = max(0.0, min(1.0, ratio))
        
        # Interpolação de Cinza (#CC) para Vermelho (#FF0000)
        # R: 204 -> 255
        # G: 204 -> 0
        # B: 204 -> 0
        r = int(204 + (255 - 204) * ratio)
        g = int(204 - 204 * ratio)
        b = int(204 - 204 * ratio)
        
        return f"#{r:02x}{g:02x}{b:02x}"

    def desenhar_mapa_base(self):
        self.canvas.delete("base")
        for origem, destinos in self.grafo.arestas.items():
            x1, y1 = self.coords_para_pixel(self.grafo.nos[origem]['lat'], self.grafo.nos[origem]['lon'])
            for destino, dados in destinos.items():
                x2, y2 = self.coords_para_pixel(self.grafo.nos[destino]['lat'], self.grafo.nos[destino]['lon'])
                
                # Cor dinâmica baseada no trânsito
                multiplicador = self.grafo.condicoes_transito.get((origem, destino), 1.0)
                cor = self.get_cor_transito(multiplicador)
                largura = 2 + int(multiplicador) 
                
                self.canvas.create_line(x1, y1, x2, y2, fill=cor, width=largura, tags="base")

        for id_no, info in self.grafo.nos.items():
            x, y = self.coords_para_pixel(info['lat'], info['lon'])
            cor = "#0066cc" if info.get('pode_carregar') else "#333333"
            self.canvas.create_oval(x-5, y-5, x+5, y+5, fill=cor, outline="", tags="base")
            self.canvas.create_text(x, y+12, text=id_no, font=("Arial", 8), fill="#555555", tags="base")

    def atualizar_estado(self, frota, pedidos_ativos, tempo_atual, descricoes_status):
        self.canvas.delete("dinamico")
        self.lbl_hora.config(text=tempo_atual.strftime("%H:%M:%S"))

        # 1. Painel Lateral
        for t_id, taxi in frota.items():
            status_text = descricoes_status.get(t_id, "Desconhecido")
            pct = taxi.autonomia_atual / taxi.autonomia_maxima
            pct = max(0.0, min(1.0, pct))
            
            if pct > 0.5: color_bar = "#4caf50" 
            elif pct > 0.2: color_bar = "#ff9800" 
            else: color_bar = "#f44336" 

            if t_id not in self.items_frota:
                frame = tk.Frame(self.painel_info, bg="white", bd=1, relief="solid")
                frame.pack(fill="x", pady=2, padx=2)
                f_head = tk.Frame(frame, bg="white")
                f_head.pack(fill="x", padx=5, pady=(2,0))
                tk.Label(f_head, text=f"{t_id} ({taxi.tipo.name[0:3]})", font=("Arial", 9, "bold"), bg="white").pack(side="left")
                lbl_pct = tk.Label(f_head, text="100%", font=("Arial", 8), bg="white", fg="gray")
                lbl_pct.pack(side="right")
                canvas_bar = tk.Canvas(frame, height=4, bg="#e0e0e0", highlightthickness=0)
                canvas_bar.pack(fill="x", padx=5, pady=2)
                bar_id = canvas_bar.create_rectangle(0, 0, 0, 4, fill=color_bar, width=0)
                lbl_desc = tk.Label(frame, text=status_text, font=("Arial", 8), bg="white", anchor="w", fg="#555555")
                lbl_desc.pack(fill="x", padx=5, pady=(0,2))
                self.items_frota[t_id] = {"lbl_desc": lbl_desc, "lbl_pct": lbl_pct, "canvas_bar": canvas_bar, "bar_id": bar_id}
            
            item = self.items_frota[t_id]
            item["lbl_desc"].config(text=status_text)
            item["lbl_pct"].config(text=f"{int(pct*100)}%")
            w_canvas = item["canvas_bar"].winfo_width()
            if w_canvas < 10: w_canvas = 260 
            item["canvas_bar"].coords(item["bar_id"], 0, 0, w_canvas * pct, 4)
            item["canvas_bar"].itemconfig(item["bar_id"], fill=color_bar)

        # 2. Mapa: Pedidos
        for p in pedidos_ativos:
            ox, oy = self.coords_para_pixel(self.grafo.nos[p.origem]['lat'], self.grafo.nos[p.origem]['lon'])
            dx, dy = self.coords_para_pixel(self.grafo.nos[p.destino]['lat'], self.grafo.nos[p.destino]['lon'])
            self.canvas.create_oval(ox-6, oy-6, ox+6, oy+6, fill=p.cor_mapa, outline="black", width=1, tags="dinamico")
            self.canvas.create_rectangle(dx-5, dy-5, dx+5, dy+5, outline=p.cor_mapa, width=2, tags="dinamico")
            self.canvas.create_line(ox, oy, dx, dy, fill=p.cor_mapa, dash=(2, 2), tags="dinamico")

        # 3. Mapa: Táxis
        for taxi in frota.values():
            tx, ty = self.coords_para_pixel(self.grafo.nos[taxi.localizacao_atual]['lat'], self.grafo.nos[taxi.localizacao_atual]['lon'])
            
            if taxi.estado == EstadoVeiculo.LIVRE: cor = "green"
            elif taxi.estado == EstadoVeiculo.A_CARREGAR: cor = "blue"
            elif taxi.estado == EstadoVeiculo.A_ABASTECER: cor = "purple"
            else: cor = "red"
            
            r = 8
            if taxi.tipo == TipoMotorizacao.COMBUSTAO:
                self.canvas.create_rectangle(tx-r, ty-r, tx+r, ty+r, fill=cor, outline="black", width=1, tags="dinamico")
            else:
                self.canvas.create_oval(tx-r, ty-r, tx+r, ty+r, fill=cor, outline="black", width=1, tags="dinamico")
            self.canvas.create_text(tx, ty, text=taxi.id_veiculo, font=("Arial", 7, "bold"), fill="white", tags="dinamico")

        self.update()