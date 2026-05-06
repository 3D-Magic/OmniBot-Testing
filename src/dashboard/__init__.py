"""
Dashboard Module
Flask blueprint for the web dashboard
"""
from flask import Blueprint

dashboard_bp = Blueprint('dashboard', __name__, template_folder='templates', static_folder='static')

# Import routes after blueprint creation
from . import routes
