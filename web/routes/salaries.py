"""
API routes for salary operations.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

from api.salary_api import SalaryAPI
from core.config.settings import config
from core.utils.dates import DateUtils
from web.routes.response import finalize_response, payload_from_exception

salaries_bp = Blueprint("salaries_api", __name__)


@salaries_bp.route("/api/salaries", methods=["GET"])
def get_salaries():
    try:
        payload, status = finalize_response(SalaryAPI.get_all_salaries(), is_production=config.app.is_production)
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@salaries_bp.route("/api/salary", methods=["POST"])
def add_salary():
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            payload, status = finalize_response(
                {"success": False, "message": "JSON body is required", "error": "required"},
                is_production=config.app.is_production,
            )
            return jsonify(payload), status

        payload, status = finalize_response(
            SalaryAPI.add_salary(
                data.get("year"),
                data.get("month"),
                data.get("advance", 0),
                data.get("salary", 0),
                data.get("advance_date"),
                data.get("salary_date"),
            ),
            is_production=config.app.is_production,
        )
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@salaries_bp.route("/api/salary/<int:year>/<int:month>", methods=["GET"])
def get_salary(year, month):
    try:
        payload, status = finalize_response(
            SalaryAPI.get_salary(year, month),
            is_production=config.app.is_production,
        )
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@salaries_bp.route("/api/salaries_by_year", methods=["GET"])
def get_salaries_by_year():
    try:
        year = request.args.get("year", type=int)
        if year:
            payload, status = finalize_response(
                SalaryAPI.get_salaries_by_year(year),
                is_production=config.app.is_production,
            )
        else:
            payload, status = finalize_response(
                {"success": False, "message": "Year parameter is required", "error": "required"},
                is_production=config.app.is_production,
            )
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@salaries_bp.route("/api/statistics", methods=["GET"])
def get_statistics():
    try:
        year = request.args.get("year", type=int)
        payload, status = finalize_response(
            SalaryAPI.get_statistics(year),
            is_production=config.app.is_production,
        )
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@salaries_bp.route("/api/forecast", methods=["GET"])
def forecast():
    """Прогноз итога текущего года по МСК (data=null — прогноза нет)."""
    try:
        year, _ = DateUtils.get_current_period()
        payload, status = finalize_response(
            SalaryAPI.forecast_year(year),
            is_production=config.app.is_production,
        )
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@salaries_bp.route("/api/years", methods=["GET"])
def get_years():
    try:
        payload, status = finalize_response(SalaryAPI.get_years(), is_production=config.app.is_production)
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@salaries_bp.route("/api/year_summary", methods=["GET"])
def get_year_summary():
    try:
        year = request.args.get("year", type=int)
        if year:
            payload, status = finalize_response(
                SalaryAPI.get_year_summary(year),
                is_production=config.app.is_production,
            )
        else:
            payload, status = finalize_response(
                {"success": False, "message": "Year parameter is required", "error": "required"},
                is_production=config.app.is_production,
            )
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@salaries_bp.route("/api/chart/<chart_type>", methods=["GET"])
def get_chart_data(chart_type):
    try:
        year = request.args.get("year", type=int)
        if chart_type == "monthly":
            payload, status = finalize_response(
                SalaryAPI.get_monthly_series_dto(year),
                is_production=config.app.is_production,
            )
        elif chart_type == "yearly_comparison":
            payload, status = finalize_response(
                SalaryAPI.get_yearly_comparison_dto(),
                is_production=config.app.is_production,
            )
        elif chart_type == "growth_rate":
            payload, status = finalize_response(
                SalaryAPI.get_growth_rate_dto(),
                is_production=config.app.is_production,
            )
        elif chart_type == "average_by_month":
            payload, status = finalize_response(
                SalaryAPI.get_average_by_month_dto(),
                is_production=config.app.is_production,
            )
        else:
            payload, status = finalize_response(
                {
                    "success": False,
                    "message": f'Chart type "{chart_type}" is not supported',
                    "error": "invalid",
                },
                is_production=config.app.is_production,
            )
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@salaries_bp.route("/api/best_periods", methods=["GET"])
def get_best_periods():
    try:
        payload, status = finalize_response(
            SalaryAPI.get_best_periods(),
            is_production=config.app.is_production,
        )
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@salaries_bp.route("/api/export", methods=["GET"])
def export_data():
    try:
        format_type = request.args.get("format", "excel")
        payload, status = finalize_response(
            SalaryAPI.export_data(format_type),
            is_production=config.app.is_production,
        )
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)

    if payload.get("success"):
        export_file = Path(payload["data"]["filepath"])

        if format_type == "excel":
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif format_type == "csv":
            mimetype = "text/csv"
        elif format_type == "json":
            mimetype = "application/json"
        else:
            mimetype = "application/octet-stream"

        # Файл отдаётся из памяти и сразу удаляется: иначе каждая выгрузка
        # из браузера оставляла в exports/ копию финансовых данных.
        content = export_file.read_bytes()
        export_file.unlink(missing_ok=True)

        return send_file(
            BytesIO(content),
            as_attachment=True,
            download_name=export_file.name,
            mimetype=mimetype,
        )

    return jsonify(payload), status


@salaries_bp.route("/api/backup", methods=["POST"])
def create_backup():
    try:
        data = request.get_json(silent=True) or {}
        comment = data.get("comment", "")
        payload, status = finalize_response(
            SalaryAPI.create_backup(comment),
            is_production=config.app.is_production,
        )
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@salaries_bp.route("/api/backups", methods=["GET"])
def list_backups():
    try:
        payload, status = finalize_response(
            SalaryAPI.list_backups(),
            is_production=config.app.is_production,
        )
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@salaries_bp.route("/api/backup/restore", methods=["POST"])
def restore_backup():
    try:
        data = request.get_json(silent=True) or {}
        reference = str(data.get("filename", "")).strip()
        payload, status = finalize_response(
            SalaryAPI.restore_backup(reference),
            is_production=config.app.is_production,
        )
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@salaries_bp.route("/api/backup", methods=["DELETE"])
def delete_backup():
    try:
        data = request.get_json(silent=True) or {}
        reference = str(data.get("filename", "")).strip()
        payload, status = finalize_response(
            SalaryAPI.delete_backup(reference),
            is_production=config.app.is_production,
        )
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status


@salaries_bp.route("/api/delete_year", methods=["DELETE"])
def delete_year():
    try:
        year = request.args.get("year", type=int)
        if year:
            payload, status = finalize_response(
                SalaryAPI.delete_year(year),
                is_production=config.app.is_production,
            )
        else:
            payload, status = finalize_response(
                {"success": False, "message": "Year parameter is required", "error": "required"},
                is_production=config.app.is_production,
            )
    except Exception as exc:  # fallback at route boundary
        payload, status = payload_from_exception(exc, is_production=config.app.is_production)
    return jsonify(payload), status
