import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import List, Dict, Any
from desktop.widgets.dialogs import BaseDialog


class BackupDialog(BaseDialog):
    """Диалоговое окно для работы с резервными копиями"""
    
    def __init__(self, parent, controller):
        # Вызываем конструктор базового класса
        super().__init__(parent, "Резервные копии")
        
        self.controller = controller
        self.parent = parent
        self.backups_list = []
        
        # Настройка окна
        self.geometry("800x600")
        self._center_on_parent()
        
        # Создаем интерфейс
        self._create_widgets()
        
        # Загружаем список резервных копий
        self._load_backups()
    
    def _create_widgets(self):
        """Создать виджеты"""
        # Основной контейнер
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Панель управления
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Кнопка Создать резервную копию
        create_button = ttk.Button(
            control_frame,
            text="Создать резервную копию",
            command=self._create_backup,
            style="Primary.TButton"
        )
        create_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Кнопка Обновить список
        refresh_button = ttk.Button(
            control_frame,
            text="Обновить список",
            command=self._load_backups
        )
        refresh_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Кнопка Закрыть
        close_button = ttk.Button(
            control_frame,
            text="Закрыть",
            command=self.destroy
        )
        close_button.pack(side=tk.LEFT)
        
        # Список резервных копий
        list_frame = ttk.LabelFrame(main_frame, text="Список резервных копий", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Создаем Treeview с прокруткой
        tree_container = ttk.Frame(list_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        # Treeview
        columns = ("filename", "size", "created", "modified")
        self.tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings"
        )
        
        # Настраиваем колонки
        self.tree.heading("filename", text="Имя файла")
        self.tree.heading("size", text="Размер")
        self.tree.heading("created", text="Создан")
        self.tree.heading("modified", text="Изменен")
        
        self.tree.column("filename", width=360, stretch=True)
        self.tree.column("size", width=80, anchor=tk.E, stretch=False)
        self.tree.column("created", width=120, anchor=tk.CENTER, stretch=False)
        self.tree.column("modified", width=120, anchor=tk.CENTER, stretch=False)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Панель действий
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Кнопка Восстановить
        self.restore_button = ttk.Button(
            action_frame,
            text="Восстановить",
            command=self._restore_backup,
            state=tk.DISABLED,
            style="Success.TButton"
        )
        self.restore_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Кнопка Удалить
        self.delete_button = ttk.Button(
            action_frame,
            text="Удалить",
            command=self._delete_backup,
            state=tk.DISABLED,
            style="Danger.TButton"
        )
        self.delete_button.pack(side=tk.LEFT)
        
        # Привязываем событие выбора
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        
        # Контекстное меню
        self._create_context_menu()
    
    def _create_context_menu(self):
        """Создать контекстное меню"""
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(
            label="Восстановить",
            command=self._restore_backup,
            state=tk.DISABLED
        )
        self.context_menu.add_command(
            label="Удалить",
            command=self._delete_backup,
            state=tk.DISABLED
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="Обновить список",
            command=self._load_backups
        )
        
        # Привязываем событие правой кнопки мыши
        self.tree.bind("<Button-3>", self._show_context_menu)
    
    def _show_context_menu(self, event):
        """Показать контекстное меню"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def _on_tree_select(self, event):
        """Обработчик выбора в дереве"""
        selection = self.tree.selection()
        if selection:
            self.restore_button.config(state=tk.NORMAL)
            self.delete_button.config(state=tk.NORMAL)
            # Обновляем контекстное меню
            self.context_menu.entryconfig("Восстановить", state=tk.NORMAL)
            self.context_menu.entryconfig("Удалить", state=tk.NORMAL)
        else:
            self.restore_button.config(state=tk.DISABLED)
            self.delete_button.config(state=tk.DISABLED)
            # Обновляем контекстное меню
            self.context_menu.entryconfig("Восстановить", state=tk.DISABLED)
            self.context_menu.entryconfig("Удалить", state=tk.DISABLED)
    
    def _load_backups(self):
        """Загрузить список резервных копий"""
        # Очищаем текущие данные
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Получаем список резервных копий
        self.backups_list = self.controller.get_backups_list()
        
        # Добавляем в дерево
        for backup in self.backups_list:
            filename = backup.get('filename', '')
            size_mb = backup.get('size_mb', 0)
            created = backup.get('created', '')
            modified = backup.get('modified', '')
            
            # Форматируем даты
            if isinstance(created, datetime):
                created = created.strftime("%d.%m.%Y %H:%M")
            if isinstance(modified, datetime):
                modified = modified.strftime("%d.%m.%Y %H:%M")
            
            self.tree.insert('', tk.END, values=(
                filename,
                f"{size_mb:.2f} MB",
                created,
                modified
            ))
    
    def _create_backup(self):
        """Создать резервную копию"""
        # Создаем диалог для ввода комментария
        comment_dialog = tk.Toplevel(self)
        comment_dialog.title("Создание резервной копии")
        comment_dialog.geometry("400x200")
        comment_dialog.transient(self)
        comment_dialog.grab_set()
        
        # Виджеты
        main_frame = ttk.Frame(comment_dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Комментарий (необязательно):").pack(anchor=tk.W, pady=(0, 10))
        
        comment_text = tk.Text(main_frame, height=4, width=40)
        comment_text.pack(fill=tk.BOTH, pady=(0, 20))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        def create():
            comment = comment_text.get("1.0", tk.END).strip()
            if self.controller.create_backup(comment):
                comment_dialog.destroy()
                self._load_backups()
        
        ttk.Button(button_frame, text="Создать", command=create).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Отмена", command=comment_dialog.destroy).pack(side=tk.LEFT)
        
        comment_text.focus_set()
    
    def _restore_backup(self):
        """Восстановить из резервной копии"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.tree.item(item, 'values')
        
        if values:
            filename = values[0]
            
            # Находим полный путь
            backup = next((b for b in self.backups_list if b.get('filename') == filename), None)
            
            if backup:
                if messagebox.askyesno(
                    "Подтверждение",
                    f"Вы уверены, что хотите восстановить базу данных из резервной копии?\n\n"
                    f"Файл: {filename}\n\n"
                    f"Текущие данные будут заменены. Рекомендуется создать резервную копию перед восстановлением."
                ):
                    if self.controller.restore_backup(backup['path']):
                        self.destroy()
    
    def _delete_backup(self):
        """Удалить резервную копию"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.tree.item(item, 'values')
        
        if values:
            filename = values[0]
            
            # Находим полный путь
            backup = next((b for b in self.backups_list if b.get('filename') == filename), None)
            
            if backup:
                if messagebox.askyesno(
                    "Подтверждение",
                    f"Вы уверены, что хотите удалить резервную копию?\n\n"
                    f"Файл: {filename}"
                ):
                    if self.controller.delete_backup(backup['path']):
                        self._load_backups()
