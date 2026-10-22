"""
Page routes.
"""
from flask import Blueprint, render_template

from core.models.extra_payment import EXTRA_KINDS

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    # Виды доп. выплат — для списка в форме месяца
    return render_template("index.html", extra_kinds=EXTRA_KINDS)


@pages_bp.route("/reports")
def reports():
    return render_template("reports.html")


@pages_bp.route("/settings")
def settings():
    return render_template("settings.html")
