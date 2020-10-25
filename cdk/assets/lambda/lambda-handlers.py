import logging
import os

from flask_lambda import FlaskLambda
from flask import request
from flask import render_template
from flask_wtf import FlaskForm
import wtforms.fields as wtf_fields
import domdiv.main

PAGES = [
    ("domdiv", "Dominion Dividers"),
    ("chitboxes", "Bits Boxes"),
    ("tuckboxes", "Card Tuckboxes"),
]

flask_app = FlaskLambda(__name__)
secret_key = os.environ["FLASK_SECRET_KEY"]
assert secret_key, "Need secret key specified in env"
flask_app.config["SECRET_KEY"] = secret_key

logger = logging.getLogger("bgtools_logger")
logger.setLevel(int(os.environ.get("LOG_LEVEL", logging.INFO)))


class DomDivForm(FlaskForm):
    # Expansions
    choices = domdiv.main.EXPANSION_CHOICES
    # make pretty names for the expansion choices
    choiceNames = []
    replacements = {
        "1stedition": "1st Edition",
        "2ndeditionupgrade": "2nd Edition Upgrade",
        "2ndedition": "2nd Edition",
    }
    for choice in choices:
        for s, r in replacements.items():
            if choice.lower().endswith(s):
                choiceNames.append("{} {}".format(choice[: -len(s)].capitalize(), r))
                break
        else:
            choiceNames.append(choice.capitalize())
    expansions = wtf_fields.SelectMultipleField(
        choices=list(zip(choices, choiceNames)),
        label="Expansions to Include (Cmd/Ctrl click to select multiple)",
    )

    orientation = wtf_fields.SelectField(
        label="Divider Orientation", choices=["Horizontal", "Vertical"]
    )


@flask_app.route("/", methods=["GET"])
def root():
    logger.info(request)
    form = DomDivForm()
    if form.validate_on_submit():
        return
    return render_template(
        "index.html",
        pages=PAGES,
        form=form,
        active="domdiv",
        static_url=os.environ["STATIC_WEB_URL"],
    )


@flask_app.route("/bar/", methods=["GET"])
def bar():
    logger.info("in bar!")
    return {"statusCode": 200, "body": "bar!"}


def generate(event, context):
    print("I'm running generate!")


if __name__ == "__main__":
    flask_app.run(debug=True)
