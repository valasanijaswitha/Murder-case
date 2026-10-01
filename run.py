from flask import Flask, redirect, url_for
from app.models import db
from app.database import migrate_database
import os
import tempfile

def create_app():
    app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.urandom(32)
    database_path = os.path.join(app.instance_path, 'murder_case.db')
    if os.environ.get('VERCEL') == '1':
        database_path = os.path.join(tempfile.gettempdir(), 'murder_case.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + database_path.replace('\\', '/')
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///murder_case.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_PERMANENT'] = True

    db.init_app(app)

    with app.app_context():
        migrate_database(database_path)
        db.create_all()

    from app.routes.team import team_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    app.register_blueprint(team_bp, url_prefix='/team')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/')
    def index():
        return redirect(url_for('team.login'))

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)
