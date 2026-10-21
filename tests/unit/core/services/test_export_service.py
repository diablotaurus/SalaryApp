import csv
import json
from datetime import datetime
from pathlib import Path

from core.config.settings import config
from core.models.salary import Salary
from core.repositories.salary_repository import SalaryRepository
from core.services.export_service import ExportService


def _seed_salary_row():
    SalaryRepository.save(
        Salary(
            year=2025,
            month=9,
            advance=11111.0,
            salary=22222.0,
            advance_date=datetime.strptime("10.09.2025", "%d.%m.%Y"),
            salary_date=datetime.strptime("25.09.2025", "%d.%m.%Y"),
        )
    )


def test_export_to_csv_creates_file_with_data(temp_db, tmp_path: Path):
    old_export_dir = config.export.export_dir
    config.export.export_dir = str(tmp_path)
    try:
        _seed_salary_row()
        filepath = ExportService.export_to_csv()
        file_path_obj = Path(filepath)

        assert file_path_obj.exists()
        assert file_path_obj.suffix == ".csv"
        # BOM: по нему Excel узнаёт UTF-8 и не показывает кириллицу «кракозябрами»
        assert file_path_obj.read_bytes().startswith(b"\xef\xbb\xbf")

        with file_path_obj.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f, delimiter=";"))

        assert len(rows) >= 2
        assert rows[0][0] == "Год"
        assert rows[1][0] == "2025"
        assert rows[1][1] == "Сентябрь"
        # Суммы с запятой — русский Excel читает их как числа
        assert (rows[1][2], rows[1][4], rows[1][6]) == ("11111,00", "22222,00", "33333,00")
    finally:
        config.export.export_dir = old_export_dir


def test_export_to_json_creates_structured_payload(temp_db, tmp_path: Path):
    old_export_dir = config.export.export_dir
    config.export.export_dir = str(tmp_path)
    try:
        _seed_salary_row()
        filepath = ExportService.export_to_json()
        file_path_obj = Path(filepath)

        assert file_path_obj.exists()
        assert file_path_obj.suffix == ".json"

        payload = json.loads(file_path_obj.read_text(encoding="utf-8"))
        assert "export_date" in payload
        assert payload["total_records"] >= 1
        assert isinstance(payload["data"], list)
        assert payload["data"][0]["year"] == 2025
    finally:
        config.export.export_dir = old_export_dir


def _export_excel(tmp_path: Path):
    from openpyxl import load_workbook

    old_export_dir = config.export.export_dir
    config.export.export_dir = str(tmp_path)
    try:
        filepath = Path(ExportService.export_to_excel())
    finally:
        config.export.export_dir = old_export_dir
    assert filepath.suffix == ".xlsx"
    return load_workbook(filepath)


def test_export_to_excel_writes_three_sheets_with_data(temp_db, tmp_path: Path):
    _seed_salary_row()

    workbook = _export_excel(tmp_path)

    assert workbook.sheetnames == ["Данные", "Сводка по годам", "Статистика"]
    data = workbook["Данные"]
    assert [cell.value for cell in data[1]] == [
        "Год", "Месяц", "Аванс", "Дата аванса", "Зарплата",
        "Дата зарплаты", "Итого", "Дата создания",
    ]
    assert [cell.value for cell in data[2]][:7] == [
        2025, 9, 11111.0, "2025-09-10", 22222.0, "2025-09-25", 33333.0,
    ]
    yearly = [cell.value for cell in workbook["Сводка по годам"][2]]
    assert yearly == [2025, 11111.0, 22222.0, 33333.0, 1]
    stats = [cell.value for cell in workbook["Статистика"][2]]
    assert stats == [1, 11111.0, 22222.0, 33333.0, 2025, 2025]


def test_export_to_excel_keeps_header_style(temp_db, tmp_path: Path):
    _seed_salary_row()

    header = _export_excel(tmp_path)["Данные"]["A1"]

    assert header.font.b is True
    assert header.border.left.style == "thin" and header.border.bottom.style == "thin"
    assert (header.alignment.horizontal, header.alignment.vertical) == ("center", "top")


def test_export_to_excel_works_on_empty_database(temp_db, tmp_path: Path):
    # Раньше суммы NULL из пустой таблицы складывались и экспорт падал с TypeError.
    workbook = _export_excel(tmp_path)

    assert workbook["Данные"].max_row == 1  # только заголовок
    assert [cell.value for cell in workbook["Статистика"][2]] == [0, 0, 0, 0, None, None]

