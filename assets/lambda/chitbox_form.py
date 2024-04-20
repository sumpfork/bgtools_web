from io import BytesIO

import wtforms.fields as wtf_fields
from wtforms import validators
from flask_wtf import FlaskForm
from flask_wtf.file import FileField as FlaskFileField, FileAllowed
from flask_uploads import IMAGES
from chitboxes.chitboxes import ChitBoxGenerator


class ChitboxForm(FlaskForm):
    width = wtf_fields.DecimalField(
        label="Width in cm (1-20)",
        validators=[validators.NumberRange(1.0, 20.0)],
        default=5,
    )
    length = wtf_fields.DecimalField(
        label="Length in cm (1-20)",
        validators=[validators.NumberRange(1.0, 20.0)],
        default=5,
    )
    height = wtf_fields.DecimalField(
        label="Height in cm (1-20)",
        validators=[validators.NumberRange(1.0, 20.0)],
        default=2,
    )
    main_image = FlaskFileField(
        label="Upload Main Image", validators=[FileAllowed(IMAGES, "Images only!")]
    )
    side_image = FlaskFileField(
        label="Upload Side Image", validators=[FileAllowed(IMAGES, "Images only!")]
    )

    def generate(self, files=None, **kwargs):
        if files is None:
            files = {}

        buf = BytesIO()
        c = ChitBoxGenerator.fromRawData(
            float(self["width"].data),
            float(self["length"].data),
            float(self["height"].data),
            buf,
            files.get("main_image"),
            files.get("side_image"),
        )
        c.generate()
        buf.seek(0)
        return buf
