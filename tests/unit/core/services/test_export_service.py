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

        with file_path_obj.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f, delimiter=";"))

        assert len(rows) >= 2
        assert rows[0][0] == "Год"
        assert rows[1][0] == "2025"
        assert rows[1][1] == "Сентябрь"
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


def test_get_available_formats_contains_expected_ids():
    formats = ExportService.get_available_formats()
    ids = {item["format"] for item in formats}
    assert {"csv", "json", "excel"}.issubset(ids)

