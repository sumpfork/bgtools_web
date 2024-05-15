from flask_wtf import FlaskForm
import wtforms.fields as wtf_fields
from loguru import logger


class DynamicForm(FlaskForm):
    @classmethod
    def add_field(cls, name, field):
        assert not hasattr(cls, name), f"Field {name} already exists"
        setattr(cls, name, field)


class ArgParse2FormWrapperSubform(DynamicForm):

    args_to_exclude = []

    # subform needs to be a separate class that does not inherit from ArgParse2FormWrapper
    # as otherwise we get infinite recursion during initialization
    @classmethod
    def add_argument(cls, *flags, **kwargs):
        # we don't care about the flags unless no destination is specified
        dest = kwargs.get("dest")

        logger.info(f"adding arg {flags} to {cls}")

        if not dest:
            longforms = [f for f in flags if f.startswith("--")]
            shortforms = [f for f in flags if f.startswith("--")]
            if longforms:
                dest = longforms[0][2:]
            elif shortforms:
                dest = shortforms[0][1:]
            else:
                dest = flags[0]
            dest = dest.replace("-", "_")

        if hasattr(cls, dest):
            return getattr(cls, dest)

        if dest in cls.args_to_exclude:
            logger.info(f"Excluding arg {dest} due to exclusion list")
            return

        choices = kwargs.get("choices")
        nargs = kwargs.get("nargs")
        default = kwargs.get("default")
        action = kwargs.get("action")
        type_ = kwargs.get("type")
        # help = kwargs.get("help")
        if not type_ and default:
            type_ = type(default)

        if choices:
            if nargs not in ["?", "1"]:
                cls.add_field(
                    dest,
                    wtf_fields.SelectMultipleField(
                        dest, choices=choices, default=default
                    ),
                )
            else:
                cls.add_field(
                    dest, wtf_fields.SelectField(dest, choices=choices, default=default)
                )
        elif type_:
            if type_ == int:
                cls.add_field(dest, wtf_fields.IntegerField(dest, default=default))
            elif type_ == float:
                cls.add_field(dest, wtf_fields.FloatField(dest, default=default))
        elif action == "store_true":
            cls.add_field(dest, wtf_fields.BooleanField(dest, default=default))
        else:
            logger.warning(f"ignoring field {dest}: {flags} {kwargs}")


class ArgParse2FormWrapper(DynamicForm):

    instantiated_form = None
    args_to_exclude = []

    # hack to support domdiv
    info = False
    info_all = False

    @classmethod
    def exclude_args(cls, *args):
        cls.args_to_exclude.extend(args)

    @classmethod
    def add_argument_group(cls, name, _description):
        if hasattr(cls, name):
            return getattr(cls, name).field_class

        if name in cls.args_to_exclude:
            logger.info(f"Excluding group {name} due to exclusion list")

            class Dummy:
                @classmethod
                def add_argument(cls, *_, **_2):
                    return

            return Dummy

        tag = "".join(name.split()).replace("/", "")
        c = type(tag, (ArgParse2FormWrapperSubform,), {})
        logger.info(f"Adding group {name} to class {cls.__name__} {cls}")
        cls.add_field(name, wtf_fields.FormField(c, id=tag.lower()))

        return c

    @classmethod
    def parse_args(cls, *args, **kwargs):
        logger.info(f"parse_args called on {cls}")
        if cls.instantiated_form is None:
            logger.info("instantiating new arg parse wrapper")
            cls.instantiated_form = ArgParse2FormWrapper()
        return cls.instantiated_form
