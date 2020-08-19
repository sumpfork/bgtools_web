import re
import base64

from django.http import HttpResponse, JsonResponse, HttpResponseServerError, HttpResponseBadRequest
from django.shortcuts import render
from django import forms
import domdiv.main
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Div, HTML
from crispy_forms.bootstrap import FormActions, Accordion, AccordionGroup, AppendedText
from chitboxes.chitboxes import ChitBoxGenerator
from tuckboxes.tuckboxes import TuckBoxGenerator

PAGES = [('domdiv', 'Dominion Dividers'), ('chitboxes', 'Bits Boxes'),
         ('tuckboxes', 'Card Tuckboxes')]

PAPER_SIZES = [u'Letter', u'Legal', u'A4', u'A3']
TAB_SIDE_SELECTION = {"left": "Left to Right (all tab counts)",
                      "right": "Right to Left (all tab counts)",
                      "left-alternate": "Left then Right (2 tabs)",
                      "right-alternate": "Right then Left (2 tabs))",
                      "left-flip":"Left then flip (2 tabs)",
                      "right-flip":"Right then flip (2 tabs)",
                      "centre":"Centre (1 tab)",
                      "full":"Full width (1 tab)"}
TAB_NUMBER_SELECTION = {1: "1: all in the same location", 2: "2: alternating sides", 3: "3", 4: "4", 5: "5"}

class TabGenerationOptionsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(TabGenerationOptionsForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Div(HTML('<h3>Generation Options</h3>'), css_class='col-md-9'),
                Div(FormActions(
                    Submit('submit', 'Generate', style="margin-top: 20px;")),
                    css_class='col-md-3'),
                css_class='row'),
            Div(
                Div(
                    Accordion(
                        AccordionGroup('Expansion Selection', 'expansions',
                                       'fan_expansions'),
                        AccordionGroup('Page Options', 
                                       'pagesize',
                                       HTML("Selecting Labels will override some settings to fit the size of the label"),
                                       'no_footer',
                                       AppendedText('back_offset', 'points', active=True),
                                       AppendedText('back_offset_height', 'points', active=True)),
                        AccordionGroup('Style Options',
                                       'orientation', 
                                       'wrappers', 'notch', 
                                       'linetype', 'cardsize',
                                       AppendedText('horizontal_gap', 'cm', active=True),
                                       AppendedText('vertical_gap', 'cm', active=True)
                                       ),
                        AccordionGroup('Tab Options',
                                       'tab_number', 'tab_side', 'serpentine', 'reset_tabs',
                                       'tab_name_align', 'set_icon', 'cost_icon', 'black_tabs',
                                       AppendedText('tabwidth', 'cm', active=True)
                                       ),
                        AccordionGroup('Body Options',
                                       'counts', 'types', 
                                       'divider_front_text', 'divider_back_text',
                                       'language'),
                        AccordionGroup('Order, Groups and Extras',
                                       'order',
                                       'group_special', 'group_kingdom', 'group_global',
                                       'start_decks', 'curse10', 'no_trash',
                                       'base_cards_with_expansion', 'upgrade_with_expansion',
                                       'expansion_dividers',
                                       'centre_expansion_dividers',
                                       'expansion_dividers_long_name'),
                    ),
                    css_class='col-md-12',
                ),
                'tag',
                css_class='row',
            ))
        self.helper.form_id = 'id-tabgenoptions'
        self.helper.form_class = 'blueForms'
        self.helper.form_method = 'post'
        self.helper.form_action = '/'
        for field in self.fields.values():
            field.required = False
    choices = ['Horizontal', 'Vertical']
    orientation = forms.ChoiceField(
        choices=list(zip(choices, choices)),
        label='Divider Orientation',
        initial='Horizontal')
    pagesize = forms.ChoiceField(
        choices=list(zip(PAPER_SIZES + domdiv.main.LABEL_KEYS, PAPER_SIZES + domdiv.main.LABEL_SELECTIONS)),
        label='Paper Type',
        initial='Letter')
    choices = ['Sleeved - Thin', 'Sleeved - Thick', 'Unsleeved']
    cardsize = forms.ChoiceField(
        choices=list(zip(choices, choices)),
        label='Card Size',
        initial='Unsleeved')
    tabwidth = forms.FloatField(
        label='Width of Tab in centimeters',
        initial='4.0',
        required=False,
        widget=forms.TextInput())
    back_offset = forms.FloatField(
        label='Back page horizontal offset points to shift to the right',
        initial='0',
        required=False,
        widget=forms.TextInput())
    back_offset_height = forms.FloatField(
        label='Back page vertical offset points to shift upward',
        initial='0',
        required=False,
        widget=forms.TextInput())

    horizontal_gap = forms.FloatField(
        label='Horizontal gap between dividers in centimeters',
        initial='0',
        required=False,
        widget=forms.TextInput())
    vertical_gap = forms.FloatField(
        label='Vertical gap between dividers in centimeters',
        initial='0',
        required=False,
        widget=forms.TextInput())

    black_tabs = forms.BooleanField(
        label='Black tab background',
        initial=False
    )
    # Expansions
    choices = domdiv.main.EXPANSION_CHOICES
    # make pretty names for the expansion choices
    choiceNames = []
    replacements = {
        '1stedition': '1st Edition',
        '2ndeditionupgrade': '2nd Edition Upgrade',
        '2ndedition': '2nd Edition'
    }
    for choice in choices:
        for s, r in replacements.items():
            if choice.lower().endswith(s):
                choiceNames.append('{} {}'.format(
                    choice[:-len(s)].capitalize(), r))
                break
        else:
            choiceNames.append(choice.capitalize())
    expansions = forms.MultipleChoiceField(
        choices=list(zip(choices, choiceNames)),
        label='Expansions to Include (Cmd/Ctrl click to select multiple)',
        initial=choices,
        widget=forms.SelectMultiple(attrs={'size': '18'}))
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
    fan_expansions = forms.MultipleChoiceField(
        choices=list(zip(choices, choiceNames)),
        label='Fan Expansions to Include (Cmd/Ctrl click to select multiple)',
        initial='',
        widget=forms.SelectMultiple(attrs={'size': '3'}))
    base_cards_with_expansion = forms.BooleanField(
        label="Include Base cards with the expansion", initial=False)
    upgrade_with_expansion = forms.BooleanField(
        label="Include upgrade cards with the expansion being upgraded",
        initial=False)
    edition = forms.ChoiceField(
        choices=list(
            zip(domdiv.main.EDITION_CHOICES, domdiv.main.EDITION_CHOICES)),
        label='Edition',
        initial='latest')
    cropmarks = forms.BooleanField(
        label="Cropmarks Instead of Outlines", initial=False)
    linetype = forms.ChoiceField(
        choices=list(
            zip(domdiv.main.LINE_CHOICES,
                domdiv.main.LINE_CHOICES)),
        label='Outline Type',
        initial='line') 
    wrappers = forms.BooleanField(
        label="Slipcases Instead of Dividers", initial=False)
    notch = forms.BooleanField(
        label="If Slipcases, add a notch in corners", initial=False)
    serpentine = forms.BooleanField(
        label="For 3 or more tabs, tab location reverses when the end is reached instead of resetting to the start",
        initial=False)
    reset_tabs = forms.BooleanField(
        label="Restart tab starting location with every expansion.", 
        initial=True)
    counts = forms.BooleanField(
        label="Show number of Cards per Divider", initial=False)
    types = forms.BooleanField(
        label="Show Card Type on each Divider", initial=False)
    tab_name_align = forms.ChoiceField(
        choices=list(
            zip(domdiv.main.NAME_ALIGN_CHOICES,
                domdiv.main.NAME_ALIGN_CHOICES)))
    tab_number = forms.ChoiceField(
        choices=list(zip(
                         [x for x in TAB_NUMBER_SELECTION],
                         [TAB_NUMBER_SELECTION[x] for x in TAB_NUMBER_SELECTION])),
        label='Number of tabs',
        initial=1)

    for x in domdiv.main.TAB_SIDE_CHOICES:
        if x not in TAB_SIDE_SELECTION:
            TAB_SIDE_SELECTION[x] = x.title()
    tab_side = forms.ChoiceField(
        choices=list(zip(
                         [x for x in TAB_SIDE_SELECTION],
                         [TAB_SIDE_SELECTION[x] for x in TAB_SIDE_SELECTION])),
        label='Starting tab location',
        initial='left')
    samesidelabels = forms.BooleanField(
        label="Same Side Labels", initial=False)
    order = forms.ChoiceField(
        label="Divider Order",
        choices=list(
            zip(domdiv.main.ORDER_CHOICES, domdiv.main.ORDER_CHOICES)))
    group_special = forms.BooleanField(
        label="Group Special Cards (e.g. Prizes with Tournament)", initial=True)
    group_kingdom = forms.BooleanField(
        label="Group cards without randomizers separately", initial=False)
    # global grouping 
    choices = domdiv.main.GROUP_GLOBAL_CHOICES
    # make pretty names for the global group choices
    choiceNames = []
    for choice in choices:
        choiceNames.append(choice.capitalize())
    group_global = forms.MultipleChoiceField(
        choices=list(zip(choices, choiceNames)),
        label='Group these card types globally (Cmd/Ctrl click to select multiple)',
        initial='',
        widget=forms.SelectMultiple(attrs={'size': '4'}))
    start_decks = forms.BooleanField(
        label="Group four start decks with the Base cards", initial=False)
    curse10 = forms.BooleanField(
        label="Group Curse cards into groups of ten cards", initial=False)
    no_trash = forms.BooleanField(
        label="Exclude Trash from cards", initial=False)
    expansion_dividers = forms.BooleanField(
        label="Include Expansion Dividers", initial=False)
    centre_expansion_dividers = forms.BooleanField(
        label="If Expansion Dividers, centre the tabs on expansion dividers",
        initial=False)
    expansion_dividers_long_name = forms.BooleanField(
        label=("If Expansion Dividers, use edition "
               "on expansion dividers names"),
        initial=False)
    set_icon = forms.ChoiceField(
        choices=list(
            zip(domdiv.main.LOCATION_CHOICES, domdiv.main.LOCATION_CHOICES)),
        label="Set Icon Location",
        initial="tab")
    cost_icon = forms.ChoiceField(
        choices=list(
            zip(domdiv.main.LOCATION_CHOICES, domdiv.main.LOCATION_CHOICES)),
        label="Cost Icon Location",
        initial="tab")
    language = forms.ChoiceField(
        choices=list(
            zip(domdiv.main.LANGUAGE_CHOICES, domdiv.main.LANGUAGE_CHOICES)),
        label='Language',
        initial='en_us')
    events = forms.BooleanField(
        label="Exclude Individual Events & Landmarks", initial=False)
    divider_front_text = forms.ChoiceField(
        label='Front Text',
        choices=list(zip(domdiv.main.TEXT_CHOICES, domdiv.main.TEXT_CHOICES)),
        initial='card')
    divider_back_text = forms.ChoiceField(
        label='Back Text',
        choices=list(
            zip(domdiv.main.TEXT_CHOICES + ['none'],
                domdiv.main.TEXT_CHOICES + ['no back page'])),
        initial='rules')
    no_footer = forms.BooleanField(
        label='Omit the expansion name at the bottom of the page', initial=False)
    tag = forms.CharField(widget=forms.HiddenInput(), initial='domdiv')


class ChitBoxForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(ChitBoxForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Div(HTML('<h3>Generation Options</h3>'), css_class='col-md-9'),
                Div(FormActions(
                    Submit('submit', 'Generate', style="margin-top: 20px;")),
                    css_class='col-md-3'),
                css_class='row'),
            Div(
                Div(
                    Accordion(
                        AccordionGroup('Measurements', 'width', 'length',
                                       'height'),
                        AccordionGroup('Images', 'main_image', 'side_image')),
                    css_class='col-md-12',
                ),
                'tag',
                css_class='row',
            ))
        self.helper.form_id = 'id-tabgenoptions'
        self.helper.form_class = 'blueForms'
        self.helper.form_method = 'post'
        self.helper.form_action = '/chitboxes/'
        for field in self.fields.values():
            field.required = False

    width = forms.FloatField(
        label='Width in cm', min_value=1.0, max_value=20.0, initial=5)
    length = forms.FloatField(
        label='Length in cm', min_value=1.0, max_value=20.0, initial=5)
    height = forms.FloatField(
        label='Height in cm', min_value=1.0, max_value=20.0, initial=2)
    main_image = forms.ImageField(label='Upload Main Image')
    side_image = forms.ImageField(label='Upload Side Image')
    tag = forms.CharField(widget=forms.HiddenInput(), initial='chitboxes')


class TuckBoxForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(TuckBoxForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Div(HTML('<h3>Generation Options</h3>'), css_class='col-md-9'),
                Div(FormActions(
                    Submit('submit', 'Generate', style="margin-top: 20px;")),
                    css_class='col-md-3'),
                css_class='row'),
            Div(
                Div(
                    Accordion(
                        AccordionGroup('Measurements', 'width', 'height',
                                       'depth'),
                        AccordionGroup('Images', 'front_image', 'side_image',
                                       'back_image', 'end_image',
                                       'fill_colour', 'preserve_side_aspect',
                                       'preserve_end_aspect')),
                    css_class='col-md-12',
                ),
                'tag',
                css_class='row',
            ))
        self.helper.form_id = 'id-tabgenoptions'
        self.helper.form_class = 'blueForms'
        self.helper.form_method = 'post'
        self.helper.form_action = '/tuckboxes/'
        for field in self.fields.values():
            field.required = False

    width = forms.FloatField(
        label='Width in cm (1-20)', min_value=1.0, max_value=20.0, initial=6)
    height = forms.FloatField(
        label='Height in cm (1-20)', min_value=1.0, max_value=20.0, initial=9.3)
    depth = forms.FloatField(
        label='Depth in cm (1-20)', min_value=1.0, max_value=20.0, initial=3)
    front_image = forms.ImageField(label='Upload Main Image')
    side_image = forms.ImageField(label='Upload Side Image')
    back_image = forms.ImageField(label='Upload Back Image')
    end_image = forms.ImageField(label='Upload End Image')
    preserve_side_aspect = forms.BooleanField(
        label='Preserve Side Image Aspect', initial=True)
    preserve_end_aspect = forms.BooleanField(
        label='Preserve End Image Aspect', initial=True)
    fill_colour = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color'}), initial='#99FF99')
    tag = forms.CharField(widget=forms.HiddenInput(), initial='tuckboxes')


def _init_options_from_form_data(post_data):
    form = TabGenerationOptionsForm(post_data)
    if form.is_valid():
        # generate default options
        options = domdiv.main.parse_opts([])
        options = domdiv.main.clean_opts(options)
        data = form.cleaned_data
        options.orientation = data['orientation'].lower()
        # Separate out the various card sizes
        if 'unsleeved' in data['cardsize'].lower():
            options.size = 'unsleeved'
        else:
            options.size = 'sleeved'
        if 'thick' in data['cardsize'].lower():
            options.sleeved_thick = True
        elif 'thin' in data['cardsize'].lower():
            options.sleeved_thin = True
        # due to argparse this should be a list of lists
        options.expansions = [[e] for e in data['expansions']]
        options.fan = [[e] for e in data['fan_expansions']]
        if data['back_offset']:
            options.back_offset = data['back_offset']
        if data['back_offset_height']:
            options.back_offset_height = data['back_offset_height']
        if data['horizontal_gap']:
            options.horizontal_gap = data['horizontal_gap']
        if data['vertical_gap']:
            options.vertical_gap = data['vertical_gap']
        options.black_tabs = data['black_tabs']
        options.upgrade_with_expansion = data['upgrade_with_expansion']
        options.base_cards_with_expansion = data['base_cards_with_expansion']
        options.wrapper = data['wrappers']
        options.notch = data['notch']
        options.cropmarks = data['cropmarks']
        options.linetype = data['linetype']
        options.tab_serpentine = data['serpentine']
        options.expansion_reset_tabs = data['reset_tabs']
        options.count = data['counts']
        options.types = data['types']
        options.tab_name_align = data['tab_name_align']
        options.tab_number = int(data['tab_number'])
        options.tab_side = data['tab_side']
        options.expansion_dividers = data['expansion_dividers']
        options.centre_expansion_dividers = data['centre_expansion_dividers']
        options.expansion_dividers_long_name = data['expansion_dividers_long_name']
        options.cost = data['cost_icon']
        options.set_icon = data['set_icon']
        options.order = data['order']
        options.group_special = data['group_special']
        options.group_kingdom = data['group_kingdom']
        if not data['group_global']:
            options.group_global = None
        else:
            options.group_global = [[e] for e in data['group_global']]
        options.start_decks = data['start_decks']
        options.curse10 = data['curse10']
        options.no_trash = data['no_trash']
        options.language = data['language']
        options.text_front = data['divider_front_text']
        options.text_back = data['divider_back_text']
        options.no_page_footer = data['no_footer']
        options.tabwidth = data['tabwidth']
        # Paper or Labels?
        if data['pagesize'] in PAPER_SIZES:
            options.papersize = data['pagesize']
            options.label_name = None
        else:
            options.label_name = data['pagesize']
            options.papersize = 'letter'
            options.wrapper = False
            options.notch = False
            options.cropmarks = False
        options = domdiv.main.clean_opts(options)
        print('options after cleaning:', options)
        return options
    return None


