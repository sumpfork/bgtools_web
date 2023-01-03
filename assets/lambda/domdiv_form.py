import argparse
from io import BytesIO
import logging
import os

import wtforms.fields as wtf_fields
from flask_wtf import FlaskForm
import domdiv.main

PAPER_SIZES = ["Letter", "Legal", "A4", "A3"]
TAB_SIDE_SELECTION = {
    "left": "Left to Right (all tab counts)",
    "right": "Right to Left (all tab counts)",
    "left-alternate": "Left then Right (2 tabs)",
    "right-alternate": "Right then Left (2 tabs))",
    "left-flip": "Left then flip (2 tabs)",
    "right-flip": "Right then flip (2 tabs)",
    "centre": "Centre (1 tab)",
    "full": "Full width (1 tab)",
}
TAB_NUMBER_SELECTION = {
    1: "1: all in the same location",
    2: "2: alternating sides",
    3: "3",
    4: "4",
    5: "5",
}

logger = logging.getLogger("domdivform")
logger.setLevel(int(os.environ.get("LOG_LEVEL", logging.INFO)))


class DomDivForm(FlaskForm):
    # Expansions
    expansion_choices, fan_choices = domdiv.main.get_expansions()

    expansion_choices = [
        choice for choice in expansion_choices if choice.lower() != "extras"
    ]
    # make pretty names for the expansion choices
    choiceNames = []
    replacements = {
        "1stedition": "1st Edition",
        "1steditionremoved": "cards removed in 2nd edition",
        "2ndeditionupgrade": "2nd Edition Upgrade",
        "2ndedition": "2nd Edition",
    }
    for choice in expansion_choices:
        for s, r in replacements.items():
            if choice.lower().endswith(s):
                choiceNames.append("{} {}".format(choice[: -len(s)].capitalize(), r))
                break
        else:
            choiceNames.append(choice.capitalize())
    expansions = wtf_fields.SelectMultipleField(
        label="Expansions to Include (Cmd/Ctrl click to select multiple)",
        choices=list(zip(expansion_choices, choiceNames)),
        default=["dominion2ndEdition"],
    )
    # Now Fan expansions
    # make pretty names for the expansion choices
    choiceNames = []
    for choice in fan_choices:
        for s, r in replacements.items():
            if choice.lower().endswith(s):
                choiceNames.append("{} {}".format(choice[: -len(s)].capitalize(), r))
                break
        else:
            choiceNames.append(choice.capitalize())
    fan = wtf_fields.SelectMultipleField(
        choices=list(zip(fan_choices, choiceNames)),
        label="Fan Expansions to Include (Cmd/Ctrl click to select multiple)",
    )
    orientation = wtf_fields.SelectField(
        label="Divider Orientation",
        choices=[("horizontal", "Horizontal"), ("vertical", "Vertical")],
        default="horizontal",
    )

    _, label_keys, label_selections, _ = domdiv.main.get_label_data()
    pagesize = wtf_fields.SelectField(
        label="Paper Size",
        choices=list(
            zip(
                PAPER_SIZES + label_keys,
                PAPER_SIZES + label_selections,
            )
        ),
        default="Letter",
    )

    cardsize_choices = ["Sleeved - Thin", "Sleeved - Thick", "Unsleeved"]
    cardsize = wtf_fields.SelectField(
        choices=list(zip(cardsize_choices, cardsize_choices)),
        label="Card Size",
        default="Unsleeved",
    )
    tabwidth = wtf_fields.FloatField(
        label="Width of Tab in centimeters",
        default=4.0,
    )
    back_offset = wtf_fields.FloatField(
        label="Back page horizontal offset points to shift to the right",
        default=0,
    )
    back_offset_height = wtf_fields.FloatField(
        label="Back page vertical offset points to shift upward",
        default=0,
    )

    horizontal_gap = wtf_fields.FloatField(
        label="Horizontal gap between dividers in centimeters",
        default=0,
    )
    vertical_gap = wtf_fields.FloatField(
        label="Vertical gap between dividers in centimeters",
        default=0,
    )

    black_tabs = wtf_fields.BooleanField(
        label="Black tab background",
    )
    tabwidth = wtf_fields.FloatField(label="Width of Tab in centimeters", default=4.0)
    base_cards_with_expansion = wtf_fields.BooleanField(
        label="Include Base cards with the expansion", default=False
    )
    upgrade_with_expansion = wtf_fields.BooleanField(
        label="Include upgrade cards with the expansion being upgraded", default=False
    )
    edition = wtf_fields.SelectField(
        choices=list(zip(domdiv.main.EDITION_CHOICES, domdiv.main.EDITION_CHOICES)),
        label="Edition",
        default="all",
    )
    cropmarks = wtf_fields.BooleanField(
        label="Cropmarks Instead of Outlines", default=False
    )
    linetype = wtf_fields.SelectField(
        choices=list(zip(domdiv.main.LINE_CHOICES, domdiv.main.LINE_CHOICES)),
        label="Outline Type",
        default="line",
    )

    wrapper_choices = ["Dividers", "Slipcases", "PullTabs", "Tents"]
    wrappers = wtf_fields.RadioField(
        label="Folded Slipcases?",
        choices=list(zip(wrapper_choices, wrapper_choices)),
        default="Dividers",
    )
    notch = wtf_fields.BooleanField(
        label="Add a notch in corners", default=False
    )
    tab_serpentine = wtf_fields.BooleanField(
        label="For 3 or more tabs, tab location reverses when the end is reached instead of resetting to the start",
        default=False,
    )
    expansion_reset_tabs = wtf_fields.BooleanField(
        label="Restart tab starting location with every expansion.", default=True
    )
    count = wtf_fields.BooleanField(
        label="Show number of Cards per Divider", default=False
    )
    types = wtf_fields.BooleanField(
        label="Show Card Type on each Divider", default=False
    )
    tab_name_align = wtf_fields.SelectField(
        choices=list(
            zip(domdiv.main.NAME_ALIGN_CHOICES, domdiv.main.NAME_ALIGN_CHOICES)
        ),
        default=domdiv.main.NAME_ALIGN_CHOICES[0],
    )
    tab_number = wtf_fields.SelectField(
        choices=list(TAB_NUMBER_SELECTION.items()), label="Number of tabs", default=1
    )

    for x in domdiv.main.TAB_SIDE_CHOICES:
        if x not in TAB_SIDE_SELECTION:
            TAB_SIDE_SELECTION[x] = x.title()
    tab_side = wtf_fields.SelectField(
        choices=list(TAB_SIDE_SELECTION.items()),
        label="Starting tab location",
        default="left",
    )

    order = wtf_fields.SelectField(
        label="Divider Order",
        choices=list(zip(domdiv.main.ORDER_CHOICES, domdiv.main.ORDER_CHOICES)),
        default=domdiv.main.ORDER_CHOICES[0],
    )
    group_special = wtf_fields.BooleanField(
        label="Group Special Cards (e.g. Prizes with Tournament)", default=True
    )
    group_kingdom = wtf_fields.BooleanField(
        label="Group cards without randomizers separately", default=False
    )
    # global grouping
    group_global_choices, _ = domdiv.main.get_global_groups()
    # make pretty names for the global group choices
    choiceNames = []
    for choice in group_global_choices:
        choiceNames.append(choice.capitalize())
    group_global = wtf_fields.SelectMultipleField(
        choices=list(zip(group_global_choices, choiceNames)),
        label="Group these card types globally (Cmd/Ctrl click to select multiple)",
        default="",
    )
    start_decks = wtf_fields.BooleanField(
        label="Group four start decks with the Base cards"
    )
    curse10 = wtf_fields.BooleanField(
        label="Group Curse cards into groups of ten cards"
    )
    no_trash = wtf_fields.BooleanField(label="Exclude Trash from cards")
    expansion_dividers = wtf_fields.BooleanField(
        label="Include Expansion Dividers", default=False
    )
    centre_expansion_dividers = wtf_fields.BooleanField(
        label="If Expansion Dividers, centre the tabs on expansion dividers",
        default=False,
    )
    expansion_dividers_long_name = wtf_fields.BooleanField(
        label=("If Expansion Dividers, use edition " "on expansion dividers names"),
        default=False,
    )
    set_icon = wtf_fields.SelectField(
        choices=list(zip(domdiv.main.LOCATION_CHOICES, domdiv.main.LOCATION_CHOICES)),
        label="Set Icon Location",
        default="tab",
    )
    cost = wtf_fields.SelectField(
        choices=list(zip(domdiv.main.LOCATION_CHOICES, domdiv.main.LOCATION_CHOICES)),
        label="Cost Icon Location",
        default="tab",
    )
    language_choices = domdiv.main.get_languages()
    language = wtf_fields.SelectField(
        choices=list(zip(language_choices, language_choices)),
        label="Language",
        default="en_us",
    )
    exclude_events = wtf_fields.BooleanField(
        label="Exclude Individual Events & Landmarks", default=False
    )
    text_front = wtf_fields.SelectField(
        label="Front Text",
        choices=list(zip(domdiv.main.TEXT_CHOICES, domdiv.main.TEXT_CHOICES)),
        default="card",
    )
    text_back = wtf_fields.SelectField(
        label="Back Text",
        choices=list(
            zip(
                domdiv.main.TEXT_CHOICES + ["none"],
                domdiv.main.TEXT_CHOICES + ["no back page"],
            )
        ),
        default="rules",
    )
    no_page_footer = wtf_fields.BooleanField(
        label="Omit the expansion name at the bottom of the page", default=False
    )

    def clean_options(self):
        form_options = argparse.Namespace()
        self.populate_obj(form_options)
        options = domdiv.main.parse_opts([])
        logger.info(f"valid options: {sorted(list(vars(options).keys()))}")
        is_label = False
        for option, value in vars(form_options).items():
            # option = option.replace('_', '-')
            logger.info(f"option {option} ({type(option)}): {value}")
            if option == "tab_number":
                value = int(value)

            if option in ["expansions", "fan", "group_global"]:
                if option == "expansions" and not value:
                    value = self.expansion_choices
                value = [[v] for v in value]

            if option == "cardsize":
                logger.info("handling cardsize")
                options.size = "unsleeved" if "Unsleeved" in value else "sleeved"
                options.sleeved_thick = "Thick" in option
                options.sleeved_thin = "Thin" in option
            elif option == "pagesize":
                logger.info("handling pagesize")
                if value in PAPER_SIZES:
                    options.papersize = value
                    options.label_name = None
                else:
                    options.label_name = value
                    options.papersize = "letter"
                    options.wrapper_meta = False
                    options.notch = False
                    options.cropmarks = False
                    is_label = True
            elif option == "wrappers":
                value = value.lower()

                if value == "slipcases":
                    options.wrapper_meta = True
                elif value == "pulltabs":
                    options.pull_tab_meta = True
                elif value == "tents":
                    options.tent_meta = True
                else:
                    assert value == "dividers"
            else:
                assert hasattr(options, option), f"{option} is not a script option"
                if is_label and option in ["wrapper", "notch", "cropmarks"]:
                    logger.info(f"skipping {option} because we're printing labels")
                    continue
                logger.info(f"{option} --> {value}")
                options.__setattr__(option, value)

        if not options.group_global:
            options.group_global = None
        if options.group_global or options.include_blanks:
            options.expansions += [["extras"]]

        logger.info(f"options after populate: {options}")
        options = domdiv.main.clean_opts(options)
        logger.info(f"options after cleaning: {options}")
        return options

    def generate(self, num_pages=None, **kwargs):
        options = self.clean_options()
        if num_pages is not None:
            options.num_pages = num_pages

        buf = BytesIO()
        options.outfile = buf
        domdiv.main.generate(options)
        logger.info("done generation, returning pdf")
        buf.seek(0)
        return buf
