import customtkinter as ctk
import sys
import os
from PIL import Image

# Ensure we can import other modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from launcher import AppLauncher
from main import BenchmarkWindow

ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class MainMenu(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TaxiGreen Simulator")
        self.geometry("800x500")
        
        # Grid configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1) # Title area
        self.grid_rowconfigure(1, weight=2) # Buttons area
        self.grid_rowconfigure(2, weight=0) # Footer area

        # --- Title Section ---
        self.frame_title = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_title.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(40, 20))
        
        self.lbl_title = ctk.CTkLabel(self.frame_title, text="TaxiGreen", font=("Roboto Medium", 48))
        self.lbl_title.pack()
        
        self.lbl_subtitle = ctk.CTkLabel(self.frame_title, text="simulator", font=("Roboto", 24), text_color="gray")
        self.lbl_subtitle.pack()

        # --- Buttons Section ---
        # Button 1: Nova Simulação
        self.btn_simulation = ctk.CTkButton(
            self, 
            text="Nova Simulação", 
            font=("Roboto Medium", 20),
            width=250, 
            height=150,
            corner_radius=20,
            fg_color="#9E9E9E", # Grayish like the image
            hover_color="#757575",
            command=self.open_simulation
        )
        self.btn_simulation.grid(row=1, column=0, padx=20, pady=20)

        # Button 2: Algoritmos
        self.btn_algorithms = ctk.CTkButton(
            self, 
            text="Algoritmos", 
            font=("Roboto Medium", 20),
            width=250, 
            height=150,
            corner_radius=20,
            fg_color="#9E9E9E",
            hover_color="#757575",
            command=self.open_algorithms
        )
        self.btn_algorithms.grid(row=1, column=1, padx=20, pady=20)

        # --- Footer Section ---
        self.lbl_footer = ctk.CTkLabel(
            self, 
            text="Inteligência Artificial | Universidade do Minho 2025/26", 
            font=("Roboto", 12), 
            text_color="gray"
        )
        self.lbl_footer.grid(row=2, column=0, columnspan=2, pady=20)

    def open_simulation(self):
        """Opens the Simulation Launcher window."""
        # Check if window is already open
        if hasattr(self, 'sim_window') and self.sim_window is not None and self.sim_window.winfo_exists():
            self.sim_window.focus()
        else:
            self.sim_window = AppLauncher(self) # Pass self as parent if needed, or just as master
            self.sim_window.grab_set() # Make it modal if desired, or just focus

    def open_algorithms(self):
        """Opens the Algorithms Benchmark window."""
        if hasattr(self, 'algo_window') and self.algo_window is not None and self.algo_window.winfo_exists():
            self.algo_window.focus()
        else:
            self.algo_window = BenchmarkWindow(self)
            self.algo_window.grab_set()

if __name__ == "__main__":
    app = MainMenu()
    app.mainloop()
