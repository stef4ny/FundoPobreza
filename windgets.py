import customtkinter as ctk
import ctypes
from typing import Optional, Tuple, List
from win10toast import ToastNotifier

class StatusCard(ctk.CTkFrame):
    """Card de status personalizado"""
    def __init__(self, master, title: str, **kwargs):
        super().__init__(master, **kwargs)
        self.title_label = ctk.CTkLabel(self, text=title, font=("Arial", 10))
        self.value_label = ctk.CTkLabel(self, text="N/A", font=("Arial", 12, "bold"))
        self.title_label.pack(pady=(5,0))
        self.value_label.pack(pady=(0,5))

    def update_value(self, value: str, color: Optional[str] = None):
        self.value_label.configure(text=value)
        if color:
            self.value_label.configure(text_color=color)

class NotificationManager:
    """Gerencia notificações do Windows"""
    @staticmethod
    def show_balloon(title: str, message: str, icon: int = 1):
        """Ícones: 1=Info, 2=Warning, 3=Error"""
        try:
            ctypes.windll.user32.MessageBoxW(0, message, title, icon)
        except Exception as e:
            print(f"Erro na notificação: {e}")

    @staticmethod
    def show_toast(title: str, message: str, duration: int = 5):
        """Notificação estilo Toast (Windows 10/11)"""
        try:
            ToastNotifier().show_toast(title, message, duration=duration)
        except:
            NotificationManager.show_balloon(title, message)