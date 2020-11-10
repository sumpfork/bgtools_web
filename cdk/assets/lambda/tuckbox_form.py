from io import BytesIO
import logging
import os

import wtforms.fields as wtf_fields
from wtforms import validators
from flask_wtf import FlaskForm
from flask_wtf.file import FileField as FlaskFileField, FileAllowed
from wtforms.validators import NumberRange
from flask_uploads import UploadSet, IMAGES
from tuckboxes.tuckboxes import TuckboxGenerator

logger = logging.getLogger("tuckboxes")
logger.setLevel(int(os.environ.get("LOG_LEVEL", logging.INFO)))

images = UploadSet("images", IMAGES)


class TuckboxForm(FlaskForm):
    width = wtf_fields.DecimalField(
        label="Width in cm (1-20)",
        validators=[validators.NumberRange(1.0, 20.0)],
        default=6,
    )
    height = wtf_fields.DecimalField(
        label="Height in cm (1-20)",
        validators=validators.NumberRange(1.0, 20.0),
        default=9.3,
    )
    depth = wtf_fields.DecimalField(
        label="Depth in cm (1-20)",
        validators=validators.NumberRange(1.0, 20.0),
        initial=3,
    )
    front_image = FlaskFileField(
        label="Upload Main Image", validators=[FileAllowed(images, "Images only!")]
    )
    side_image = FlaskFileField(
        label="Upload Side Image", validators=[FileAllowed(images, "Images only!")]
    )
    back_image = FlaskFileField(
        label="Upload Back Image", validators=[FileAllowed(images, "Images only!")]
    )
    end_image = FlaskFileField(
        label="Upload End Image", validators=[FileAllowed(images, "Images only!")]
    )
    preserve_side_aspect = wtf_fields.BooleanField(
        label="Preserve Side Image Aspect", default=True
    )
    preserve_end_aspect = wtf_fields.BooleanField(
        label="Preserve End Image Aspect", default=True
    )
    fill_colour = wtf_fields.StringField(default="#99FF99")
    #        widget=forms.TextInput(attrs={'type': 'color'}), initial='#99FF99')
    tag = wtf_fields.HiddenField(default="tuckboxes")

    def generate(self):
        buf = BytesIO()
        fc = re.match(r"#(\w{2})(\w{2})(\w{2})", self["fill_colour"]).groups()
        fc = tuple(int(p, 16) / 255.0 for p in fc)
        c = TuckboxGenerator.fromRawData(
            self["width"],
            self["height"],
            self["depth"],
            buf,
            fillColour=fc,
            preserveSideAspect=self["preserve_side_aspect"],
            preserveEndAspect=self["preserve_end_aspect"],
        )
        c.generate()
        c.close()
        buf.seek(0)
        return buf
