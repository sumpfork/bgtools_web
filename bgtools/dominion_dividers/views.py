from django.http import HttpResponse
from django.shortcuts import render
from django import forms
import domdiv.main
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Div, HTML
from crispy_forms.bootstrap import FormActions, Accordion, AccordionGroup
# from chitboxes.chitboxes import ChitBoxGenerator


class TabGenerationOptionsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(TabGenerationOptionsForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div(
                    HTML('<h3>Generation Options</h3>'),
                    css_class='col-md-9'
                ),
                Div(
                    FormActions(
                        Submit('submit', 'Generate',
                               style="margin-top: 20px;")
                    ),
                    css_class='col-md-3'
                ),
                css_class='row'
            ),
            Div(
                Div(
                    Accordion(
                        AccordionGroup('Expansion Selection',
                                       'expansions',
                                       'edition'),
                        AccordionGroup('Global Style',
                                       'cropmarks',
                                       'wrappers',
                                       'tabsonly',
                                       'no_footer'),
                        AccordionGroup('Sizes and Orientation',
                                       'orientation',
                                       'pagesize',
                                       'cardsize'),
                        AccordionGroup('Divider Layout',
                                       'tab_side',
                                       'tab_name_align',
                                       'set_icon',
                                       'cost_icon',
                                       'counts'),
                        AccordionGroup('Text Options',
                                       'divider_front_text',
                                       'divider_back_text',
                                       'language'),
                        AccordionGroup('Order and Extras',
                                       'order',
                                       'group_special',
                                       'expansion_dividers'),

                    ),
                    css_class='col-md-12',
                ),
                css_class='row',
            )
        )
        self.helper.form_id = 'id-tabgenoptions'
        self.helper.form_class = 'blueForms'
        self.helper.form_method = 'post'
        self.helper.form_action = '/'
        # self.helper.add_input(Submit('submit', 'Generate'))

    choices = ['Horizontal', 'Vertical']
    orientation = forms.ChoiceField(choices=zip(choices, choices),
                                    label='Divider Orientation',
                                    initial='Horizontal',
                                    required=True)
    choices = ['Letter', 'A4', 'A3']
    pagesize = forms.ChoiceField(choices=zip(choices, choices), label='Page Size', initial='Letter', required=True)
    choices = ['Sleeved', 'Unsleeved']
    cardsize = forms.ChoiceField(choices=zip(choices, choices), label='Card Size', initial='Unsleeved', required=True)
    choices = set(domdiv.main.EXPANSION_CHOICES)
    # for the form, simplify the choices a little
    common = set()
    remove = set()
    for choice in choices:
        try:
            index = choice.lower().index('edition')
        except ValueError:
            continue
        if index == len(choice) - 7:
            remove.add(choice)
            common.add(choice.lower()[:index - 3])
    choices -= remove
    choices |= common
    choices = sorted(choices)

    expansions = forms.MultipleChoiceField(
        choices=zip(choices, choices),
        label='Expansions to Include',
        initial=choices, required=True
    )
    edition = forms.ChoiceField(choices=zip(domdiv.main.EDITION_CHOICES, domdiv.main.EDITION_CHOICES),
                                label='Edition',
                                initial='latest')
    cropmarks = forms.BooleanField(label="Cropmarks Instead of Outlines", initial=False, required=False)
    wrappers = forms.BooleanField(label="Slipcases Instead of Dividers", initial=False, required=False)
    counts = forms.BooleanField(label="Show # of Cards per Divider", initial=False, required=False)
    tab_name_align = forms.ChoiceField(choices=zip(domdiv.main.NAME_ALIGN_CHOICES, domdiv.main.NAME_ALIGN_CHOICES))
    tab_side = forms.ChoiceField(choices=zip(domdiv.main.TAB_SIDE_CHOICES, domdiv.main.TAB_SIDE_CHOICES))
    samesidelabels = forms.BooleanField(label="Same Side Labels", initial=False, required=False)
    order = forms.ChoiceField(label="Divider Order",
                              choices=zip(domdiv.main.ORDER_CHOICES, domdiv.main.ORDER_CHOICES),
                              required=False)
    group_special = forms.BooleanField(label="Group Special Cards (e.g. Prizes)", initial=True, required=False)
    expansion_dividers = forms.BooleanField(label="Extra Expansion Dividers", initial=False, required=False)
    tabsonly = forms.BooleanField(label="Avery 5167/8867 Tab Label Sheets", initial=False, required=False)
    set_icon = forms.ChoiceField(
        choices=zip(domdiv.main.LOCATION_CHOICES, domdiv.main.LOCATION_CHOICES),
        label="Set Icon Location",
        initial="tab",
        required=False
    )
    cost_icon = forms.ChoiceField(
        choices=zip(domdiv.main.LOCATION_CHOICES, domdiv.main.LOCATION_CHOICES),
        label="Cost Icon Location",
        initial="tab",
        required=False
    )
    language = forms.ChoiceField(
        choices=zip(domdiv.main.LANGUAGE_CHOICES, domdiv.main.LANGUAGE_CHOICES),
        label='Language',
        initial='en_us',
        required=False
    )
    events = forms.BooleanField(label="Exclude Individual Events & Landmarks", initial=False, required=False)
    divider_front_text = forms.ChoiceField(label='Front Text',
                                           choices=zip(domdiv.main.TEXT_CHOICES, domdiv.main.TEXT_CHOICES),
                                           initial='card',
                                           required=False)
    divider_back_text = forms.ChoiceField(
        label='Back Text',
        choices=zip(domdiv.main.TEXT_CHOICES + ['none'], domdiv.main.TEXT_CHOICES + ['no back page']),
        initial='rules',
        required=False
    )
    no_footer = forms.BooleanField(label='Omit set label footer text', initial=False, required=False)


class ChitBoxForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(ChitBoxForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = '/chitbox'

        self.helper.add_input(Submit('submit', 'Generate'))

    width = forms.FloatField(required=True, label='Width in cm', min_value=1.0, max_value=20.0, initial=5)
    length = forms.FloatField(required=True, label='Length in cm', min_value=1.0, max_value=20.0, initial=5)
    height = forms.FloatField(required=True, label='Height in cm', min_value=1.0, max_value=20.0, initial=2)
    main_image = forms.ImageField(required=True, label='Upload Main Image')
    side_image = forms.ImageField(required=True, label='Upload Side Image')


def index(request):
    if request.method == 'POST':
        form = TabGenerationOptionsForm(request.POST)
        if form.is_valid():
            # generate default options
            options = domdiv.main.parse_opts([])
            data = form.cleaned_data
            options.orientation = data['orientation'].lower()
            options.size = data['cardsize'].lower()
            options.expansions = data['expansions']
            options.edition = data['edition']
            options.papersize = data['pagesize']
            options.cropmarks = data['cropmarks']
            options.wrapper = data['wrappers']
            options.count = data['counts']
            options.tab_name_align = data['tab_name_align']
            options.tab_side = data['tab_side']
            options.expansion_dividers = data['expansion_dividers']
            options.cost = data['cost_icon']
            options.set_icon = data['set_icon']
            options.order = data['order']
            options.special_card_groups = data['group_special']
            options.tabs_only = data['tabsonly']
            options.language = data['language']
            options.exclude_events = data['events']
            options.exclude_landmarks = data['events']
            options.text_front = data['divider_front_text']
            options.text_back = data['divider_back_text']
            options.no_page_footer = data['no_footer']
            print options

            # Create the HttpResponse object with the appropriate PDF headers.
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="sumpfork_dominion_tabs.pdf"'
            options.outfile = response

            domdiv.main.generate(options)
            return response
    else:
        form = TabGenerationOptionsForm()

    return render(request, 'dominion_dividers/index.html', {'form': form})


# def chitbox(request):
#     if request.method == 'POST':
#         form = ChitBoxForm(request.POST, request.FILES)
#         if form.is_valid():
#             data = form.cleaned_data
#             # Create the HttpResponse object with the appropriate PDF headers.
#             response = HttpResponse(mimetype='application/pdf')
#             response['Content-Disposition'] = 'attachment; filename="sumpfork_chitbox.pdf"'
#             c = ChitBoxGenerator.fromRawData(
#                 data['width'], data['length'], data['height'], response, data['main_image'], data['side_image']
#             )
#             c.generate()

#             return response
#     else:
#         form = ChitBoxForm()
#     return render(request, 'domtabs/chitboxes.html', {'form': form})
