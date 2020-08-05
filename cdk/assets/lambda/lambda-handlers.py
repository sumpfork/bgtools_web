import logging
import os

from flask_lambda import FlaskLambda
from flask import request

flask_app = FlaskLambda(__name__)

logger = logging.getLogger("bgtools_logger")
logger.setLevel(int(os.environ.get("LOG_LEVEL", logging.INFO)))


@flask_app.route("/", methods=["GET"])
def root():
    logger.info("in root!")
    logger.info(request)
    data = {
        "form": dict(request.form.copy()),
        "args": dict(request.args.copy()),
        "json": request.json,
    }
    logger.info(data)
    return data


def bar(event, context):
    logger.info("in bar!")
    logger.info(event)
    logger.info(context)
    return {"statusCode": 200, "body": "bar!"}


def generate(event, context):
    print("I'm running generate!")


if __name__ == "__main__":
    flask_app.run(debug=True)

