from io import BytesIO
import logging
import os

from flask_lambda import FlaskLambda
from flask import request, send_file, make_response
from flask import render_template
from flask_wtf import FlaskForm

# from flask_wtf.csrf import CSRFProtect
import wtforms.fields as wtf_fields
import domdiv.main

PAGES = [
    ("domdiv", "Dominion Dividers"),
    ("chitboxes", "Bits Boxes"),
    ("tuckboxes", "Card Tuckboxes"),
]

flask_app = FlaskLambda(__name__)
# CSRFProtect(flask_app)
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
        default=[choices[0]],
    )

    orientation = wtf_fields.SelectField(
        label="Divider Orientation", choices=["Horizontal", "Vertical"]
    )


@flask_app.route("/", methods=["GET", "POST"])
def root():
    logger.info(f"root call, request is {request}, form is {request.form}")
    # logger.info(f"session: {session} {session.get('csrf_token')}")
    logger.info(request)
    form = DomDivForm(request.form)
    logger.info(f"{form} - validate: {form.validate_on_submit()}")
    logger.info(f"submitted: {form.is_submitted()}")
    logger.info(f"validates: {form.validate()}")
    logger.info(f"errors: {form.errors}")

    if form.validate_on_submit():
        options = domdiv.main.parse_opts([])
        logger.info(f"options before populate: {options}")
        logger.info(f"expansions data: {form['expansions'].data}")
        form.populate_obj(options)
        options.expansions = [[e] for e in form["expansions"].data]
        logger.info(f"expansions data: {form['expansions'].data}")
        logger.info(f"options after populate: {options}")
        options = domdiv.main.clean_opts(options)
        logger.info(f"options after cleaning: {options}")
        buf = BytesIO()
        options.outfile = buf
        domdiv.main.generate(options)
        logger.info("done generation, returning pdf")
        r = make_response(buf.getvalue())
        r.headers['Content-Type'] = 'application/pdf'
        r.headers['Content-Disposition'] = 'attachment; filename="sumpfork_dominion_dividers.pdf"'
        logger.info(f"response: {r}")
        return r
        # return send_file(
        #     buf,
        #     mimetype="application/pdf",
        #     as_attachment=True,
        #     attachment_filename="sumpfork_dominion_dividers.pdf".encode("utf-8"),
        # )
    r = render_template(
        "index.html",
        pages=PAGES,
        form=form,
        active="domdiv",
        static_url=os.environ["STATIC_WEB_URL"],
    )
    return r


@flask_app.route("/bar/", methods=["GET"])
def bar():
    logger.info("in bar!")
    return {"statusCode": 200, "body": "bar!"}


def generate(event, context):
    print("I'm running generate!")


if __name__ == "__main__":
    flask_app.run(debug=True)
