from tkinter import ttk


class BaseView(ttk.Frame):
    """Базовое представление"""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self._create_widgets()
    
    def _create_widgets(self):
        """Создать виджеты (должен быть переопределен)"""
        pass
    
    def update_data(self, data):
        """Обновить данные (может быть переопределен)"""
        pass