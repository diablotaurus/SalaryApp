"""
Error handlers.
"""
from flask import Blueprint, jsonify, render_template, request

errors_bp = Blueprint("errors", __name__)


@errors_bp.app_errorhandler(404)
def page_not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify({
            "success": False,
            "data": None,
            "message": "API endpoint not found",
            "error": "not found",
        }), 404
    return render_template("404.html"), 404


@errors_bp.app_errorhandler(500)
def internal_server_error(_error):
    if request.path.startswith("/api/"):
        return jsonify({
            "success": False,
            "data": None,
            "message": "Internal server error",
            "error": None,
        }), 500
    return render_template("500.html"), 500
