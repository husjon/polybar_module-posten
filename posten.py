#!/usr/bin/env python

import json
import os
import pathlib
import time
import re
import datetime
import sys
import subprocess

import requests


def error(msg=''):
    print('%{F#ff0000}', msg)
    exit(0)


def load_config():
    try:
        with open(BASEDIR / 'config.json', 'r') as fh:
            return json.load(fh)
    except FileNotFoundError:
        error('Config missing')
    except json.decoder.JSONDecodeError:
        error('Config invalid')


def convert_datetime(date):
    m = re.findall(
        pattern=r'\w+ \w+ [0-9.]+$',
        string=date
    )
    date_string = m.pop()

    date_string += f'{datetime.datetime.now().year}'
    parsed_datetime = datetime.datetime.strptime(date_string, '%A %B %d %Y')

    return parsed_datetime


def fetch_postal_data():
    """ Fetches postal data from Posten.no """
    cache_file = BASEDIR / 'cache.json'

    postal_data = None
    if os.path.exists(cache_file):
        if time.time() - os.path.getmtime(cache_file) < 3600 * 4:
            with open(cache_file, 'r') as fh:
                postal_data = json.load(fh)

    if postal_data is None:
        result = requests.get(
            url=API_URL,
            headers={
                'x-requested-with': 'XMLHttpRequest'
            },
            timeout=5
        )

        if result.status_code == 200:
            postal_data = json.loads(result.content)
            with open(cache_file, 'w+') as fh:
                json.dump(postal_data, fh, indent=2)
        else:
            postal_data = {}
            with open(cache_file, 'w+') as fh:
                json.dump(postal_data, fh, indent=2)
            error('No data')

    return postal_data['nextDeliveryDays']


def bar_output():
    next_delivery_date = fetch_postal_data()[0]

    postal_date = next_delivery_date.split(' ')[0]
    if postal_date in ['today', 'tomorrow']:
        color_postal_date = postal_date
    else:
        color_postal_date = 'someday'

    color = '%{{F{}}}'.format(CONFIG['colors'][color_postal_date])

    return {
        "icon": '',
        "color": color,
        "date": postal_date.capitalize(),
        "unit": '',
    }



def notify():
    next_delivery_dates = fetch_postal_data()

    dates_list = [ re.sub('(today|tomorrow) ', '', date) for date in next_delivery_dates ]

    _output = ''
    for date in dates_list:
        _out = re.sub('(today|tomorrow) ', '', date)
        _output += _out.rjust(25) + '\n'

    subprocess.call(f"/usr/bin/notify-send 'Posten Delivery Dates' '{_output}'", shell=True)

    return


def main():
    if sys.argv.pop() == 'notify':
        notify()
    else:
        DATA = bar_output()
        print('{icon} {color}{date}'.format(**DATA))


BASEDIR = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
CONFIG = load_config()
API_URL = (
    "https://www.posten.no/en/delivery-mail/_/component/main/1/leftRegion/1?postCode={postal_code}"
).format(**CONFIG)


if __name__ == "__main__":
    try:
        main()
    except requests.ConnectTimeout:
        error('Timeout')  # https://fontawesome.com/icons/poo-storm?style=solid
    except requests.ConnectionError:
        error('Error')
    except Exception as e:  # pylint: disable=broad-except
        error(f'Error: {e}')  # https://fontawesome.com/icons/poo-storm?style=solid
