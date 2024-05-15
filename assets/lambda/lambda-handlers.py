import argparse
import base64
from io import BytesIO
import json
import os
import sys

from loguru import logger
import apig_wsgi
import domdiv
import domdiv.main
import domdiv.db
import domdiv.config_options

from flask import Flask, request, send_file, url_for, jsonify, abort
from flask import render_template
from flask_bootstrap import Bootstrap4
from flask_uploads import IMAGES

from domdiv_form import DomDivForm
from tuckbox_form import TuckboxForm
from chitbox_form import ChitboxForm
from argparse2form import ArgParse2FormWrapper

PAGES = {
    "dominion_dividers": "Dominion Dividers",
    "dominion_dividers_advanced": "Dominion Dividers (Advanced)",
    "chitboxes": "Bits Boxes",
    "tuckboxes": "Card Tuckboxes",
}

flask_app = Flask(__name__)
bootstrap = Bootstrap4(flask_app)

secret_key = os.environ["FLASK_SECRET_KEY"]
assert secret_key, "Need secret key specified in env"
flask_app.config["SECRET_KEY"] = secret_key
flask_app.config["UPLOADS_DEFAULT_DEST"] = "/tmp"
flask_app.config["UPLOADED_FILES_ALLOW"] = IMAGES
flask_app.config["WTF_CSRF_ENABLED"] = False

logger.remove()
logger.add(sys.stderr, level=os.environ.get("LOG_LEVEL", "INFO"))

apig_wsgi_handler = apig_wsgi.make_lambda_handler(flask_app, binary_support=True)

if os.environ.get("DEBUG"):
    apig_wsgi_handler_helper = apig_wsgi_handler

    def apig_wsgi_handler(event, context):
        logger.info("in apig handler")
        print(json.dumps(event, indent=2, sort_keys=True))
        response = apig_wsgi_handler_helper(event, context)
        print(json.dumps(response, indent=2, sort_keys=True))
        return response


def get_pages():
    return {url_for(p): n for p, n in PAGES.items()}


@flask_app.route("/", methods=["GET", "POST"])
def dominion_dividers():
    logger.info(f"root call, request is {request}, form is {request.form}")
    # logger.info(f"session: {session} {session.get('csrf_token')}")
    logger.info(f"env is: {os.environ}")
    form = DomDivForm(font_dir=os.environ.get("FONT_DIR"))
    logger.info(f"{form} - validate: {form.validate_on_submit()}")
    logger.info(f"submitted: {form.is_submitted()}")
    logger.info(f"validates: {form.validate()}")
    logger.info(f"errors: {form.errors}")

    logger.info(f"domdiv version: {domdiv.__version__}")
    logger.info(f"expansion choices: {domdiv.db.get_expansions()}")
    if form.validate_on_submit():
        buf = form.generate()
        r = send_file(
            buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="sumpfork_dominion_dividers.pdf",
        )
        logger.info(f"response: {r}")
        return r

    # setting the default doesn't seem to work, so override here
    form.expansions.data = ["dominion2ndEdition"]
    form.process()

    r = render_template(
        "index.html",
        pages=PAGES,
        form=form,
        active="dominion_dividers",
        static_url=os.environ["STATIC_WEB_URL"],
        version=domdiv.__version__,
        version_url=f"https://github.com/sumpfork/dominiontabs/releases/tag/v{domdiv.__version__}",
        form_target=url_for("dominion_dividers"),
        ga_config=os.environ.get("GA_CONFIG", ""),
    )
    return r


