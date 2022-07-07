__author__ = 'tiborkiss'
import requests
from datetime import datetime
import pytz

from pyalgotrade.bar import Bar

# EasternTZ is also present in tools.csv_tools, but that would cause circular include
EasternTZ = pytz.timezone('US/Eastern')

def download_csv(url, url_params=None, content_type="text/csv"):
    response = requests.get(url, params=url_params)

    response.raise_for_status()
    response_content_type = response.headers['content-type']
    if response_content_type != content_type:
        raise Exception("Invalid content-type: %s" % response_content_type)

    ret = response.text

    # Remove the BOM
    while not ret[0].isalnum():
        ret = ret[1:]

    return ret


def get_google_1m_bars_for_year(instrument, year):
    begin = datetime(year, 1, 1)
    end = datetime(year, 12, 31)
    url = "http://www.google.com/finance/historical"
    params = {
        "q": instrument,
        "startdate": begin.strftime("%Y-%m-%d"),
        "enddate": end.strftime("%Y-%m-%d"),
        "output": "csv",
    }

    bars = []
    headerRowSeen = False
    csvContent = download_csv(url, url_params=params, content_type="application/vnd.ms-excel")
    for line in csvContent.split('\n'):
        if len(line) == 0:
            # Skip empty lines
            continue

        if not headerRowSeen:
            if line != 'Date,Open,High,Low,Close,Volume':
                raise Exception("Invalid header row from yahoo: %s" % line)
            else:
                headerRowSeen = True
        (dtStr, open_, high, low, close, volume) = line.split(',')

        if dtStr == 'Date':
            # Skip header row
            continue

        dt = datetime.strptime(dtStr, "%d-%b-%y")
        dt = EasternTZ.localize(dt)

        def safe_parse_float(f):
            try:
                ret = float(f)
            except ValueError:
                ret = float('nan')
            return ret

        bar = Bar(dt, safe_parse_float(open_), safe_parse_float(high), safe_parse_float(low), safe_parse_float(close), 
                  safe_parse_float(volume), safe_parse_float(close))
        bars.append(bar)

    return bars
