from flask import Flask

from .routes.home import home_bp
from .routes.player_matches import player_bp
from .routes.player_rankings import ranking_bp
from .routes.team import team_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "your_secret_key"

    # Register Blueprints
    app.register_blueprint(home_bp)
    app.register_blueprint(player_bp, url_prefix="/player")
    app.register_blueprint(team_bp, url_prefix="/team")
    app.register_blueprint(ranking_bp, url_prefix="/ranking")

    return app
