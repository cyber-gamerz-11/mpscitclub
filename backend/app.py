import os
from flask import Flask, render_template, send_from_directory, request
from flask_login import LoginManager
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key_123')
    
    # Login Manager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from backend.models.user import User
        return User.get_by_id(user_id)

    # Register Blueprints
    from backend.routes.auth_routes import auth_bp
    from backend.routes.event_routes import event_bp
    from backend.routes.payment_routes import payment_bp
    from backend.routes.user_routes import user_bp
    from backend.routes.admin_routes import admin_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(event_bp, url_prefix='/events')
    app.register_blueprint(payment_bp, url_prefix='/payments')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Aggressive Caching for Static Files
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000

    @app.after_request
    def add_cache_headers(response):
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response

    # Main Routes
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/about')
    def about():
        return render_template('about.html')

    @app.route('/ec-panel')
    def ec_panel():
        return render_template('ec-panel.html')

    @app.route('/gallery')
    def gallery():
        return render_template('gallery.html')

    @app.route('/events')
    def events_page():
        return render_template('events.html')

    @app.route('/programs')
    def programs():
        return render_template('programs.html')

    @app.route('/contact')
    def contact():
        return render_template('contact.html')

    @app.route('/user/dashboard')
    def dashboard():
        return render_template('dashboard.html')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
