"""
Error handlers.
"""
from flask import Blueprint, render_template

errors_bp = Blueprint("errors", __name__)


@errors_bp.app_errorhandler(404)
def page_not_found(_error):
    return render_template("404.html"), 404


@errors_bp.app_errorhandler(500)
def internal_server_error(_error):
    return render_template("500.html"), 500