@flask_app.route("/advanced", methods=["GET", "POST"])
def dominion_dividers_advanced():
    logger.info(f"root call, request is {request}, form is {request.form}")
    # logger.info(f"session: {session} {session.get('csrf_token')}")
    logger.info(f"env is: {os.environ}")
    argparsewrapper = ArgParse2FormWrapper
    argparsewrapper.exclude_args("Miscellaneous", "log_level", "preview_resolution")

    form = domdiv.config_options.parse_opts(parser=argparsewrapper)
    # form = DomDivForm(font_dir=os.environ.get("FONT_DIR"))
    logger.info(f"{form} - validate: {form.validate_on_submit()}")
    logger.info(f"submitted: {form.is_submitted()}")
    logger.info(f"validates: {form.validate()}")
    logger.info(f"errors: {form.errors}")

    logger.info(f"domdiv version: {domdiv.__version__}")
    logger.info(f"expansion choices: {domdiv.db.get_expansions()}")

    if form.validate_on_submit():
        form_options = argparse.Namespace()
        form.populate_obj(form_options)
        buf = BytesIO()
        form_options.outfile = buf
        domdiv.main.generate(form_options)
        buf.seek(0)
        r = send_file(
            buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="sumpfork_dominion_dividers.pdf",
        )
        logger.info(f"response: {r}")
        return r

    form.process()

    r = render_template(
        "index.html",
        pages=PAGES,
        form=form,
        active="dominion_dividers_advanced",
        static_url=os.environ["STATIC_WEB_URL"],
        version=domdiv.__version__,
        version_url=f"https://github.com/sumpfork/dominiontabs/releases/tag/v{domdiv.__version__}",
        form_target=url_for("dominion_dividers_advanced"),
        ga_config=os.environ.get("GA_CONFIG", ""),
    )
    return r


@flask_app.route("/tuckboxes/", methods=["GET", "POST"])
def tuckboxes():
    form = TuckboxForm()
    logger.info(f"in tuckboxes, form validates: {form.validate_on_submit()}")
    logger.info(f"errors: {form.errors}")

    logger.info(f"file: {form.front_image} {type(form.front_image)}")
    logger.info(f"file data: {form.front_image.data} {type(form.front_image.data)}")
    if form.front_image.data:
        logger.info(f"file data: {form.front_image.data.filename}")
    if form.validate_on_submit():
        logger.info(f"tuckbox files: {request.files}")
        buf = form.generate(files=request.files)
        r = send_file(
            buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="sumpfork_tuckbox.pdf",
        )
        logger.info(f"response: {r}")
        return r
    r = render_template(
        "index.html",
        pages=PAGES,
        form=form,
        active="tuckboxes",
        static_url=os.environ["STATIC_WEB_URL"],
        form_target=url_for("tuckboxes"),
    )
    return r


@flask_app.route("/chitboxes/", methods=["GET", "POST"])
def chitboxes():
    form = ChitboxForm()
    logger.info(f"in chitboxes, form validates: {form.validate_on_submit()}")
    logger.info(f"errors: {form.errors}")
    if form.validate_on_submit():
        logger.info(f"chitbox files: {request.files}")
        buf = form.generate(files=request.files)
        r = send_file(
            buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="sumpfork_chitbox.pdf",
        )
        logger.info(f"response: {r}")
        return r
    r = render_template(
        "index.html",
        pages=PAGES,
        form=form,
        active="chitboxes",
        static_url=os.environ["STATIC_WEB_URL"],
        form_target=url_for("chitboxes"),
    )
    return r


@flask_app.route("/preview/<string:tag>/", methods=["POST"])
def preview(tag):
    logger.info(f"preview call for {tag}, request is {request}, form is {request.form}")
    if tag == "dominion_dividers":
        form = DomDivForm(request.form, font_dir=os.environ.get("FONT_DIR"))
    elif tag == "chitboxes":
        form = ChitboxForm(request.form)
    elif tag == "tuckboxes":
        form = TuckboxForm(request.form)
    else:
        abort(404)
    logger.info(f"submitted: {form.is_submitted()}")
    logger.info(f"validates: {form.validate()}")
    logger.info(f"errors: {form.errors}")
    if form.validate():
        buf = form.generate(num_pages=1, files=request.files)
        buf = base64.b64encode(buf.getvalue()).decode("ascii")
        r = jsonify({"preview_pdf": buf})
        logger.info(f"reponse: {r}")
        return r
    return jsonify({"error": "Invalid Form Entries"})


if __name__ == "__main__":
    flask_app.run(debug=True)
