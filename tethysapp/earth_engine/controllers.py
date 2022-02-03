import datetime as dt
from django.shortcuts import render
from tethys_sdk.permissions import login_required
from tethys_sdk.gizmos import SelectInput, DatePicker, Button, MapView, MVView, ButtonGroup, ToggleSwitch
from .gee.products import EE_PRODUCTS
import logging
from django.http import JsonResponse, HttpResponseNotAllowed
from .gee.methods import sentinel1,get_tile_url
import json

log = logging.getLogger(f'tethys.apps.{__name__}')


@login_required()
def home(request):
    """
    Controller for the app home page.
    """
    default_platform = 'sentinel'
    default_sensors = EE_PRODUCTS[default_platform]
    first_sensor_key = next(iter(default_sensors.keys()))
    default_products = default_sensors[first_sensor_key]
    first_product_key = next(iter(default_products.keys()))
    first_product = default_products[first_product_key]

    sentinel1 = Button(
        display_text = 'Sentinel 1',
        name = 'sentinel1',
        style = 'primary',
        attributes={
            'sensor':'1',
            'product':'SAR',
            'id': 'sentinel1_button'
        }
    )
    landsat8 = Button(
        display_text = 'Landsat 8',
        name = 'landsat8',
        style = 'primary',
        attributes={
            'sensor':'8',
            'product':'RAW',
            'id': 'landsat8_button'
        }
    )

    platform_select = ButtonGroup(buttons = [sentinel1, landsat8])

    # Build initial platform control
    # platform_select = SelectInput(
    #     name='platform',
    #     display_text='Satellite Platform',
    #     options=(
    #         ('Sentinel', 'sentinel'),
    #         ('Landsat', 'landsat')
    #     )
    # )

    #Build initial sensor control
    # sensor_options = []

    # for sensor in default_sensors:
    #     sensor_options.append((sensor.upper(), sensor))

    # sensor_select = SelectInput(
    #     name='sensor',
    #     display_text='Sensor',
    #     options=sensor_options
    # )

    # # Build initial product control
    # product_options = []
    # for product, info in default_products.items():
    #     product_options.append((info['display'], product))

    # product_select = SelectInput(
    #     name='product',
    #     display_text='Product',
    #     options=product_options
    # )

    # Hardcode initial end date to today (since all of our datasets extend to present)
    today = dt.datetime.today()
    initial_end_date = today.strftime('%Y-%m-%d')

    # Initial start date will a set number of days before the end date
    # NOTE: This assumes the start date of the dataset is at least 30+ days prior to today
    initial_end_date_dt = dt.datetime.strptime(initial_end_date, '%Y-%m-%d')
    initial_start_date_dt = initial_end_date_dt - dt.timedelta(days=30)
    initial_start_date = initial_start_date_dt.strftime('%Y-%m-%d')

    # Build date controls
    first_product_start_date = first_product.get('start_date', None)
    first_product_end_date = first_product.get('end_date', None) or initial_end_date

    start_date = DatePicker(
        name='start_date',
        display_text='Start Date',
        format='yyyy-mm-dd',
        start_view='decade',
        today_button=True,
        today_highlight=True,
        start_date=first_product_start_date,
        end_date=first_product_end_date,
        initial=initial_start_date,
        autoclose=True
    )

    end_date = DatePicker(
        name='end_date',
        display_text='End Date',
        format='yyyy-mm-dd',
        start_view='decade',
        today_button=True,
        today_highlight=True,
        start_date=first_product_start_date,
        end_date=first_product_end_date,
        initial=initial_end_date,
        autoclose=True
    )

    # Build reducer method control
    reducer_select = SelectInput(
        name='reducer',
        display_text='Reduction Method',
        options=(
            ('Median', 'median'),
            ('Mode', 'mode'),
            ('Mean', 'mean'),
            ('Minimum', 'min'),
            ('Maximum', 'max'),
        )
    )

    # Build Buttons
    load_button = Button(
        name='load_map',
        display_text='Load',
        style='default',
        attributes={'id': 'load_map'}
    )

    map_view = MapView(
        height='100%',
        width='100%',
        controls=[
            # {'ZoomToExtent': {
            #     'projection': 'EPSG:4326',
            #     'extent': [29.25, -4.75, 46.25, 5.2]  #: Kenya
            # }}
        ],
        basemap=[
            'CartoDB',
            'ESRI'
        ],
        view=MVView(
            projection='EPSG:4326',
            center=[-10, 20],
            zoom=3,
            maxZoom=18,
            minZoom=2
        )
    )

    clear_button = Button(
        name='clear_map',
        display_text='Clear',
        style='default',
        attributes={'id': 'clear_map'}
    )

    context = {
        'platform_select': platform_select,
        # 'sensor_select': sensor_select,
        # 'product_select': 'SAR',
        'start_date': start_date,
        'end_date': end_date,
        'reducer_select': reducer_select,
        'load_button': load_button,
        'clear_button': clear_button,
        'ee_products': EE_PRODUCTS,
        'map_view': map_view
    }

    return render(request, 'earth_engine/home.html', context)

@login_required()
def get_image_collection(request):
    """
    Controller to handle image collection requests.
    """
    response_data = {'success': False}

    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    try:
        log.debug(f'POST: {request.POST}')

        platform = request.POST.get('platform', None)
        sensor = request.POST.get('sensor', None)
        product = request.POST.get('product', None)
        start_date = request.POST.get('start_date', None)
        end_date = request.POST.get('end_date', None)
        reducer = request.POST.get('reducer', None)

        url = get_image_collection_asset(
            platform=platform,
            sensor=sensor,
            product=product,
            date_from=start_date,
            date_to=end_date,
            reducer=reducer
        )

        log.debug(f'Image Collection URL: {url}')

        response_data.update({
            'success': True,
            'url': url
        })

    except Exception as e:
        response_data['error'] = f'Error Processing Request: {e}'

    return JsonResponse(response_data)

def retrieve_layer(request):
    print("calling retrieve_layers")
    response_data = {'success': False}

    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    try:
        log.debug(f'GET: {request.GET}')

        region = request.GET.get('input_spatial', None)
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)


        imgs = sentinel1(json.loads(region),start_date,end_date)
        wurl = get_tile_url(imgs["water"].selfMask(), {"min":0,"max":1,"palette": "darkblue"})
        surl = get_tile_url(imgs["satellite"], {"bands":"VV","min":-25,"max":0})

        # log.debug(f'Image Collection URL: {url}')

        response_data.update({
            'success': True,
            'water_url': wurl,
            'image_url': surl
        })

    except Exception as e:
        response_data['error'] = f'Error Processing Request: {e}'

    return JsonResponse(response_data)
