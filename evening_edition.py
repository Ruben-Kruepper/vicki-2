from lib.authors            import *
from lib.fcsapi             import fcsapi
from lib.azure_news         import AzureNewsService
from lib.fxstreet_calendar  import FxstreetCalendar
from lib.chart_grabber      import ChartGrabber

import config as cfg

import datetime as dt
import shutil

shutil.rmtree(cfg.CHART_PATH, ignore_errors=True)

API_KWARGS = {
    'fcsapi'    : fcsapi(cfg.FSCAPI_TOKEN),
    'fxsc'      : FxstreetCalendar(),
    'ans'       : AzureNewsService(cfg.AZURE_KEY),
    'cg'        : ChartGrabber(cfg.TRADINGVIEW_URL, cfg.TRADINGVIEW_USERNAME, cfg.TRADINGVIEW_PASSWORD, cfg.EVENING_EDITION_CHART_PATH)
}

en_author = EnglishAuthor('Vicki Master - EN - Evening Edition', **API_KWARGS)
# en_author.write_headline_news()
# en_author.write_economic_calendar(date=dt.datetime.today() + dt.timedelta(days=2))
en_author.write_stock_sentences()
en_author.write_forex_sentences()

AUTHORS = [
    (HebrewAuthor, 'Vicki Master - HE - Evening Edition'),
    (HungarianAuthor, 'Vicki Master - HU - Evening Edition'),
    (RussianAuthor, 'Vicki Master - RU - Evening Edition')
]

def gen_authors(authors):
    for author, workbook in authors:
        print(workbook)
        time.sleep(30)
        yield author(workbook, **API_KWARGS)

for author in gen_authors(AUTHORS):
    author.write_economic_calendar()
    author.write_stock_sentences()
    author.write_forex_sentences()

### Begin Crypto ###
author = EnglishAuthor('Vicki Master - EN - Crypto Edition', **API_KWARGS)
author.write_headline_news()
author.write_forex_sentences()

CG = API_KWARGS['cg']

for symbol, name in [
    ('nke', 'nike.png'),
    ('eurusd', 'eurusd.png'),
    ('gbpusd', 'gbpusd.png'),
    ('audusd', 'audusd.png'),
    ('usdjpy', 'usdjpy.png'),
    ('btcusd', 'btcusd.png'),
    ('gold', 'gold.png'),
    ('usoil', 'crudeoil.png'),
    ]:
    CG.make_chart(symbol, name)

API_KWARGS['cg'].driver.close()
