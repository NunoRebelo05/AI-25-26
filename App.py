import customtkinter as ctk
from PIL import Image
import os
import sys

# Ensure we can import from local directories
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from views.HomeView import HomeView
from views.SimulationView import SimulationView
from views.AlgorithmsView import AlgorithmsView

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    """
    Ponto de Entrada da Aplicação (Main Entry Point).
    
    Responsável pela orquestração de janelas, injeção de dependências e configuração
    do ciclo de vida da interface gráfica (Tkinter Mainloop).
    """
    def __init__(self):
        super().__init__()

        self.title("TaxiGreen Simulator")
        self.geometry("1100x700")
        
        # Maximize window
        self.after(0, lambda: self.state('zoomed'))
        
        # Handle close event
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Configure grid layout (1x2)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Load assets
        self.image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        self.logo_image = ctk.CTkImage(Image.open(os.path.join(self.image_path, "taxi.png")), size=(26, 26))
        self.add_image = ctk.CTkImage(Image.open(os.path.join(self.image_path, "add.png")), size=(20, 20))
        self.algo_image = ctk.CTkImage(Image.open(os.path.join(self.image_path, "algorithm.png")), size=(20, 20))

        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="  TaxiGreen", image=self.logo_image,
                                       compound="left", font=ctk.CTkFont(size=15, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=20)

        self.btn_home = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=40, border_spacing=10, text="Início",
                                      fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                      image=self.logo_image, anchor="w", command=self.show_home)
        self.btn_home.grid(row=1, column=0, sticky="ew")

        self.btn_sim = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=40, border_spacing=10, text="Nova Simulação",
                                     fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                     image=self.add_image, anchor="w", command=self.show_simulation)
        self.btn_sim.grid(row=2, column=0, sticky="ew")

        self.btn_algo = ctk.CTkButton(self.sidebar_frame, corner_radius=0, height=40, border_spacing=10, text="Algoritmos",
                                      fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                      image=self.algo_image, anchor="w", command=self.show_algorithms)
        self.btn_algo.grid(row=3, column=0, sticky="ew")
        
        # Appearance Mode
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Tema:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["System", "Light", "Dark"],
                                                             command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 20))

        # --- Content Area ---
        self.home_view = HomeView(self)
        self.sim_view = SimulationView(self)
        self.algo_view = AlgorithmsView(self)

        self.select_frame_by_name("home")

    def select_frame_by_name(self, name):
        # Update button colors
        self.btn_home.configure(fg_color=("gray75", "gray25") if name == "home" else "transparent")
        self.btn_sim.configure(fg_color=("gray75", "gray25") if name == "sim" else "transparent")
        self.btn_algo.configure(fg_color=("gray75", "gray25") if name == "algo" else "transparent")

        # Show selected frame
        if name == "home":
            self.home_view.grid(row=0, column=1, sticky="nsew")
        else:
            self.home_view.grid_forget()
            
        if name == "sim":
            self.sim_view.grid(row=0, column=1, sticky="nsew")
        else:
            self.sim_view.grid_forget()
            
        if name == "algo":
            self.algo_view.grid(row=0, column=1, sticky="nsew")
        else:
            self.algo_view.grid_forget()

    def show_home(self):
        self.select_frame_by_name("home")

    def show_simulation(self):
        self.select_frame_by_name("sim")

    def show_algorithms(self):
        self.select_frame_by_name("algo")

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def on_close(self):
        """
        Gestor de Encerramento (Graceful Shutdown).
        
        Garante a terminação correta de threads de simulação e libertação de recursos gráficos
        antes de destruir a janela principal, prevenindo 'Zombie Threads' e falhas de runtime.
        """
        try:
            if hasattr(self, 'sim_view') and self.sim_view:
                self.sim_view.stop_simulation()
        except Exception as e:
            print(f"Error checking sim_view on close: {e}")
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
