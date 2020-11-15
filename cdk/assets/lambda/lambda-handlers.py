import json
import logging
import os

import apig_wsgi
import domdiv
from flask import Flask, request, send_file, url_for
from flask import render_template

# from flask_wtf.csrf import CSRFProtect
from domdiv_form import DomDivForm
from tuckbox_form import TuckboxForm

PAGES = [
    ("", "Dominion Dividers"),
    ("chitboxes", "Bits Boxes"),
    ("tuckboxes", "Card Tuckboxes"),
]

flask_app = Flask(__name__)

secret_key = os.environ["FLASK_SECRET_KEY"]
assert secret_key, "Need secret key specified in env"
flask_app.config["SECRET_KEY"] = secret_key

logger = logging.getLogger("bgtools_logger")
logger.setLevel(int(os.environ.get("LOG_LEVEL", logging.INFO)))

apig_wsgi_handler = apig_wsgi.make_lambda_handler(flask_app, binary_support=True)

if os.environ.get("DEBUG"):
    apig_wsgi_handler_helper = apig_wsgi_handler
    def apig_wsgi_handler(event, context):
        logger.info("in apig handler")        
        print(json.dumps(event, indent=2, sort_keys=True))
        response = apig_wsgi_handler_helper(event, context)
        print(json.dumps(response, indent=2, sort_keys=True))
        return response



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
        buf = form.generate()
        r = send_file(
            buf,
            mimetype="application/pdf",
            as_attachment=True,
            attachment_filename="sumpfork_dominion_dividers.pdf",
        )
        logger.info(f"response: {r}")
        return r

    r = render_template(
        "index.html",
        pages=PAGES,
        form=form,
        active="domdiv",
        static_url=os.environ["STATIC_WEB_URL"],
        version=domdiv.__version__,
        version_url=f"https://github.com/sumpfork/dominiontabs/releases/tag/v{domdiv.__version__}",
        form_target=url_for("root")
    )
    return r


@flask_app.route("/tuckboxes/", methods=["GET", "POST"])
def tuckboxes():
    form = TuckboxForm(request.form)
    logger.info("in tuckboxes!")
    if form.validate_on_submit():
        buf = form.generate()
        r = send_file(
            buf,
            mimetype="application/pdf",
            as_attachment=True,
            attachment_filename="sumpfork_tuckbox.pdf"
        )
        logger.info(f"response: {r}")
        return r
    r = render_template(
        "index.html",
        pages=PAGES,
        form=form,
        active="tuckboxes",
        static_url=os.environ["STATIC_WEB_URL"],
        form_target=url_for("tuckboxes")
    )
    return r

@flask_app.route("/chitboxes/", methods=["GET", "POST"])
def chitboxes():
    logger.info("in chitboxes!")
    return {"statusCode": 200, "body": "chitboxes"}


if __name__ == "__main__":
    flask_app.run(debug=True)
