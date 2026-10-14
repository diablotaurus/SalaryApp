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
from typing import Any, Dict, Iterable, List, Sequence
from core.config.settings import config
from core.repositories.analytics_repository import AnalyticsRepository
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
            
        Формат CSV (рассчитан на открытие двойным кликом в русском Excel):
            - Разделитель: точка с запятой (;)
            - Кодировка: UTF-8 с BOM — без него Excel показывает кириллицу
              «кракозябрами» (правило «UTF-8 без BOM» относится к исходникам
              проекта, а не к пользовательским выгрузкам)
            - Суммы: два знака, запятая в дробной части — Excel читает их как числа
            - Заголовки: русские названия колонок
            - Данные: все записи о зарплатах отсортированные по дате (новые сверху)
        """
        if filepath is None:
            # Создание автоматического имени файла с временной меткой
            export_dir = Path(config.export.export_dir)
            export_dir.mkdir(exist_ok=True)  # Создание директории если не существует
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = export_dir / f"salary_export_{timestamp}.csv"
        
        salaries = SalaryService.get_all_salaries()
        
        # Запись данных в CSV файл (utf-8-sig добавляет BOM для Excel)
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')  # Разделитель точка с запятой
            
            # Заголовки столбцов на русском языке
            writer.writerow([
                'Год', 'Месяц', 'Аванс', 'Дата аванса',
                'Зарплата', 'Дата зарплаты', 'Итого', 'Дата создания'
            ])
            
            # Запись данных построчно
            for salary_record in salaries:
                writer.writerow([
                    salary_record.year,
                    DateUtils.get_month_name(salary_record.month),
                    ExportService._csv_amount(salary_record.advance),
                    salary_record.advance_date.date().isoformat() if salary_record.advance_date else "",
                    ExportService._csv_amount(salary_record.salary),
                    salary_record.salary_date.date().isoformat() if salary_record.salary_date else "",
                    ExportService._csv_amount(salary_record.total),
                    salary_record.created_at.isoformat(sep=" ") if salary_record.created_at else "",
                ])

        return str(filepath)

    @staticmethod
    def _csv_amount(amount: float) -> str:
        """Сумма для CSV: два знака и запятая в дробной части (так её понимает русский Excel)."""
        return f"{amount:.2f}".replace(".", ",")
    
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
            - Файл пишется напрямую через openpyxl (без pandas)
            - Заголовки оформлены как раньше: жирный шрифт, тонкая рамка,
              выравнивание по центру и по верху
            - Автоматическая настройка ширины столбцов (до 50 символов)

        Зависимости:
            - openpyxl импортируется только здесь: его загрузка занимает ~0.7 с,
              и при импорте модуля она замедляла бы запуск всех приложений
        """
        if filepath is None:
            # Создание автоматического имени файла
            export_dir = Path(config.export.export_dir)
            export_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = export_dir / f"salary_export_{timestamp}.xlsx"

        from openpyxl import Workbook

        salaries = SalaryService.get_all_salaries()
        data_rows = [
            [
                item.year,
                item.month,
                item.advance,
                item.advance_date.date().isoformat() if item.advance_date else None,
                item.salary,
                item.salary_date.date().isoformat() if item.salary_date else None,
                round(item.total, 2),
                item.created_at.isoformat(sep=" ") if item.created_at else None,
            ]
            for item in salaries
        ]

        yearly_rows = [
            [
                item["year"],
                item["total_advance"],
                item["total_salary"],
                item["total"],
                item["months_count"],
            ]
            for item in AnalyticsRepository.get_yearly_totals()
        ]

        # Общая статистика. Для пустой базы SQL-суммы равны NULL (None) —
        # раньше их сложение падало с TypeError, и экспорт без данных не работал.
        stats = SalaryService.get_statistics()
        total_advance = stats.get('total_advance_all') or 0
        total_salary = stats.get('total_salary_all') or 0
        stats_rows = [[
            stats.get('total_records') or 0,
            total_advance,
            total_salary,
            round(total_advance + total_salary, 2),
            stats.get('first_year'),
            stats.get('last_year'),
        ]]

        workbook = Workbook()
        workbook.remove(workbook.active)  # пустой лист по умолчанию не нужен
        ExportService._write_sheet(
            workbook, 'Данные',
            ['Год', 'Месяц', 'Аванс', 'Дата аванса', 'Зарплата',
             'Дата зарплаты', 'Итого', 'Дата создания'],
            data_rows,
        )
        ExportService._write_sheet(
            workbook, 'Сводка по годам',
            ['Год', 'Сумма авансов', 'Сумма зарплат', 'Общая сумма', 'Количество месяцев'],
            yearly_rows,
        )
        ExportService._write_sheet(
            workbook, 'Статистика',
            ['Всего записей', 'Общая сумма авансов', 'Общая сумма зарплат',
             'Общая сумма', 'Первый год', 'Последний год'],
            stats_rows,
        )
        workbook.save(filepath)

        return str(filepath)

    @staticmethod
    def _write_sheet(
        workbook: Any,
        title: str,
        headers: Sequence[str],
        rows: Iterable[Sequence[Any]],
    ) -> None:
        """Добавить лист: оформленный заголовок, строки данных, ширина колонок по содержимому."""
        from openpyxl.styles import Alignment, Border, Font, Side

        sheet = workbook.create_sheet(title)
        sheet.append(list(headers))
        for row in rows:
            sheet.append(list(row))

        thin = Side(style="thin")
        for cell in sheet[1]:
            cell.font = Font(bold=True)
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
            cell.alignment = Alignment(horizontal="center", vertical="top")

        # Ширина колонки — по самому длинному значению (ограничение 50 символов)
        for column in sheet.columns:
            max_length = max(len("" if cell.value is None else str(cell.value)) for cell in column)
            sheet.column_dimensions[column[0].column_letter].width = min(max_length + 2, 50)
    
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
