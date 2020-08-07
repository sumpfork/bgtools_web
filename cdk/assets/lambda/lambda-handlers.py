import logging
import os

from flask_lambda import FlaskLambda
from flask import request
from flask import render_template

PAGES = [
    ("domdiv", "Dominion Dividers"),
    ("chitboxes", "Bits Boxes"),
    ("tuckboxes", "Card Tuckboxes"),
]

flask_app = FlaskLambda(__name__)

logger = logging.getLogger("bgtools_logger")
logger.setLevel(int(os.environ.get("LOG_LEVEL", logging.INFO)))


@flask_app.route("/", methods=["GET"])
def root():
    logger.info("in root!")
    logger.info(request)
    return render_template(
        "index.html",
        pages=PAGES,
        active="domdiv",
        static_url=os.environ["STATIC_WEB_URL"],
    )


def bar(event, context):
    logger.info("in bar!")
    logger.info(event)
    logger.info(context)
    return {"statusCode": 200, "body": "bar!"}


def generate(event, context):
    print("I'm running generate!")


if __name__ == "__main__":
    flask_app.run(debug=True)

