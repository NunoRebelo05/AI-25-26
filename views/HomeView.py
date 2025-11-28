import customtkinter as ctk

class HomeView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.frame_content = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_content.grid(row=0, column=0)
        
        self.lbl_title = ctk.CTkLabel(self.frame_content, text="TaxiGreen", font=("Roboto Medium", 48))
        self.lbl_title.pack()
        
        self.lbl_subtitle = ctk.CTkLabel(self.frame_content, text="simulator", font=("Roboto", 24), text_color="gray")
        self.lbl_subtitle.pack()
        
        self.lbl_info = ctk.CTkLabel(self.frame_content, text="\nBem-vindo ao simulador de frota de táxis.\nSelecione uma opção no menu lateral para começar.", 
                                     font=("Roboto", 16))
        self.lbl_info.pack(pady=30)
