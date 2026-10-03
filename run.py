from flask import Flask, redirect, url_for
from app.models import db
from app.database import migrate_database
import os

def create_app():
    app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
    database_url = os.environ.get('DATABASE_URL')
    is_vercel = os.environ.get('VERCEL') == '1' or 'VERCEL_ENV' in os.environ or 'AWS_EXECUTION_ENV' in os.environ or bool(database_url and not database_url.startswith('sqlite'))
    secret_key = os.environ.get('SECRET_KEY')

    if is_vercel and not secret_key:
        raise RuntimeError('SECRET_KEY must be configured in the deployment environment. Do not use random keys.')
    if is_vercel and not os.environ.get('ADMIN_PASSWORD'):
        raise RuntimeError('ADMIN_PASSWORD must be configured in the deployment environment.')
    if is_vercel and not database_url:
        raise RuntimeError('DATABASE_URL must point to persistent PostgreSQL storage.')

    app.config['SECRET_KEY'] = secret_key or os.urandom(32)
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = is_vercel
    database_path = None
    if database_url:
        if database_url.startswith('postgres://'):
            database_url = 'postgresql://' + database_url[len('postgres://'):]
        if database_url.startswith('postgresql://'):
            database_url = 'postgresql+psycopg://' + database_url[len('postgresql://'):]
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    elif not is_vercel:
        database_path = os.path.join(app.instance_path, 'murder_case.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///murder_case.db'
    else:
        raise RuntimeError('Vercel deployments must use persistent PostgreSQL storage.')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}
    app.config['SESSION_PERMANENT'] = True

    db.init_app(app)

    with app.app_context():
        if database_path:
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
