import json
import re
from datetime import datetime as dt
from datetime import timedelta
import urllib


import time
import pandas as pd
import requests


class FxstreetCalendar():

    def get_definition(self, event_id):
        url = "https://calendar-api.fxstreet.com/en/api/v1/eventDates/" + event_id
        headers = {
            'authority': 'calendar-api.fxstreet.com',
            'method': 'GET',
            'path': url[url.find('https://calendar-api.fxstreet.com'):],
            'scheme': 'https',
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br',
            'origin': 'https://www.fxstreet.com',
            'referer': 'https://www.fxstreet.com/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f'Response returned with code {response.status_code}')
            return None
        content = json.loads(response.text)
        description = content['description']
        description = re.sub('<a.+?>|</a>', '', description)
        description = description.replace('  ', ' ')
        description = '. '.join(description.split('. ')[:3])
        time.sleep(0.1)
        return description

    def get_calendar_df(self, from_=(dt.today()+timedelta(days=2)), to_=(dt.today()+timedelta(days=2))):
        url = "https://calendar-api.fxstreet.com/en/api/v1/eventDates/"
        url += from_.strftime('%Y-%m-%d') + 'T00:00:00Z/'
        url += to_.strftime('%Y-%m-%d') + 'T23:59:59Z'
        headers = {
            'authority': 'calendar-api.fxstreet.com',
            'method': 'GET',
            'path': url[url.find('https://calendar-api.fxstreet.com'):],
            'scheme': 'https',
            'accept': 'application/json',
            'accept-encoding': 'gzip, deflate, br',
            'origin': 'https://www.fxstreet.com',
            'referer': 'https://www.fxstreet.com/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f'Response returned with code {response.status_code}')
            print(response.content)
            return None
        content = json.loads(response.text)
        df = pd.DataFrame(content)[['id', 'name', 'dateUtc', 'previous', 'unit', 'currencyCode', 'countryCode', 'volatility', 'potency']]
        df['name'] = df['name'].apply(lambda x: re.sub(r'\([^)]*\)|([a-zA-Z]\.)+[a-zA-Z]?|\sex.*|\sa|\,.*', '', x).split(' - ')[0].strip())

        df['previous'] = df['previous'].astype(str).str.replace('None', '---').str.replace('NaN', '---').str.replace('nan', '---')
        df['unit'] = df['unit'].astype(str).str.replace('None', '')
        df['potency'] = df['potency'].astype(str)
        df['previous'] = (df['previous'] + df['unit']).where((df['potency']=='ZERO') | (df['potency']=='None'), (df['unit'] + df['previous'] + df['potency']))
        df = df[df['volatility']!='NONE']
        df['dateUtc'] = pd.to_datetime(df['dateUtc'], format='%Y-%m-%dT%H:%M:%SZ')
        df = df.drop_duplicates(subset=['name', 'currencyCode'])
        df['volatility'] = pd.Categorical(df['volatility'], ['HIGH', 'MEDIUM', 'LOW'])
        return df
