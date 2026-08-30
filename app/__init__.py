import os
from pathlib import Path
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

db=SQLAlchemy(); login_manager=LoginManager(); csrf=CSRFProtect()

def create_app():
    app=Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY','dev-only-change-me'),
        SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL','sqlite:////data/echovault.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=500*1024*1024,
        MEDIA_ROOT=os.getenv('MEDIA_ROOT','/media'),
        ALLOW_REGISTRATION=os.getenv('ALLOW_REGISTRATION','true').lower()=='true')
    Path(app.config['MEDIA_ROOT']).mkdir(parents=True,exist_ok=True)
    db.init_app(app); login_manager.init_app(app); csrf.init_app(app)
    login_manager.login_view='login'
    app.wsgi_app=ProxyFix(app.wsgi_app,x_for=1,x_proto=1,x_host=1)
    from .routes import register_routes
    register_routes(app)
    with app.app_context():
        from .models import User
        db.create_all()
        admin=os.getenv('ADMIN_USER','admin')
        if not User.query.filter_by(username=admin).first():
            u=User(username=admin,is_admin=True); u.set_password(os.getenv('ADMIN_PASSWORD','change-me-now'))
            db.session.add(u); db.session.commit()
    return app
