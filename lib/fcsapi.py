import requests as re
import json
import urllib.parse
import inspect
from datetime import datetime, timedelta
import time

class fcsapi():

    indicator_mapping = {
        'RSI14':                'RSI',
        'STOCH9_6':             'Stochastic indicator',
        'STOCHRSI14':           'Stochastic-RSI',
        'MACD12_26':            'MACD',
        'WilliamsR':            'Williams indicator',
        'CCI14':                'CCI',
        'ATR14':                'ATR',
        'UltimateOscillator':   'Ultimate Oscillator',
        'ROC':                  'ROC'
    }

    default_headers = {
        'Cookie': 'c_reffer=direct'
    }

    def __init__(self, access_key):
        self.access_key = access_key
        self.cache = {function_name: {} for function_name, _ in inspect.getmembers(self, predicate=inspect.ismethod) if function_name.startswith('query')}

    def patch_candles(self, response: dict):
        sorted_by_date = sorted(response.keys())
        return [response[x] for x in sorted_by_date]

    def query_fx_pair(self, symbol, candle='1d'):
        if symbol in self.cache['query_fx_pair']:
            return self.cache['query_fx_pair'][symbol]
        time.sleep(4)
        params = {
            'access_key':   self.access_key,
            'period':       candle,
            'symbol':       symbol,
            'level':        1,
        }
        url = 'https://fcsapi.com/api-v3/forex/history?' + urllib.parse.urlencode(params).replace('%2F', '/')
        res = re.get(url, headers=self.default_headers)
        try:
            response = self.patch_candles(json.loads(res.text)['response'])
        except:
            print(url)
            print(symbol, res, res.text)
            return
        self.cache['query_fx_pair'][symbol] = response
        return response
        
    def query_fx_indicator(self, symbol, candle='1d'):
        if symbol in self.cache['query_fx_indicator']:
            return self.cache['query_fx_indicator'][symbol]
        time.sleep(4)
        params = {
            'access_key':   self.access_key,
            'period':       candle,
            'symbol':       symbol,
            'level':        1,
        }
        url = 'https://fcsapi.com/api-v3/forex/indicators?' + urllib.parse.urlencode(params).replace('%2F', '/')
        response = json.loads(re.get(url, headers=self.default_headers).text)['response']
        overall_summary = response['overall']['summary']
        indicators = response['indicators']
        renamed_indicators = {}
        for key in indicators:
            if key in self.indicator_mapping:
                renamed_indicators[self.indicator_mapping[key]] = indicators[key]
            else:
                renamed_indicators[key] = indicators[key]
        
        self.cache['query_fx_indicator'][symbol] = { 'overall_summary': overall_summary, 'indicators': renamed_indicators }
        return { 'overall_summary': overall_summary, 'indicators': renamed_indicators }
    
    def query_fx_pivots(self, symbol, candle='1d'):
        if symbol in self.cache['query_fx_pivots']:
            return self.cache['query_fx_pivots'][symbol]
        time.sleep(4)
        params = {
            'access_key':   self.access_key,
            'period':       candle,
            'symbol':       symbol,
            'level':        1,
        }
        url = 'https://fcsapi.com/api-v3/forex/pivot_points?' + urllib.parse.urlencode(params).replace('%2F', '/')
        response = json.loads(re.get(url, headers=self.default_headers).text)['response']
        self.cache['query_fx_pivots'][symbol] = response
        return response

    def query_stock(self, stock, candle='1d'):
        if stock in self.cache['query_stock']:
            return self.cache['query_stock'][stock]
        if ':' in stock:
            params = {
                'access_key':   self.access_key,
                'period':       candle,
                'exchange':     stock.split(':')[0],
                'symbol':       stock.split(':')[1],
                'level':        1,
            } 
        else:
            params = {
                'access_key':   self.access_key,
                'period':       candle,
                'symbol':       stock,
                'level':        1,
            }
        time.sleep(4)
        url = 'https://fcsapi.com/api-v3/stock/history?' + urllib.parse.urlencode(params).replace('%2F', '/')
        try:
            response = self.patch_candles(json.loads(re.get(url, headers=self.default_headers).text)['response'])
        except Exception as e:
            print('Error querying stock:', stock)
            print(e)
            raise
        self.cache['query_stock'][stock] = response
        return response

    def query_stock_indicator(self, stock, candle='1d'):
        if stock in self.cache['query_stock_indicator']:
            return self.cache['query_stock_indicator'][stock]
        if ':' in stock:
            params = {
                'access_key':   self.access_key,
                'period':       candle,
                'exchange':     stock.split(':')[0],
                'symbol':       stock.split(':')[1],
                'level':        1,
            } 
        else:
            params = {
                'access_key':   self.access_key,
                'period':       candle,
                'symbol':       stock,
                'level':        1,
            }
        time.sleep(4)
        url = 'https://fcsapi.com/api-v3/stock/indicators?' + urllib.parse.urlencode(params).replace('%2F', '/')
        try:
            response = re.get(url, headers=self.default_headers)
            response = json.loads(response.text)['response']
        except Exception as e:
            print(stock)
            print(response)
            print(response.text)
            raise e
        overall_summary = response['overall']['summary']
        indicators = response['indicators']
        renamed_indicators = {}
        for key in indicators:
            if key in self.indicator_mapping:
                renamed_indicators[self.indicator_mapping[key]] = indicators[key]
            else:
                renamed_indicators[key] = indicators[key]

        self.cache['query_stock_indicator'][stock] = { 'overall_summary': overall_summary, 'indicators': renamed_indicators }
        return { 'overall_summary': overall_summary, 'indicators': renamed_indicators }

    def query_stock_pivots(self, stock, candle='1d'):
        if stock in self.cache['query_stock_pivots']:
            return self.cache['query_stock_pivots'][stock]
        if ':' in stock:
            params = {
                'access_key':   self.access_key,
                'period':       candle,
                'exchange':     stock.split(':')[0],
                'symbol':       stock.split(':')[1],
                'level':        1,
            } 
        else:
            params = {
                'access_key':   self.access_key,
                'period':       candle,
                'symbol':       stock,
                'level':        1,
            }
        time.sleep(4)
        url = 'https://fcsapi.com/api-v3/stock/pivot_points?' + urllib.parse.urlencode(params).replace('%2F', '/')
        response = json.loads(re.get(url, headers=self.default_headers).text)['response']
        self.cache['query_stock_pivots'][stock] = response
        return response

    # def query_index(self, index, candle='1d'):
    #     if index in self.cache['query_index']:
    #         return self.cache['query_index'][index]
    # time.sleep(4)    
    # params = {
    #         'access_key':   self.access_key,
    #         'period':       candle,
    #         'symbol':       index,
    #         'level':        1,
    #     }
    #     url = 'https://fcsapi.com/api-v3/stock/index/history?' + urllib.parse.urlencode(params).replace('%2F', '/')
    #     response = json.loads(re.get(url, headers=self.default_headers).text)['response']
    #     self.cache['query_index'][index] = response
    #     return response

    # def query_index_indicator(self, index, candle='1d'):
    #     if index in self.cache['query_index_indicator']:
    #         return self.cache['query_index_indicator'][index]
    # time.sleep(4)    
    # params = {
    #         'access_key':   self.access_key,
    #         'period':       candle,
    #         'symbol':       index,
    #         'level':        1,
    #     }
    #     url = 'https://fcsapi.com/api-v3/stock/index/indicators?' + urllib.parse.urlencode(params).replace('%2F', '/')
    #     response = json.loads(re.get(url, headers=self.default_headers).text)['response']
    #     overall_summary = response['overall']['summary']
    #     indicators = response['indicators']
    #     renamed_indicators = {}
    #     for key in indicators:
    #         if key in self.indicator_mapping:
    #             renamed_indicators[self.indicator_mapping[key]] = indicators[key]
    #         else:
    #             renamed_indicators[key] = indicators[key]

    #     self.cache['query_index_indicator'][index] = { 'overall_summary': overall_summary, 'indicators': renamed_indicators }
    #     return { 'overall_summary': overall_summary, 'indicators': renamed_indicators }

    # def query_index_pivots(self, index, candle='1d'):
    #     if index in self.cache['query_index_pivots']:
    #         return self.cache['query_index_pivots'][index]
    # time.sleep(4)    
    # params = {
    #         'access_key':   self.access_key,
    #         'period':       candle,
    #         'symbol':       index,
    #         'level':        1,
    #     }
    #     url = 'https://fcsapi.com/api-v3/stock/index/pivot_points?' + urllib.parse.urlencode(params).replace('%2F', '/')
    #     response = json.loads(re.get(url, headers=self.default_headers).text)['response']
    #     self.cache['query_index_pivots'][index] = response
    #     return response