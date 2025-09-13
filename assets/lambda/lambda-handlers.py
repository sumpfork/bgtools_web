import base64
import binascii
import functools
import io
import json
import os
import random
import string
import sys

import apig_wsgi
import boto3
import domdiv
import domdiv.db
from chitbox_form import ChitboxForm
from domdiv_form import DomDivForm
from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_bootstrap import Bootstrap4
from flask_uploads import IMAGES
from loguru import logger
from tuckbox_form import TuckboxForm

PAGES = {
    "dominion_dividers": "Dominion Dividers",
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


@functools.lru_cache(maxsize=1)
def get_client(c):
    return boto3.client(c)


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


def upload_pdf_to_s3(buf, file_type):
    """Upload PDF to S3 and return CloudFront URL"""
    s3 = get_client("s3")
    tag = "".join(random.choice(string.ascii_letters) for i in range(6))
    fname = f"{file_type}_{tag}.pdf"
    key = f"{os.environ['OUTPUT_PREFIX'].strip('/')}/{fname}"

    s3.upload_fileobj(
        buf,
        os.environ["OUTPUT_BUCKET"],
        key,
        ExtraArgs={
            "ContentType": "application/pdf",
            "ContentDisposition": f'attachment; filename="{fname}"',
        },
    )

    # Generate the CloudFront URL for download
    static_url = os.environ["STATIC_WEB_URL"].rstrip("/")
    output_prefix = os.environ["OUTPUT_PREFIX"].strip("/")
    download_url = f"{static_url}/{output_prefix}/{fname}"
    return download_url


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
        # Create a copy of the buffer data for S3 upload
        buf_data = buf.getvalue()
        buf_copy = io.BytesIO(buf_data)
        download_url = upload_pdf_to_s3(buf_copy, "dominion_dividers")

        logger.info(f"redirecting to: {download_url}")
        return redirect(download_url)

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
        # Create a copy of the buffer data for S3 upload
        buf_data = buf.getvalue()
        buf_copy = io.BytesIO(buf_data)
        download_url = upload_pdf_to_s3(buf_copy, "tuckbox")

        logger.info(f"redirecting to: {download_url}")
        return redirect(download_url)
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
        # Create a copy of the buffer data for S3 upload
        buf_data = buf.getvalue()
        buf_copy = io.BytesIO(buf_data)
        download_url = upload_pdf_to_s3(buf_copy, "chitbox")

        logger.info(f"redirecting to: {download_url}")
        return redirect(download_url)
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
