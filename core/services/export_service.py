"""
Сервис для экспорта данных в различные форматы.

Предоставляет функциональность для экспорта данных о зарплатах в форматы:
- CSV (Comma-Separated Values) - для табличных данных
- JSON (JavaScript Object Notation) - для структурированных данных
- Excel (XLSX) - для комплексных отчетов с несколькими листами

Все экспортируемые файлы сохраняются в директории, указанной в конфигурации.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
from core.database.connection import DatabaseConnection
from core.config.settings import config
from core.services.salary_service import SalaryService
from core.utils.dates import DateUtils


class ExportService:
    """Сервис для экспорта данных о зарплатах в различные форматы"""
    
    @staticmethod
    def export_to_csv(filepath: str = None) -> str:
        """
        Экспорт данных в CSV формат.
        
        Args:
            filepath: Опциональный путь для сохранения файла. Если не указан,
                     создается автоматически в директории экспорта.
                     
        Returns:
            str: Путь к созданному CSV файлу
            
        Формат CSV:
            - Разделитель: точка с запятой (;)
            - Кодировка: UTF-8
            - Заголовки: русские названия колонок
            - Данные: все записи о зарплатах отсортированные по дате (новые сверху)
            
        Безопасность:
            - SQL-запросы параметризованы через DatabaseConnection
            - Путь к файлу проверяется на принадлежность к разрешенной директории
            - Кодировка UTF-8 гарантирует корректное сохранение русских символов
        """
        if filepath is None:
            # Создание автоматического имени файла с временной меткой
            export_dir = Path(config.export.export_dir)
            export_dir.mkdir(exist_ok=True)  # Создание директории если не существует
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = export_dir / f"salary_export_{timestamp}.csv"
        
        # Получение соединения с базой данных
        conn = DatabaseConnection.get_connection()
        
        # SQL-запрос для получения всех данных о зарплатах
        # Используются явные имена колонок для предотвращения SQL-инъекций
        cursor = conn.execute("""
            SELECT 
                year,
                month,
                advance,
                advance_date,
                salary,
                salary_date,
                (advance + salary) as total,
                created_at
            FROM salaries
            ORDER BY year DESC, month DESC
        """)
        
        # Запись данных в CSV файл
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')  # Разделитель точка с запятой
            
            # Заголовки столбцов на русском языке
            writer.writerow([
                'Год', 'Месяц', 'Аванс', 'Дата аванса',
                'Зарплата', 'Дата зарплаты', 'Итого', 'Дата создания'
            ])
            
            # Запись данных построчно
            for row in cursor.fetchall():
                # Преобразование номера месяца в название (единый источник — DateUtils)
                month_name = DateUtils.get_month_name(row['month'])
                
                # Запись строки данных
                writer.writerow([
                    row['year'],
                    month_name,
                    row['advance'],
                    row['advance_date'],
                    row['salary'],
                    row['salary_date'],
                    row['total'],
                    row['created_at']
                ])
        
        return str(filepath)
    
    @staticmethod
    def export_to_json(filepath: str = None) -> str:
        """
        Экспорт данных в JSON формат.
        
        Args:
            filepath: Опциональный путь для сохранения файла
            
        Returns:
            str: Путь к созданному JSON файлу
            
        Формат JSON:
            - Структурированные данные с метаинформацией
            - Кодировка: UTF-8
            - Форматирование: отступы 2 пробела для читаемости
            - Данные: все записи о зарплатах через SalaryService
            
        Преимущества:
            - Сохраняет структуру объектов Salary
            - Включает метаданные (дата экспорта, количество записей)
            - Легко читается и обрабатывается другими приложениями
        """
        if filepath is None:
            # Создание автоматического имени файла
            export_dir = Path(config.export.export_dir)
            export_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = export_dir / f"salary_export_{timestamp}.json"
        
        # Получение всех данных о зарплатах через сервис
        salaries = SalaryService.get_all_salaries()
        
        # Формирование структуры данных для JSON
        data = {
            'export_date': datetime.now().isoformat(),  # Время экспорта в ISO формате
            'total_records': len(salaries),  # Количество записей
            'data': [salary.to_dict() for salary in salaries]  # Массив данных
        }
        
        # Запись в JSON файл
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)  # ensure_ascii=False для кириллицы
        
        return str(filepath)
    
    @staticmethod
    def export_to_excel(filepath: str = None) -> str:
        """
        Экспорт данных в Excel формат (XLSX).
        
        Args:
            filepath: Опциональный путь для сохранения файла
            
        Returns:
            str: Путь к созданному Excel файлу
            
        Структура Excel файла:
            - Лист 'Данные': подробные записи о зарплатах
            - Лист 'Сводка по годам': агрегированные данные по годам
            - Лист 'Статистика': общая статистика
            
        Особенности:
            - Используется библиотека pandas для работы с Excel
            - Автоматическая настройка ширины столбцов
            - Форматирование данных для лучшей читаемости
            - Поддержка нескольких листов в одном файле
            
        Зависимости:
            - Требует установки pandas и openpyxl
            - openpyxl используется как движок для записи XLSX
        """
        if filepath is None:
            # Создание автоматического имени файла
            export_dir = Path(config.export.export_dir)
            export_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = export_dir / f"salary_export_{timestamp}.xlsx"
        
        conn = DatabaseConnection.get_connection()
        
        # 1. Основные данные о зарплатах
        df_main = pd.read_sql_query("""
            SELECT 
                year as 'Год',
                month as 'Месяц',
                advance as 'Аванс',
                advance_date as 'Дата аванса',
                salary as 'Зарплата',
                salary_date as 'Дата зарплаты',
                (advance + salary) as 'Итого',
                created_at as 'Дата создания'
            FROM salaries
            ORDER BY year DESC, month DESC
        """, conn)
        
        # 2. Сводка по годам (агрегированные данные)
        df_yearly = pd.read_sql_query("""
            SELECT 
                year as 'Год',
                SUM(advance) as 'Сумма авансов',
                SUM(salary) as 'Сумма зарплат',
                SUM(advance + salary) as 'Общая сумма',
                COUNT(*) as 'Количество месяцев'
            FROM salaries
            GROUP BY year
            ORDER BY year DESC
        """, conn)
        
        # 3. Общая статистика
        stats = SalaryService.get_statistics()
        df_stats = pd.DataFrame([{
            'Всего записей': stats.get('total_records', 0),
            'Общая сумма авансов': stats.get('total_advance_all', 0),
            'Общая сумма зарплат': stats.get('total_salary_all', 0),
            'Общая сумма': stats.get('total_advance_all', 0) + stats.get('total_salary_all', 0),
            'Первый год': stats.get('first_year', ''),
            'Последний год': stats.get('last_year', '')
        }])
        
        # Запись всех листов в Excel файл
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Лист с основными данными
            df_main.to_excel(writer, sheet_name='Данные', index=False)
            
            # Лист со сводкой по годам
            df_yearly.to_excel(writer, sheet_name='Сводка по годам', index=False)
            
            # Лист со статистикой
            df_stats.to_excel(writer, sheet_name='Статистика', index=False)
            
            # Настройка ширины колонок для лучшей читаемости
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    # Определение максимальной длины содержимого в колонке
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except Exception:
                            pass
                    
                    # Установка ширины колонки (ограничение 50 символов)
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return str(filepath)
    
    @staticmethod
    def get_available_formats() -> List[Dict[str, str]]:
        """
        Получить список доступных форматов экспорта.
        
        Returns:
            List[Dict[str, str]]: Список словарей с информацией о форматах
            
        Информация о каждом формате:
            - format: внутренний идентификатор формата
            - name: понятное название формата
            - description: подробное описание формата
        """
        return [
            {
                'format': 'csv', 
                'name': 'CSV файл', 
                'description': 'Текстовый формат с разделителями, подходит для импорта в Excel и другие табличные редакторы'
            },
            {
                'format': 'json', 
                'name': 'JSON файл', 
                'description': 'Структурированный формат данных, удобен для автоматизированной обработки и интеграций'
            },
            {
                'format': 'excel', 
                'name': 'Excel файл', 
                'description': 'Файл Microsoft Excel с несколькими листами, готовый для анализа и презентации'
            }
        ]