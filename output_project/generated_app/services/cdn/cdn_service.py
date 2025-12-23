from flask import Flask
from services.cdn.edge_node import EdgeNode
from services.cdn.health_monitor import HealthMonitor

class CDNService:
    def __init__(self):
        self.app = Flask(__name__)
        self.edge_nodes = [EdgeNode(i) for i in range(3)]
        self.health_monitor = HealthMonitor()
        self._init_routes()

    def _init_routes(self):
        @self.app.route('/api/v1/video/<video_id>', methods=['GET'])
        def get_video(video_id):
            return {'status': 'OK', 'video_id': video_id}