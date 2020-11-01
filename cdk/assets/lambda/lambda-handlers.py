from io import BytesIO
import json
import logging
import os

import apig_wsgi
from flask import Flask, request, send_file, make_response
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
PAPER_SIZES = ["Letter", "Legal", "A4", "A3"]
TAB_SIDE_SELECTION = {"left": "Left to Right (all tab counts)",
                      "right": "Right to Left (all tab counts)",
                      "left-alternate": "Left then Right (2 tabs)",
                      "right-alternate": "Right then Left (2 tabs))",
                      "left-flip":"Left then flip (2 tabs)",
                      "right-flip":"Right then flip (2 tabs)",
                      "centre":"Centre (1 tab)",
                      "full":"Full width (1 tab)"}
TAB_NUMBER_SELECTION = {1: "1: all in the same location", 2: "2: alternating sides", 3: "3", 4: "4", 5: "5"}

flask_app = Flask(__name__)
apig_wsgi_handler = apig_wsgi.make_lambda_handler(flask_app, binary_support=True)
secret_key = os.environ["FLASK_SECRET_KEY"]
assert secret_key, "Need secret key specified in env"
flask_app.config["SECRET_KEY"] = secret_key

logger = logging.getLogger("bgtools_logger")
logger.setLevel(int(os.environ.get("LOG_LEVEL", logging.INFO)))

