import requests as rq
import datetime
import re
import json
import urllib


class AzureNewsService:
    providers = ['Reuters', 'Bloomberg', 'MarketWatch', 'CoinDesk', 'CoinTelegraph', 'DailyFX']
    def __init__(self, key):
        self.subscription_key = key

    def make_news(self, q):
        news_dict = self.make_news_dict(q)
        # Yield select providers first
        for provider in self.providers:
            try:
                provider_headlines = news_dict[provider]
            except KeyError: continue
            
            for headline in provider_headlines:
                yield headline
        # Yield other providers later
        for provider in news_dict:
            if provider in self.providers: continue
            provider_headlines = news_dict[provider]
            for headline in provider_headlines:
                yield headline
        # Finally keep yielding ''
        while True:
            yield ''

    def make_news_dict(self, q):
        result = {}
        news = self.query_news(q)['value']
        for line in news:
            if self.check_line(line):
                try:
                    result[line['provider'][0]['name']].append({
                            'headline_name': line['name'], 
                            'headline_description': line['description'], 
                            'date_published': line['datePublished'], 
                            'provider': line['provider'][0]['name'],
                            'url': line['url']

                        })
                except KeyError:
                    result[line['provider'][0]['name']] = [{
                            'headline_name': line['name'], 
                            'headline_description': line['description'], 
                            'date_published': line['datePublished'], 
                            'provider': line['provider'][0]['name'], 
                            'url': line['url']
                        }]
        return result

    def query_news(self, q, mkt='en-us'):
        params = {
            'q':q,
            'mkt':mkt,
            'freshness': 'Day',
            'category': 'Business'
        }
        url = 'https://api.bing.microsoft.com/v7.0/news/search?' + urllib.parse.urlencode(params)
        response = json.loads(rq.get(url, headers={'Ocp-Apim-Subscription-Key':self.subscription_key}).text)
        return response

    def check_line(self, line):
        if 'video' in line:
            return False
        if self.is_clean(line['name']) and self.is_clean(line['description']) and line['description'].strip()[-1] == '.':
                return True
        return False

    def is_clean(self, s):
        if '?' in s:
            return False
        if any(x in s.lower() for x in ['buy','sell',' i ']):
            return False
        return True
