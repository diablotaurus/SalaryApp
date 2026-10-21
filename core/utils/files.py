"""
Утилиты для работы с файловой системой.

Содержит методы для создания директорий, работы с размерами файлов,
чтения/записи JSON файлов, копирования и удаления файлов.
"""



class FileUtils:
    """Утилиты для работы с файлами и директориями"""
    
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
    