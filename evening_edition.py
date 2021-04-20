from lib.authors            import *
from lib.fcsapi             import fcsapi
from lib.azure_news         import AzureNewsService
from lib.fxstreet_calendar  import FxstreetCalendar
from lib.chart_grabber      import ChartGrabber

import config as cfg

import datetime as dt
import shutil

if not dt.datetime.today().weekday() in (4,5):
    API_KWARGS = {
        'fcsapi'    : fcsapi(cfg.FSCAPI_TOKEN),
        'fxsc'      : FxstreetCalendar(),
        'ans'       : AzureNewsService(cfg.AZURE_KEY),
        'cg'        : ChartGrabber(cfg.TRADINGVIEW_URL, cfg.TRADINGVIEW_USERNAME, cfg.TRADINGVIEW_PASSWORD, cfg.EVENING_EDITION_CHART_PATH)
    }

    en_author = EnglishAuthor('Vicki Master - EN - Evening Edition', **API_KWARGS)
    en_author.write_headline_news()
    en_author.write_economic_calendar()
    en_author.write_stock_sentences()
    en_author.write_forex_sentences()

    ### Begin Crypto ###
    author = EnglishAuthor('Vicki Master - EN - Crypto Edition', **API_KWARGS)
    author.write_headline_news()
    author.write_forex_sentences()

    AUTHORS = [
        (GermanAuthor, 'Vicki Master - DE - Evening Edition'),
        (HebrewAuthor, 'Vicki Master - HE - Evening Edition'),
        (HungarianAuthor, 'Vicki Master - HU - Evening Edition'),
        (RussianAuthor, 'Vicki Master - RU - Evening Edition'),
        (ArabicAuthor, 'Vicki Master - AR - Evening Edition'),
        (ItalianAuthor, 'Vicki Master - IT - Evening Edition'),
        (PortugueseAuthor, 'Vicki Master - PT - Evening Edition'),
        (RomanianAuthor, 'Vicki Master - RO - Evening Edition'),
        # (SpanishAuthor, 'Vicki Master - SP - Evening Edition')
    ]

    def gen_authors(authors):
        for author, workbook in authors:
            print(workbook)
            time.sleep(20)
            yield author(workbook, **API_KWARGS)

    for author in gen_authors(AUTHORS):
        author.write_economic_calendar()
        author.write_stock_sentences()
        author.write_forex_sentences()

    API_KWARGS['cg'].driver.close()