# def apig_wsgi_handler(event, context):
#     print(json.dumps(event, indent=2, sort_keys=True))
#     response = apig_wsgi_handler_helper(event, context)
#     print(json.dumps(response, indent=2, sort_keys=True))
#     return response


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
        label="Expansions to Include (Cmd/Ctrl click to select multiple)",
        choices=list(zip(choices, choiceNames)),
        default=["2ndedition"],
    )
    # Now Fan expansions
    choices = domdiv.main.FAN_CHOICES
    # make pretty names for the expansion choices
    choiceNames = []
    for choice in choices:
        for s, r in replacements.items():
            if choice.lower().endswith(s):
                choiceNames.append('{} {}'.format(
                    choice[:-len(s)].capitalize(), r))
                break
        else:
            choiceNames.append(choice.capitalize())
    fan_expansions = wtf_fields.SelectMultipleField(
        choices=list(zip(choices, choiceNames)),
        label='Fan Expansions to Include (Cmd/Ctrl click to select multiple)',
    )
    orientation = wtf_fields.SelectField(
        label="Divider Orientation",
        choices=["Horizontal", "Vertical"],
        default="Horizontal",
    )

    pagesize = wtf_fields.SelectField(
        label="Paper Size",
        choices=list(
            zip(
                PAPER_SIZES + domdiv.main.LABEL_KEYS,
                PAPER_SIZES + domdiv.main.LABEL_SELECTIONS,
            )
        ),
        default="Letter",
    )

    choices = ["Sleeved - Thin", "Sleeved - Thick", "Unsleeved"]
    cardsize = wtf_fields.SelectField(
        choices=list(zip(choices, choices)), label="Card Size", default="Unsleeved"
    )
    tabwidth = wtf_fields.DecimalField(
        label='Width of Tab in centimeters',
        default=4.0,
    )
    back_offset = wtf_fields.DecimalField(
        label='Back page horizontal offset points to shift to the right',
        default=0,
        )
    back_offset_height = wtf_fields.DecimalField(
        label='Back page vertical offset points to shift upward',
        default=0,
        )

    horizontal_gap = wtf_fields.DecimalField(
        label='Horizontal gap between dividers in centimeters',
        default=0,
        )
    vertical_gap = wtf_fields.DecimalField(
        label='Vertical gap between dividers in centimeters',
        default=0,
        )

    black_tabs = wtf_fields.BooleanField(
        label='Black tab background',
    )
    base_cards_with_expansion = wtf_fields.BooleanField(
        label="Include Base cards with the expansion", default=False)
    upgrade_with_expansion = wtf_fields.BooleanField(
        label="Include upgrade cards with the expansion being upgraded",
        default=False)
    edition = wtf_fields.SelectField(
        choices=list(
            zip(domdiv.main.EDITION_CHOICES, domdiv.main.EDITION_CHOICES)),
        label='Edition',
        default='latest')
    cropmarks = wtf_fields.BooleanField(
        label="Cropmarks Instead of Outlines", default=False)
    linetype = wtf_fields.SelectField(
        choices=list(
            zip(domdiv.main.LINE_CHOICES,
                domdiv.main.LINE_CHOICES)),
        label='Outline Type',
        default='line')
    wrappers = wtf_fields.BooleanField(
        label="Slipcases Instead of Dividers", default=False)
    notch = wtf_fields.BooleanField(
        label="If Slipcases, add a notch in corners", default=False)
    serpentine = wtf_fields.BooleanField(
        label="For 3 or more tabs, tab location reverses when the end is reached instead of resetting to the start",
        default=False)
    reset_tabs = wtf_fields.BooleanField(
        label="Restart tab starting location with every expansion.",
        default=True)
    counts = wtf_fields.BooleanField(
        label="Show number of Cards per Divider", default=False)
    types = wtf_fields.BooleanField(
        label="Show Card Type on each Divider", default=False)
    tab_name_align = wtf_fields.SelectField(
        choices=list(
            zip(domdiv.main.NAME_ALIGN_CHOICES,
                domdiv.main.NAME_ALIGN_CHOICES)))
    tab_number = wtf_fields.SelectField(
        choices=list(TAB_NUMBER_SELECTION.items()),
        label='Number of tabs',
        default=1)

    for x in domdiv.main.TAB_SIDE_CHOICES:
        if x not in TAB_SIDE_SELECTION:
            TAB_SIDE_SELECTION[x] = x.title()
    tab_side = wtf_fields.SelectField(
        choices=list(TAB_SIDE_SELECTION.items()),
        label='Starting tab location',
        default='left')
    
    samesidelabels = wtf_fields.BooleanField(
        label="Same Side Labels", default=False)
    order = wtf_fields.SelectField(
        label="Divider Order",
        choices=list(
            zip(domdiv.main.ORDER_CHOICES, domdiv.main.ORDER_CHOICES)))
    group_special = wtf_fields.BooleanField(
        label="Group Special Cards (e.g. Prizes)", default=True)
    expansion_dividers = wtf_fields.BooleanField(
        label="Include Expansion Dividers", default=False)
    centre_expansion_dividers = wtf_fields.BooleanField(
        label="If Expansion Dividers, centre the tabs on expansion dividers",
        default=False)
    expansion_dividers_long_name = wtf_fields.BooleanField(
        label=("If Expansion Dividers, use edition "
               "on expansion dividers names"),
        default=False)
    set_icon = wtf_fields.SelectField(
        choices=list(
            zip(domdiv.main.LOCATION_CHOICES, domdiv.main.LOCATION_CHOICES)),
        label="Set Icon Location",
        default="tab")
    cost_icon = wtf_fields.SelectField(
        choices=list(
            zip(domdiv.main.LOCATION_CHOICES, domdiv.main.LOCATION_CHOICES)),
        label="Cost Icon Location",
        default="tab")
    language = wtf_fields.SelectField(
        choices=list(
            zip(domdiv.main.LANGUAGE_CHOICES, domdiv.main.LANGUAGE_CHOICES)),
        label='Language',
        default='en_us')
    events = wtf_fields.BooleanField(
        label="Exclude Individual Events & Landmarks", default=False)
    divider_front_text = wtf_fields.SelectField(
        label='Front Text',
        choices=list(zip(domdiv.main.TEXT_CHOICES, domdiv.main.TEXT_CHOICES)),
        default='card')
    divider_back_text = wtf_fields.SelectField(
        label='Back Text',
        choices=list(
            zip(domdiv.main.TEXT_CHOICES + ['none'],
                domdiv.main.TEXT_CHOICES + ['no back page'])),
        default='rules')
    no_footer = wtf_fields.BooleanField(
        label='Omit the expansion name at the bottom of the page', default=False)
    tag = wtf_fields.HiddenField(default='domdiv')


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
        form.populate_obj(options)
        options.expansions = [[e] for e in form["expansions"].data]
        options.fan_expansions = [[e] for e in form["fan_expansions"].data]
        options.tab_number = int(options.tab_number)
        options.tabwidth = float(options.tabwidth)
        options.vertical_gap = float(options.vertical_gap)
        options.horizontal_gap = float(options.horizontal_gap)
        options.back_offset = float(options.back_offset)
        options.back_offset_height = float(options.back_offset_height)
        
        logger.info(f"options after populate: {options}")
        options = domdiv.main.clean_opts(options)
        logger.info(f"options after cleaning: {options}")
        buf = BytesIO()
        options.outfile = buf
        domdiv.main.generate(options)
        logger.info("done generation, returning pdf")
        buf.seek(0)
        r = send_file(
            buf,
            mimetype="application/pdf",
            as_attachment=True,
            attachment_filename="sumpfork_dominion_dividers.pdf",
        )
        logger.info(f"response: {r}")
        return r
        # r = make_response(buf.getvalue())
        # r.headers["Content-Type"] = "application/pdf"
        # r.headers[
        #     "Content-Disposition"
        # ] = 'attachment; filename="sumpfork_dominion_dividers.pdf"'
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


if __name__ == "__main__":
    flask_app.run(debug=True)
