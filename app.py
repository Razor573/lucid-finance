import os
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from dotenv import load_dotenv

load_dotenv()

def create_app(test_config=None):
    app = Flask(__name__)
    
    env = os.environ.get('FLASK_ENV', 'development')
    if test_config is not None:
        app.config.from_mapping(test_config)
    elif env == 'production':
        app.config.from_object('config.ProductionConfig')
        if not app.config.get('SECRET_KEY') or app.config.get('SECRET_KEY') == 'dev-fallback-key-38d7c2a1':
            raise RuntimeError("SECRET_KEY environment variable must be set in production mode!")
    else:
        app.config.from_object('config.DevelopmentConfig')
        
    from models import db, User
    db.init_app(app)
    
    csrf = CSRFProtect(app)
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        
    from forms import LogoutForm
    @app.context_processor
    def inject_logout_form():
        return dict(logout_form=LogoutForm())
        
    from routes.auth import auth_bp
    from routes.transactions import transactions_bp
    from routes.dashboard import dashboard_bp
    from routes.stocks import stocks_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(stocks_bp)
    
    # reset rate limits for testing
    from flask import jsonify, abort
    @app.route('/dev/reset-rate-limits', methods=['POST'])
    @csrf.exempt
    def dev_reset_rate_limits():
        if not app.config.get('DEBUG'):
            abort(404)
        from utils.rate_limiter import reset_rate_limits
        reset_rate_limits()
        return jsonify({'status': 'success'})
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(429)
    def rate_limit_error(error):
        return render_template('429.html'), 429

    @app.errorhandler(500)
    def internal_error(error):
        try:
            from models import db
            db.session.rollback()
        except Exception:
            pass
        return render_template('500.html'), 500
        
    @app.after_request
    def add_security_headers(response):
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com https://unpkg.com; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        if os.environ.get('FLASK_ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
        # No-Cache for auth pages
        from flask_login import current_user
        try:
            if current_user.is_authenticated:
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
        except Exception:
            pass
            
        response.headers['Vary'] = 'Cookie'
        return response
        
    return app
