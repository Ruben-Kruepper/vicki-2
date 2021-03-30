from lib.authors            import *
from lib.fcsapi             import fcsapi
from lib.azure_news         import AzureNewsService
from lib.fxstreet_calendar  import FxstreetCalendar
from lib.chart_grabber      import ChartGrabber

import config as cfg

import datetime as dt
import shutil

# 
# API_KWARGS = {
#     'fcsapi'    : fcsapi(cfg.FSCAPI_TOKEN),
#     'fxsc'      : FxstreetCalendar(),
#     'ans'       : AzureNewsService(cfg.AZURE_KEY),
#     'cg'        : ChartGrabber(cfg.TRADINGVIEW_URL, cfg.TRADINGVIEW_USERNAME, cfg.TRADINGVIEW_PASSWORD, cfg.CHART_PATH)
# }
# AUTHORS = [
#     EnglishAuthor('Vicki Master - EN - Crypto Edition', **API_KWARGS),
# ]

# for author in AUTHORS:
#     author.write_stock_sentences()
#     author.write_forex_sentences()

# API_KWARGS['cg'].driver.close()
cg = ChartGrabber(cfg.TRADINGVIEW_URL, cfg.TRADINGVIEW_USERNAME, cfg.TRADINGVIEW_PASSWORD, './test')
cg.make_chart('AUD/USD')
cg.driver.close()
