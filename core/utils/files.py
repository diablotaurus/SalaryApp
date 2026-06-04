"""
Утилиты для работы с файловой системой.

Содержит методы для создания директорий, работы с размерами файлов,
чтения/записи JSON файлов, копирования и удаления файлов.
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any
import json


class FileUtils:
    """Утилиты для работы с файлами и директориями"""
    
    @staticmethod
    def ensure_directory(directory_path: str) -> Path:
        """
        Создать директорию, если она не существует.
        
        Args:
            directory_path: Путь к директории
            
        Returns:
            Path: Объект Path созданной директории
            
        Особенности:
            - Создает все промежуточные директории (parents=True)
            - Не вызывает ошибку если директория уже существует (exist_ok=True)
        """
        path = Path(directory_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """
        Получить размер файла в байтах.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            int: Размер файла в байтах или 0 если файл не существует
            
        Безопасность:
            - Обработка исключений OSError при недоступности файла
            - Возврат 0 вместо выброса исключения
        """
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Форматировать размер файла в читаемом виде.
        
        Args:
            size_bytes: Размер файла в байтах
            
        Returns:
            str: Отформатированный размер с единицей измерения
            
        Единицы измерения:
            - B: байты (< 1024 байт)
            - KB: килобайты (< 1024 KB)
            - MB: мегабайты (< 1024 MB)
            - GB: гигабайты (< 1024 GB)
            - TB: терабайты
            
        Примеры:
            format_file_size(500) -> "500.00 B"
            format_file_size(1500) -> "1.46 KB"
            format_file_size(1500000) -> "1.43 MB"
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    @staticmethod
    def read_json(file_path: str) -> Dict[str, Any]:
        """
        Прочитать JSON файл.
        
        Args:
            file_path: Путь к JSON файлу
            
        Returns:
            Dict[str, Any]: Словарь с данными из файла или пустой словарь при ошибке
            
        Обработка ошибок:
            - FileNotFoundError: файл не существует
            - JSONDecodeError: файл содержит невалидный JSON
            
        Кодировка:
            - Всегда используется UTF-8 для корректной работы с русскими символами
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    @staticmethod
    def write_json(file_path: str, data: Dict[str, Any]) -> bool:
        """
        Записать данные в JSON файл.
        
        Args:
            file_path: Путь к JSON файлу
            data: Данные для записи
            
        Returns:
            bool: True если запись успешна, False при ошибке
            
        Форматирование:
            - ensure_ascii=False: сохранение русских символов как есть
            - indent=2: отступы для читаемости
            
        Безопасность:
            - Обработка любых исключений при записи
            - Возврат булевого результата вместо выброса исключения
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    @staticmethod
    def copy_file(src: str, dst: str) -> bool:
        """
        Скопировать файл с сохранением метаданных.
        
        Args:
            src: Путь к исходному файлу
            dst: Путь к целевому файлу
            
        Returns:
            bool: True если копирование успешно, False при ошибке
            
        Особенности:
            - Использует shutil.copy2 для сохранения метаданных (время создания, права доступа)
            - Обрабатывает все исключения
        """
        try:
            shutil.copy2(src, dst)
            return True
        except Exception:
            return False
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """
        Удалить файл.
        
        Args:
            file_path: Путь к удаляемому файлу
            
        Returns:
            bool: True если удаление успешно, False при ошибке
            
        Безопасность:
            - Проверка существования файла не выполняется (ошибка OSError обрабатывается)
            - Не удаляет директории, только файлы
        """
        try:
            os.remove(file_path)
            return True
        except OSError:
            return False
    
    @staticmethod
    def list_files(directory: str, pattern: str = "*") -> List[Path]:
        """
        Получить список файлов в директории по шаблону.
        
        Args:
            directory: Путь к директории
            pattern: Шаблон поиска (например, "*.txt", "*.json")
            
        Returns:
            List[Path]: Список объектов Path найденных файлов или пустой список при ошибке
            
        Примеры:
            list_files("/path", "*.txt") -> [Path("/path/file1.txt"), Path("/path/file2.txt")]
            list_files("/path", "data_*.json") -> [Path("/path/data_2024.json")]
        """
        try:
            path = Path(directory)
            return list(path.glob(pattern))
        except Exception:
            return []