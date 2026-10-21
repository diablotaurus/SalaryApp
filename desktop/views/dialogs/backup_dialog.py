import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Any
from core.utils.files import FileUtils
from desktop.widgets.dialogs import BaseDialog
from desktop.widgets.window_centering import center_on_main_window
from desktop.views.constants import BACKUP_COMMENT_LABELS, BUTTON_DIALOG_WIDTH, PADX_DEFAULT


class BackupDialog(BaseDialog):
    """Диалоговое окно для работы с резервными копиями"""
    
    def __init__(self, parent, controller):
        # Вызываем конструктор базового класса
        super().__init__(parent, "Резервные копии")
        
        self.controller = controller
        self.parent = parent
        self.backups_list = []
        
        # Создаем интерфейс
        self._create_widgets()

        # Загружаем список резервных копий
        self._load_backups()

        # Размер окна и положение по центру главного окна — после построения содержимого
        self._center_on_main_window(800, 600)
    
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
        
        # Treeview (колонка «Изменен» заменена комментарием: у копии она всегда равна «Создан»)
        columns = ("filename", "comment", "size", "created")
        self.tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings"
        )

        # Настраиваем колонки
        self.tree.heading("filename", text="Имя файла")
        self.tree.heading("comment", text="Комментарий")
        self.tree.heading("size", text="Размер")
        self.tree.heading("created", text="Создан")

        self.tree.column("filename", width=270, stretch=False)
        self.tree.column("comment", width=250, stretch=True)
        self.tree.column("size", width=80, anchor=tk.E, stretch=False)
        self.tree.column("created", width=120, anchor=tk.CENTER, stretch=False)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Панель действий (по центру)
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))

        action_buttons = ttk.Frame(action_frame)
        action_buttons.pack(anchor=tk.CENTER)

        # Кнопка Восстановить
        self.restore_button = ttk.Button(
            action_buttons,
            text="Восстановить",
            command=self._restore_backup,
            state=tk.DISABLED,
            style="Success.TButton",
            width=BUTTON_DIALOG_WIDTH
        )
        self.restore_button.pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))

        # Кнопка Удалить
        self.delete_button = ttk.Button(
            action_buttons,
            text="Удалить",
            command=self._delete_backup,
            state=tk.DISABLED,
            style="Danger.TButton",
            width=BUTTON_DIALOG_WIDTH
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
            size_bytes = backup.get('size_bytes', 0)
            created = backup.get('created', '')

            # Форматируем даты
            if isinstance(created, datetime):
                created = created.strftime("%d.%m.%Y %H:%M")

            self.tree.insert('', tk.END, values=(
                filename,
                self._format_comment(backup.get('comment')),
                # KB/MB по размеру: «0.00 MB» для небольшой базы ничего не говорил
                FileUtils.format_file_size(size_bytes),
                created,
            ))

    @staticmethod
    def _format_comment(comment: Any) -> str:
        """Комментарий для списка: в одну строку, служебные метки — понятным текстом."""
        text = " ".join(str(comment or "").split())
        return BACKUP_COMMENT_LABELS.get(text, text)
    
    def _create_backup(self):
        """Создать резервную копию"""
        # Создаем диалог для ввода комментария (модальный; BaseDialog
        # ставит его по центру главного окна — раньше он появлялся в углу экрана)
        comment_dialog = BaseDialog(self, "Создание резервной копии")

        # Виджеты
        main_frame = ttk.Frame(comment_dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Комментарий (необязательно):").pack(anchor=tk.W, pady=(0, 10))
        
        comment_text = tk.Text(main_frame, height=4, width=40)
        comment_text.pack(fill=tk.BOTH, pady=(0, 20))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        buttons_container = ttk.Frame(button_frame)
        buttons_container.pack(anchor=tk.CENTER)

        def create():
            comment = comment_text.get("1.0", tk.END).strip()
            if self.controller.create_backup(comment):
                comment_dialog.destroy()
                self._load_backups()

        ttk.Button(buttons_container, text="Создать", command=create,
                   width=BUTTON_DIALOG_WIDTH).pack(side=tk.LEFT, padx=(0, PADX_DEFAULT))
        ttk.Button(buttons_container, text="Отмена", command=comment_dialog.destroy,
                   width=BUTTON_DIALOG_WIDTH).pack(side=tk.LEFT)

        center_on_main_window(comment_dialog, 400, 200)
        
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
                    f"Текущие данные будут заменены. Перед восстановлением автоматически "
                    f"создаётся резервная копия текущей базы — к ней можно будет вернуться."
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
