from lib.authors            import *
from lib.fcsapi             import fcsapi
from lib.azure_news         import AzureNewsService
from lib.fxstreet_calendar  import FxstreetCalendar
from lib.chart_grabber      import ChartGrabber

import config as cfg

import datetime as dt
import shutil
import time

shutil.rmtree(cfg.CHART_PATH, ignore_errors=True)

API_KWARGS = {
    'fcsapi'    : fcsapi(cfg.FSCAPI_TOKEN),
    'fxsc'      : FxstreetCalendar(),
    'ans'       : AzureNewsService(cfg.AZURE_KEY),
    'cg'        : ChartGrabber(cfg.TRADINGVIEW_URL, cfg.TRADINGVIEW_USERNAME, cfg.TRADINGVIEW_PASSWORD, cfg.NOON_EDITION_CHART_PATH)
}
AUTHORS = [
    (EnglishAuthor, 'Vicki Master - EN - Noon Edition'),
    (JapaneseAuthor, 'Vicki Master - JP - Noon Edition'), 
    (ThaiAuthor, 'Vicki Master - TH - Noon Edition'),
    (ChineseAuthor, 'Vicki Master - CN - Noon Edition'),
    (MalaysianAuthor, 'Vicki Master - MY - Noon Edition'),
    (VietnameseAuthor, 'Vicki Master - VN - Noon Edition')
]


EnglishAuthor('Vicki Master - EN - Noon Edition', **API_KWARGS).write_headline_news()

def gen_authors(authors):
    for author, workbook in authors:
        print(workbook)
        yield author(workbook, **API_KWARGS)

for author in gen_authors(AUTHORS):
    author.write_stock_sentences()
    author.write_forex_sentences()
    author.write_economic_calendar(date=dt.datetime.today() + dt.timedelta(days=1))
    time.sleep(30)

API_KWARGS['cg'].driver.close()