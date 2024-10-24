from flask import Flask, g, render_template
from sqlalchemy.orm import Session
from werkzeug.middleware.proxy_fix import ProxyFix

from shared.config.settings import settings
from shared.database.database import Database
from shared.logging.logging import web_app_logger
from web_app.routes.home import home_bp
from web_app.routes.player_matches import player_bp  # type: ignore
from web_app.routes.player_rankings import ranking_bp
from web_app.routes.team import team_bp


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=None,
        subdomain_matching=True,
    )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)  # type: ignore

    app.static_folder = str(settings.STATIC_FOLDER)
    # fix for static files not found (404) due to missing subdomain
    app.add_url_rule(
        "/static/<path:filename>",
        endpoint="static",
        subdomain="btfv",
        view_func=app.send_static_file,
    )

    # initialize database
    db = Database.instance(settings=settings)
    db.init_flask_app(app)

    # app config
    app.logger = web_app_logger
    # app.config["SQLALCHEMY_DATABASE_URI"] = settings.SYNC_URL
    app.config["FLASK_SECRET_KEY"] = settings.FLASK_SECRET_KEY
    # app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SERVER_NAME"] = settings.SERVER_NAME

    # fix for static files not found (404) due to missing subdomain
    app.add_url_rule(
        "/static/<path:filename>",
        endpoint="static",
        subdomain="btfv",
        view_func=app.send_static_file,
    )

    # Register blueprints for modular routing
    app.register_blueprint(home_bp, subdomain="btfv")
    app.register_blueprint(player_bp, url_prefix="/player", subdomain="btfv")
    app.register_blueprint(ranking_bp, url_prefix="/ranking", subdomain="btfv")
    app.register_blueprint(team_bp, url_prefix="/team", subdomain="btfv")

    @app.before_request
    def inject_session() -> None:
        session: Session = db.get_sync_session()
        g.db_session = session

    @app.teardown_request
    def remove_session(e: BaseException | None = None) -> None:
        g.pop("db_session", None)

    @app.errorhandler(404)
    def page_not_found(
        e: BaseException | None = None,
    ) -> tuple[str, int]:
        return render_template("404.html"), 404

    return app


app = create_app()
