import os

from app.routes import register_routes
from flask import Flask

app = Flask(__name__)
register_routes(app)

if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    app.run(host=host, port=port, debug=False)
