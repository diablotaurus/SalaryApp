"""
Сервис для работы с резервными копиями базы данных.

Обеспечивает создание, восстановление, удаление и управление резервными копиями.
Резервные копии хранятся в ZIP-архивах с метаданными и автоматически очищаются по истечении срока хранения.
"""

import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import zipfile
from core.database.connection import DatabaseConnection
from core.config.settings import config

logger = logging.getLogger(__name__)


class BackupService:
    """Сервис для создания и управления резервными копиями базы данных"""
    
    @staticmethod
    def create_backup(comment: str = "") -> str:
        """
        Создать резервную копию базы данных.
        
        Args:
            comment: Комментарий к резервной копии (для истории)
            
        Returns:
            str: Путь к созданной резервной копии
            
        Процесс создания:
            1. Создается ZIP-архив с базой данных
            2. Добавляются метаданные (дата, комментарий, версия приложения)
            3. Автоматически очищаются старые резервные копии
            
        Безопасность:
            - Проверка существования файла базы данных
            - Архивирование с использованием DEFLATE сжатия
            - Хранение только в разрешенной директории
        """
        # Создание директории для резервных копий если не существует
        backup_dir = Path(config.db.backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Генерация имени файла с временной меткой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"salary_backup_{timestamp}.zip"
        backup_path = backup_dir / backup_filename
        
        # Создание ZIP архива с базой данных
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Добавление файла базы данных в архив
            db_path = Path(config.db.path)
            if db_path.exists():
                zipf.write(db_path, db_path.name)
            
            # Создание метаданных резервной копии
            metadata = {
                'backup_date': datetime.now().isoformat(),  # Дата создания в ISO формате
                'comment': comment,  # Пользовательский комментарий
                'app_version': config.app.version,  # Версия приложения для совместимости
                'database_size': db_path.stat().st_size if db_path.exists() else 0  # Размер БД
            }
            
            # Запись метаданных в файл внутри архива
            import json
            metadata_str = json.dumps(metadata, ensure_ascii=False, indent=2)
            zipf.writestr('backup_info.json', metadata_str)
        
        # Автоматическая очистка старых резервных копий
        BackupService._cleanup_old_backups()
        
        return str(backup_path)
    
    @staticmethod
    def _cleanup_old_backups():
        """
        Удалить старые резервные копии согласно настройкам хранения.
        
        Политика хранения:
            - Хранение резервных копий заданное количество дней (по умолчанию 30)
            - Удаление происходит при создании новой резервной копии
            - Проверяется дата в имени файла (формат YYYYMMDD)
            
        Особенности:
            - Удаляются только файлы с паттерном 'salary_backup_*.zip'
            - Ошибки при удалении логируются, но не прерывают выполнение
        """
        backup_dir = Path(config.db.backup_dir)
        if not backup_dir.exists():
            return
        
        # Получение срока хранения из конфигурации
        retention_days = config.db.backup_retention_days
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        # Обработка всех файлов резервных копий
        for backup_file in backup_dir.glob("*.zip"):
            try:
                # Извлечение даты из имени файла (формат: salary_backup_YYYYMMDD_HHMMSS.zip)
                filename = backup_file.stem  # Имя файла без расширения
                if filename.startswith("salary_backup_"):
                    # Извлечение даты (первые 8 цифр после префикса)
                    date_str = filename[14:22]  # YYYYMMDD
                    file_date = datetime.strptime(date_str, "%Y%m%d")
                    
                    # Удаление если файл старше срока хранения
                    if file_date < cutoff_date:
                        backup_file.unlink()
                        logger.info("Deleted old backup: %s", backup_file)
            except Exception:
                logger.exception("Error processing backup file %s", backup_file)
    
    @staticmethod
    def list_backups() -> List[Dict[str, Any]]:
        """
        Получить список всех доступных резервных копий.
        
        Returns:
            List[Dict[str, Any]]: Список резервных копий с метаданными
            
        Метаданные каждой копии:
            - filename: Имя файла
            - path: Полный путь к файлу
            - size: Размер файла в байтах
            - created: Дата создания файла
            - modified: Дата последнего изменения
            
        Сортировка:
            - По умолчанию отсортированы по дате создания (новые сверху)
        """
        backup_dir = Path(config.db.backup_dir)
        if not backup_dir.exists():
            return []
        
        backups = []
        # Получение всех ZIP файлов, отсортированных по дате изменения (новые первые)
        for backup_file in sorted(backup_dir.glob("*.zip"), reverse=True):
            try:
                file_info = backup_file.stat()
                backups.append({
                    'filename': backup_file.name,
                    'path': str(backup_file),
                    'size': file_info.st_size,  # Размер в байтах
                    'created': datetime.fromtimestamp(file_info.st_ctime),  # Дата создания
                    'modified': datetime.fromtimestamp(file_info.st_mtime)   # Дата изменения
                })
            except Exception:
                logger.exception("Error reading backup info for %s", backup_file)

        return backups
    
    @staticmethod
    def restore_backup(backup_path: str) -> bool:
        """
        Восстановить базу данных из резервной копии.
        
        Args:
            backup_path: Путь к файлу резервной копии
            
        Returns:
            bool: True если восстановление успешно, False в случае ошибки
            
        Процесс восстановления:
            1. Закрытие текущих соединений с БД
            2. Создание резервной копии текущей базы (на случай отката)
            3. Распаковка резервной копии
            4. Замена текущей базы данных
            
        Меры предосторожности:
            - Создается временная копия текущей базы перед восстановлением
            - В случае ошибки можно восстановить предыдущее состояние
            - Проверка наличия файла базы данных в архиве
        """
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                return False
            
            # Закрытие текущего соединения с БД для избежания блокировок
            DatabaseConnection.close_connection()
            
            # Создание резервной копии текущей базы данных перед восстановлением
            current_db = Path(config.db.path)
            if current_db.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_backup = current_db.parent / f"salary_pre_restore_{timestamp}.bak"
                shutil.copy2(current_db, temp_backup)  # Копирование с сохранением метаданных
            
            # Распаковка резервной копии
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                # Поиск файла базы данных в архиве
                db_files = [f for f in zipf.namelist() if f.endswith('.db')]
                if not db_files:
                    return False
                
                # Извлечение базы данных из архива
                zipf.extract(db_files[0], current_db.parent)
                
                # Переименование если имя файла отличается от ожидаемого
                extracted_db = current_db.parent / db_files[0]
                if extracted_db != current_db:
                    if current_db.exists():
                        current_db.unlink()  # Удаление старой базы
                    extracted_db.rename(current_db)  # Переименование извлеченной базы
            
            return True
        except Exception:
            logger.exception("Error restoring backup")
            return False
        finally:
            # Восстановление соединения с базой данных
            DatabaseConnection.get_connection()
    
    @staticmethod
    def delete_backup(backup_path: str) -> bool:
        """
        Удалить резервную копию.
        
        Args:
            backup_path: Путь к файлу резервной копии
            
        Returns:
            bool: True если удаление успешно, False в случае ошибки
            
        Безопасность:
            - Проверка существования файла перед удалением
            - Обработка исключений при удалении
            - Логирование ошибок
        """
        try:
            backup_file = Path(backup_path)
            if backup_file.exists():
                backup_file.unlink()
                return True
            return False
        except Exception:
            logger.exception("Error deleting backup")
            return False
    
    @staticmethod
    def get_backup_info(backup_path: str) -> Dict[str, Any]:
        """
        Получить подробную информацию о резервной копии.
        
        Args:
            backup_path: Путь к файлу резервной копии
            
        Returns:
            Dict[str, Any]: Словарь с информацией о резервной копии
            
        Информация включает:
            - Основные метаданные файла (размер, даты)
            - Метаданные из backup_info.json (если есть)
            - Размер в мегабайтах для удобства чтения
        """
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                return {}
            
            # Получение базовой информации о файле
            file_info = backup_file.stat()
            info = {
                'filename': backup_file.name,
                'path': str(backup_file),
                'size': file_info.st_size,  # Размер в байтах
                'size_mb': round(file_info.st_size / (1024 * 1024), 2),  # Размер в МБ
                'created': datetime.fromtimestamp(file_info.st_ctime),  # Дата создания
                'modified': datetime.fromtimestamp(file_info.st_mtime)   # Дата изменения
            }
            
            # Чтение дополнительных метаданных из архива
            try:
                with zipfile.ZipFile(backup_file, 'r') as zipf:
                    if 'backup_info.json' in zipf.namelist():
                        import json
                        with zipf.open('backup_info.json') as f:
                            metadata = json.load(f)
                            info.update(metadata)  # Добавление метаданных в общую информацию
            except Exception:
                pass  # Если не удалось прочитать метаданные, продолжаем без них

            return info
        except Exception:
            logger.exception("Error getting backup info")
            return {}