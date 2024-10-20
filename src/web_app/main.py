from typing import Any

from flask import render_template

from web_app import create_app

app = create_app()


@app.errorhandler(404)
def not_found_error(error: Any) -> tuple[str, int]:
    return render_template("404.html", message=error.description), 404


if __name__ == "__main__":
    app.run(debug=True)