def index(request):
    if request.method == 'POST':
        options = _init_options_from_form_data(request.POST)
        print('options after POST:', options)
        # Create the HttpResponse object with the appropriate PDF headers.
        response = HttpResponse(content_type='application/pdf')
        response[
            'Content-Disposition'] = 'attachment; filename="sumpfork_dominion_tabs.pdf"'
        options.outfile = response
        domdiv.main.generate(options)
        return response
    else:
        form = TabGenerationOptionsForm()

    return render(request, 'dominion_dividers/index.html', {
        'form': form,
        'pages': PAGES,
        'active': 'domdiv'
    })


def preview(request):
    print('preview request: {}'.format(request))
    print('preview post: {}'.format(request.POST))
    print('preview files: {}'.format(request.FILES))
    if request.POST['tag'] == 'domdiv':
        return domdiv_preview(request)
    elif request.POST['tag'] == 'chitboxes':
        return chitbox_preview(request)
    elif request.POST['tag'] == 'tuckboxes':
        return tuckbox_preview(request)
    else:
        return HttpResponseBadRequest('Unknown tag: {}'.format(
            request.POST['tag']))


def domdiv_preview(request):
    options = _init_options_from_form_data(request.POST)
    preview_img = domdiv.main.generate_sample(options)
    preview_img = base64.b64encode(preview_img).decode('ascii')
    try:
        return JsonResponse({'preview_data': preview_img})
    except Exception as e:
        return HttpResponseServerError('Error generating domdiv preview: ' +
                                       str(e))


def chitbox_preview(request):
    form = ChitBoxForm(request.POST, request.FILES)
    if form.is_valid():
        data = form.cleaned_data
        generator = ChitBoxGenerator.fromRawData(
            data['width'],
            data['length'],
            data['height'],
            None,
            None,
            None,
        )
        preview_img = generator.generate_sample()
        preview_img = base64.b64encode(preview_img).decode('ascii')
        try:
            return JsonResponse({'preview_data': preview_img})
        except Exception as e:
            return HttpResponseServerError(
                'Error generating chitbox preview: ' + str(e))
    else:
        return HttpResponseBadRequest("invalid form data: {}".format(
            request.POST))


def tuckbox_preview(request):
    form = TuckBoxForm(request.POST, request.FILES)
    if form.is_valid():
        data = form.cleaned_data
        fc = re.match(r'#(\w{2})(\w{2})(\w{2})', data['fill_colour']).groups()
        fc = tuple(int(p, 16) / 255.0 for p in fc)

        c = TuckBoxGenerator.fromRawData(
            data['width'], data['height'], data['depth'],
            fillColour=fc, preserveSideAspect=data['preserve_side_aspect'],
            preserveEndAspect=data['preserve_end_aspect'])
        preview_img = c.generate_sample()
        preview_img = base64.b64encode(preview_img).decode('ascii')
        try:
            return JsonResponse({'preview_data': preview_img})
        except Exception as e:
            return HttpResponseServerError(
                'Error generating tuckbox preview: ' + str(e))
    else:
        return HttpResponseBadRequest("invalid form data: {}".format(
            request.POST))


def chitboxes(request):
    if request.method == 'POST':
        form = ChitBoxForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            # Create the HttpResponse object with the appropriate PDF headers.
            response = HttpResponse(content_type='application/pdf')
            response[
                'Content-Disposition'] = 'attachment; filename="sumpfork_chitbox.pdf"'
            c = ChitBoxGenerator.fromRawData(
                data['width'], data['length'], data['height'], response,
                data['main_image'], data['side_image'])
            c.generate()

            return response
    else:
        form = ChitBoxForm()
    return render(request, 'dominion_dividers/index.html', {
        'form': form,
        'pages': PAGES,
        'active': 'chitboxes'
    })


def tuckboxes(request):
    if request.method == 'POST':
        form = TuckBoxForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            # Create the HttpResponse object with the appropriate PDF headers.
            response = HttpResponse(content_type='application/pdf')
            response[
                'Content-Disposition'] = 'attachment; filename="sumpfork_chitbox.pdf"'
            fc = re.match(r'#(\w{2})(\w{2})(\w{2})',
                          data['fill_colour']).groups()
            fc = tuple(int(p, 16) / 255.0 for p in fc)
            c = TuckBoxGenerator.fromRawData(
                data['width'], data['height'], data['depth'], response,
                data['front_image'], data['side_image'], data['back_image'],
                data['end_image'], fc, data['preserve_side_aspect'],
                data['preserve_end_aspect'])
            c.generate()
            c.close()
            return response
    else:
        form = TuckBoxForm()
    return render(request, 'dominion_dividers/index.html', {
        'form': form,
        'pages': PAGES,
        'active': 'tuckboxes'
    })
