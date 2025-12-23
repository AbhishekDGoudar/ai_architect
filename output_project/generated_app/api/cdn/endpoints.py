from flask import Blueprint
from services.cdn.cdn_service import CDNService

cdn_bp = Blueprint('cdn', __name__)

def init_cdn_routes(app):
    cdn_service = CDNService()
    app.register_blueprint(cdn_bp, url_prefix='/api/v1')