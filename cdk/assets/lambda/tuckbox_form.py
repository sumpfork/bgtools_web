from io import BytesIO
import logging
import os
import re

import wtforms.fields as wtf_fields
from wtforms import validators
from flask_wtf import FlaskForm
from flask_wtf.file import FileField as FlaskFileField, FileAllowed
from flask_uploads import UploadSet, IMAGES, configure_uploads
from tuckboxes.tuckboxes import TuckBoxGenerator

logger = logging.getLogger("tuckboxes")
logger.setLevel(int(os.environ.get("LOG_LEVEL", logging.INFO)))

class TuckboxForm(FlaskForm):
    images = UploadSet("images", IMAGES)

    @classmethod
    def init(cls, app):
        configure_uploads(app, [cls.images])

    width = wtf_fields.DecimalField(
        label="Width in cm (1-20)",
        validators=[validators.NumberRange(1.0, 20.0)],
        default=6,
    )
    height = wtf_fields.DecimalField(
        label="Height in cm (1-20)",
        validators=[validators.NumberRange(1.0, 20.0)],
        default=9.3,
    )
    depth = wtf_fields.DecimalField(
        label="Depth in cm (1-20)",
        validators=[validators.NumberRange(1.0, 20.0)],
        default=3,
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
    tag = wtf_fields.HiddenField(default="tuckboxes")

    def generate(self, files):
        buf = BytesIO()
        logger.info(f"fill colour: {self['fill_colour'].data}, {type(self['fill_colour'].data)}")
        fc = re.match("#(\w{2})(\w{2})(\w{2})", self["fill_colour"].data).groups()
        fc = tuple(int(p, 16) / 255.0 for p in fc)
        c = TuckBoxGenerator.fromRawData(
            float(self["width"].data),
            float(self["height"].data),
            float(self["depth"].data),
            buf,
            fIm=files.get("front_image"),
            sIm=files.get("side_image"),
            bIm=files.get("back_image"),
            eIm=files.get("end_images"),
            fillColour=fc,
            preserveSideAspect=self["preserve_side_aspect"].data,
            preserveEndAspect=self["preserve_end_aspect"].data,
        )
        c.generate()
        c.close()
        buf.seek(0)
        return buf
