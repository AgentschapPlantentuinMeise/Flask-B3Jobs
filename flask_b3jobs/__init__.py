# builtin
import os
import logging
# flask imports
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_fefset import FEFset
from flask_uxfab import UXFab
from flask_iam import IAM
from flask_iam.utils import root_required, role_required
from flask_apium import Apium
from celery.result import AsyncResult

db = SQLAlchemy()
fef = FEFset(frontend='bootstrap4')
uxf = UXFab()
iam = IAM(db)

def gcreate_app():
    logging.basicConfig(level=logging.INFO)
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config['SECRET_KEY'] = os.urandom(12).hex() # to allow csrf forms
    fef.init_app(app)
    db.init_app(app)
    uxf.init_app(app)
    iam.init_app(app)
    app.config.from_mapping(
        CELERY=dict(
            broker_url='sqla+sqlite:////tmp/celery.db', #"redis://localhost",
            result_backend='db+sqlite:////tmp/celery.db', #"redis://localhost",
            task_ignore_result=True,
        ),
    )
    logging.info('Flask and celery app name %s', __name__)
    apium = Apium(__name__)
    apium.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route('/')
    def index():
        return render_template('index.html')

    @apium.task(ignore_result=False)
    def add_together(a: int, b: int) -> int:
        return a + b

    @app.get("/add")
    def start_add() -> dict[str, object]:
        a = 2#request.form.get("a", type=int)
        b = 3#request.form.get("b", type=int)
        result = add_together.delay(a, b)
        return {"result_id": result.id}

    @app.get("/result/<id>")
    def task_result(id: str) -> dict[str, object]:
        result = AsyncResult(id)
        return {
            "ready": result.ready(),
            "successful": result.successful(),
            "value": result.result if result.ready() else None,
        }

    return app

if __name__ == '__main__' or os.environ.get('CREATE_CELERY_APP', False):
    flask_app = gcreate_app()
    celery_app = flask_app.extensions['apium'].celery_app
