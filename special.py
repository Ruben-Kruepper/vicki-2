from lib.authors            import *
from lib.fcsapi             import fcsapi
from lib.azure_news         import AzureNewsService
from lib.fxstreet_calendar  import FxstreetCalendar
from lib.chart_grabber      import ChartGrabber

import config as cfg

import datetime as dt

pseudo_cg = type('', (), {})()
pseudo_cg.make_chart = lambda x: None

API_KWARGS = {
    'fcsapi'    : fcsapi(cfg.FSCAPI_TOKEN),
    'fxsc'      : FxstreetCalendar(),
    'ans'       : AzureNewsService(cfg.AZURE_KEY),
    'cg'        : pseudo_cg # ChartGrabber(cfg.TRADINGVIEW_URL, cfg.TRADINGVIEW_USERNAME, cfg.TRADINGVIEW_PASSWORD, './special/charts')
}

AUTHORS = [
    (PortugueseAuthor, 'Vicki Master - PT - Evening Edition')
]

def gen_authors(authors):
    for author, workbook in authors:
        print(workbook)
        yield author(workbook, **API_KWARGS)

for author in gen_authors(AUTHORS):
    author.write_economic_calendar()
    # author.write_stock_sentences()
    # author.write_forex_sentences()

# API_KWARGS['cg'].driver.close()
