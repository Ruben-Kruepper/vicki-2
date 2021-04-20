from urllib.parse import quote
from pandas.core.frame import DataFrame
from pandas.core.indexes import period
import yaml
import random
import pandas as pd
import re
import datetime as dt
import time

from yaml import events

from lib.fcsapi import fcsapi
from lib.fxstreet_calendar import FxstreetCalendar
from lib.azure_news import AzureNewsService
from lib.vicki_operator import Operator
from lib.chart_grabber import ChartGrabber
from lib.chart_grabber import chart_name

# Make headlines linked to stock

def calc_change(first, last):
    return (float(last)-float(first))/float(first)*100

class ShellManager(Operator):

    def __init__(self, workbook_name: str, shell_file: str, fcsapi: fcsapi, ans: AzureNewsService, fxsc: FxstreetCalendar, cg: ChartGrabber):
        super().__init__(workbook_name)
        with open(shell_file, encoding='utf-8') as f:
            shell_master = yaml.load(f, Loader=yaml.FullLoader)

        self.forex_shells       = shell_master['forex_shells']
        self.stock_shells       = shell_master['stock_shells']
        self.indicator_shells   = shell_master['indicator_shells']
        self.fcsapi             = fcsapi
        self.ans                = ans
        self.fxsc               = fxsc
        self.cg                 = cg

        keywords_df = self.workbook.sheet_to_df(sheet='Keywords', index=None)
        self.symbol_translations = dict(zip(keywords_df['symbol'], keywords_df['translated_symbol']))
        self.indicator_translations = dict(zip(keywords_df['indicator'], keywords_df['translated_indicator']))
        self.signal_translations = dict(zip(keywords_df['signal'], keywords_df['translated_signal']))
        self.countries_possessive = dict(zip(keywords_df['country'], keywords_df['country_possesive']))
    
    ################################################################
    # Fill out stock master sheet
    ################################################################
    def write_stock_sentences(self, sheet='Stocks'):
        table = self.workbook.sheet_to_df(sheet=sheet).to_dict('records')
        marks = list(range(len(table)))
        random.shuffle(marks)
        random_marks = iter(marks)
        for row in table:
            symbol = row['symbol']
            try:
                # select stock shells
                candles = self.fcsapi.query_stock(symbol)
                days = random.choice([1, 1]) # Expand to allow for different time periods
                period_change = calc_change(candles[-days]['o'], candles[-1]['c'])
                period_high = max(calc_change(candles[-days]['o'], x['h']) if calc_change(candles[-days]['o'], x['h']) > 0 else 0 for x in candles[-days:])
                period_low = min(calc_change(candles[-days]['o'], x['l']) if calc_change(candles[-days]['o'], x['h']) < 0 else 0 for x in candles[-days:])
                narration_stock_shell, lower_line_shell = self.select_stock_shells(days, period_change, period_high, period_low)
            except:
                print('Error on:', symbol)
                continue
            # make indicator sentences
            tech_analysis = self.fcsapi.query_stock_indicator(symbol)
            narration_indicator, indicator_lower_line = self.write_indicator_sentence(tech_analysis)

            # collect information to fill shells
            kwargs = {
                'symbol': symbol,
                'company_name': row['company_name'],
                'period_change': self.format_percentage_float(period_change),
                'period_high': self.format_percentage_float(period_high),
                'period_low': self.format_percentage_float(period_low)
            }
            pivots = self.fcsapi.query_stock_pivots(symbol)
            pivots = pivots['pivot_point']['classic']
            # write to row
            row['narration'] = self.fill_shell(narration_stock_shell, **kwargs) + ' ' + narration_indicator
            row['lower_line'] = self.fill_shell(lower_line_shell, **kwargs)
            row['indicator_line'] = indicator_lower_line
            for x in ('R2', 'R1', 'S1', 'S2'):
                row[x] = pivots[x]
            row['mark'] = next(random_marks)
            row['chart_name'] = chart_name(symbol)
            self.cg.make_chart(symbol)
        self.workbook.df_to_sheet(pd.DataFrame(table), sheet=sheet)

    def select_stock_shells(self, days, period_change, period_high, period_low):
        possible = []
        # Simple shells
        if period_change <= -3:
            possible += ['major_fall'] * 3
        elif period_change <= -0.4:
            possible += ['simple_fall'] * 2
        elif period_change <= -0.1:
            possible += ['minor_fall']
        elif abs(period_change) <= 0.1:
            possible += ['no_change']
        elif period_change <= 0.4:
            possible += ['minor_gain']
        elif period_change <= 3:
            possible += ['simple_gain'] * 2
        else:
            possible += ['major_gain'] * 3
        
        # High combo shells
        if period_high >= 3:
            if period_change <= -0.1:
                possible += ['fall_with_high']
            elif abs(period_change) <= 0.1:
                pass # TODO Write corresponding shells
            else:
                possible += ['gain_with_high']
        # Low combo shells
        if period_low <= -3:
            if period_change <= -0.1:
                possible += ['fall_with_low']
            elif abs(period_change) <= 0.1:
                pass # TODO Write corresponding shells
            else:
                possible += ['gain_with_low']

        narration_selected_category = random.choice(possible)
        narration_shell = random.choice(self.stock_shells['narration'][narration_selected_category])
        lower_line_possible = list(set(self.stock_shells['lower_line'].keys()).intersection(possible))
        lower_line_shell = random.choice(self.stock_shells['lower_line'][random.choice(lower_line_possible)])
        return narration_shell, lower_line_shell
    
    ################################################################
    # Fill out forex master sheet
    ################################################################
    def write_forex_sentences(self, sheet='Forex'):
        table = self.workbook.sheet_to_df(sheet=sheet).to_dict('records')
        marks = list(range(len(table)))
        random_marks = iter(marks)
        for row in table:
            symbol = row['symbol']
            base_verbose = row['base_verbose']
            quote_verbose = row['quote_verbose']
            pair_verbose = self.make_pair_verbose(base_verbose, quote_verbose)

            # select forex shells
            candles = self.fcsapi.query_fx_pair(symbol)
            days = random.choice([1, 1]) # Expand to allow for different time periods
            period_change = calc_change(candles[-days]['o'], candles[-1]['c'])
            period_high = max(calc_change(candles[-days]['o'], x['h']) if calc_change(candles[-days]['o'], x['h']) > 0 else 0 for x in candles[-days:])
            period_low = min(calc_change(candles[-days]['o'], x['l']) if calc_change(candles[-days]['o'], x['h']) < 0 else 0 for x in candles[-days:])
            narration_forex_shell, lower_line_shell = self.select_forex_shells(days, period_change, period_high, period_low)
            
            # make indicator sentences
            tech_analysis = self.fcsapi.query_fx_indicator(symbol)
            narration_indicator, indicator_lower_line = self.write_indicator_sentence(tech_analysis)

            # collect information to fill shells
            kwargs = {
                'symbol': self.translate_symbol(symbol)[0],
                'base_symbol': self.translate_symbol(symbol)[1],
                'base_verbose': base_verbose,
                'quote_symbol': self.translate_symbol(symbol)[2],
                'quote_verbose': quote_verbose,
                'pair_verbose': pair_verbose,
                'period_change': self.format_percentage_float(period_change),
                'period_high': self.format_percentage_float(period_high),
                'period_low': self.format_percentage_float(period_low)
            }
            pivots = self.fcsapi.query_fx_pivots(symbol)
            pivots = pivots['pivot_point']['classic']
            # write to row
            row['narration'] = self.fill_shell(narration_forex_shell, **kwargs) + ' ' + narration_indicator
            row['lower_line'] = self.fill_shell(lower_line_shell, **kwargs)
            row['indicator_line'] = indicator_lower_line
            for x in ('R2', 'R1', 'S1', 'S2'):
                row[x] = pivots[x]
            row['mark'] = next(random_marks)
            row['chart_name'] = chart_name(symbol)
            self.cg.make_chart(symbol)
        self.workbook.df_to_sheet(pd.DataFrame(table)[['narration', 'lower_line', 'indicator_line', 'R2', 'R1', 'S1', 'S2', 'chart_name']], sheet=sheet, start='F1', index=False)

    def select_forex_shells(self, days, period_change, period_high, period_low):
        possible = []
        # Simple shells
        if period_change <= -1:
            possible += ['major_fall'] * 3
        elif period_change <= -0.3:
            possible += ['simple_fall'] * 2
        elif period_change <= -0.1:
            possible += ['minor_fall']
        elif abs(period_change) <= 0.1:
            possible += ['no_change']
        elif period_change <= 0.3:
            possible += ['minor_gain']
        elif period_change <= 1:
            possible += ['simple_gain'] * 2
        else:
            possible += ['major_gain'] * 3
        
        # High combo shells
        if period_high >= 1:
            if period_change <= -0.1:
                possible += ['fall_with_high']
            elif abs(period_change) <= 0.1:
                pass # TODO Write corresponding shells
            elif period_change >= 0.1 and abs(period_high - period_change) >= 0.3:
                possible += ['gain_with_high']
        # Low combo shells
        if period_low <= -1:
            if period_change <= -0.1 and abs(period_change - period_low) >= 0.3:
                possible += ['fall_with_low']
            elif abs(period_change) <= 0.1:
                pass # TODO Write corresponding shells
            elif period_change >= 0.1:
                possible += ['gain_with_low']

        narration_selected_category = random.choice(possible)
        narration_shell = random.choice(self.forex_shells['narration'][narration_selected_category])
        lower_line_possible = list(set(self.forex_shells['lower_line'].keys()).intersection(possible))
        lower_line_shell = random.choice(self.forex_shells['lower_line'][random.choice(lower_line_possible)])
        return narration_shell, lower_line_shell
    
    ################################################################
    # Indicator sentence writer for all sheets
    ################################################################
    def write_indicator_sentence(self, tech_analysis):
        indicators = tech_analysis['indicators']
        indicators.pop('summary', None)
        indicators.pop('ATR', None)

        overall_summary = tech_analysis['overall_summary']

        # Bias against neutral
        no_neutrals = dict((k, indicators[k]) for k in indicators if indicators[k]['s'] != 'Neutral')
        if no_neutrals:
            indicators = no_neutrals

        # Choose random indicator:
        indicator = random.choice(list(indicators.keys()))
        signal = indicators[indicator]['s']

        # Identify possible shell subtypes
        possible = []
        if 'Buy' in signal or 'Sell' in signal:
            possible.append('simple_signal')
        elif 'Overbought' in signal or 'Oversold' in signal:
            possible.append('market_status')
        else:
            possible.append('neutral_signal')

        if ('Buy' in overall_summary and 'Buy' in signal) or ('Sell' in overall_summary and 'Sell' in signal):
            possible.append('align_signal')

        if ('Buy' in overall_summary and 'Oversold' in signal) or ('Sell' in overall_summary and 'Overbought' in signal):
            possible.append('align_market_status')

        if ('Buy' in overall_summary and 'Sell' in signal) or ('Sell' in overall_summary and 'Buy' in signal):
            possible.append('adverse_signal')
        if not possible:
            print()

        narration_indicator_shell = random.choice(self.indicator_shells['narration'][random.choice(possible)])
        lower_line_possible = list(set(possible).intersection(self.indicator_shells['lower_line'].keys()))
        lower_line_shell = random.choice(self.indicator_shells['lower_line'][random.choice(lower_line_possible)])
        signal = self.signal_translations[signal.lower()]
        overall_summary = 'buy' if 'Buy' in overall_summary else 'sell' if 'Sell' in overall_summary else overall_summary.lower()
        overall_summary = self.signal_translations[overall_summary]
        kwargs = {
            'indicator': self.indicator_translations[indicator],
            'signal': signal,
            'overall_summary': overall_summary
        }
        return self.fill_shell(narration_indicator_shell, **kwargs), self.fill_shell(lower_line_shell, **kwargs)
    
    ################################################################
    # Overwriteables (format, fill, etc.)
    ################################################################
    def verbose_pair(self, symbol):
        symbol = symbol.split('/')
        verbose_pair = f'{self.currency_names[symbol[0]]}-{self.currency_names[symbol[1]]}'
        verbose_base = self.currency_names[symbol[0]]
        verbose_quote = self.currency_names[symbol[1]]
        return verbose_pair, verbose_base, verbose_quote

    def fill_shell(self, shell, **kwargs):
        raise NotImplementedError('Required fill_shell method')
    
    def format_percentage_float(self, percentage_float):
        string = str(abs(percentage_float))
        period_idx = string.find('.')
        return string[:period_idx + 2]
    
    ################################################################
    # Calendar Section
    ################################################################
    def write_economic_calendar(self, date=dt.datetime.today().date() + dt.timedelta(days=1), sheet='Economic Calendar', db_sheet_name='Economic Calendar Definitions'):
        currencies_list = list(self.workbook.sheet_to_df(sheet=sheet)['currencies_list'])
        l1_currencies = currencies_list[currencies_list.index('Level 1')+1:currencies_list.index('Level 2')]
        l2_currencies = currencies_list[currencies_list.index('Level 2')+1:currencies_list.index('Level 3')]
        l3_currencies = currencies_list[currencies_list.index('Level 3')+1:]

        events_df = self.fxsc.get_calendar_df(from_=date, to_=date)
        all_known = self.workbook.sheet_to_df(sheet=db_sheet_name)
        known_coming = events_df.merge(all_known, on='name')

        number_of_events = 6
        l1_events = self.select_events(known_coming, l1_currencies, number_of_events)
        number_of_events -= len(l1_events)
        # Try to fill up with l2 events
        l2_events = self.select_events(known_coming, l2_currencies, number_of_events)
        number_of_events -= len(l2_events)
        # If necessary fill up with l3 events
        l3_events = self.select_events(known_coming, l3_currencies, number_of_events)
        out_df = pd.concat([l1_events, l2_events, l3_events], ignore_index=True)
        
        
        # Tomorrow while necessary
        date = date + (dt.timedelta(days=7-date.weekday()) if date.weekday() in [3, 4] else dt.timedelta(days=1))
        events_df = self.fxsc.get_calendar_df(from_=date, to_=date)
        all_known = self.workbook.sheet_to_df(sheet=db_sheet_name)
        known_coming = events_df.merge(all_known, on='name')

        number_of_events = 6
        l1_events = self.select_events(known_coming, l1_currencies, number_of_events)
        number_of_events -= len(l1_events)
        # Try to fill up with l2 events
        l2_events = self.select_events(known_coming, l2_currencies, number_of_events)
        number_of_events -= len(l2_events)
        # If necessary fill up with l3 events
        l3_events = self.select_events(known_coming, l3_currencies, number_of_events)
        out_df = pd.concat([out_df, l1_events, l2_events, l3_events], ignore_index=True)
        # Make titles 
        out_df['title'] = out_df.apply(self.make_title, axis=1)
        event_list = out_df.to_dict('records')
        out_df.at[0, 'narration'] = self.make_narration(event_list[:3])
        out_df.at[3, 'narration'] = self.make_narration(event_list[3:6])
        out_df.at[6, 'narration'] = self.make_narration(event_list[6:9])
        out_df.at[9, 'narration'] = self.make_narration(event_list[9:])
        # Fix up for push
        out_df = pd.concat([pd.DataFrame({'currencies_list': currencies_list}), out_df], axis=1)
        out_df = out_df[['currencies_list', 'title', 'definition', 'dateUtc', 'previous', 'countryCode', 'narration']]
        self.workbook.df_to_sheet(out_df, sheet=sheet)
    
    def select_events(self, events_df: pd.DataFrame, currencies, max_number):
        country_events = events_df[events_df['currencyCode'].isin(currencies)]
        country_events = events_df[events_df['countryCode'].isin(self.countries_possessive.keys())]
        events_by_currency = []
        for i in range(5):
            for x in currencies:
                currency_events = country_events[country_events['currencyCode']==x]
                if len(currency_events) > 0:
                    if len(currency_events) <= i:
                        events_by_currency.append(currency_events)
                    else:
                        events_by_currency.append(currency_events.sort_values('volatility').head(i))
            if sum(len(x) for x in events_by_currency) >= max_number or i==4:
                break
            else:
                events_by_currency = []
        try:
            selected_rows = pd.concat(events_by_currency)
        except ValueError:
            selected_rows = pd.DataFrame(columns=events_df.columns)
        if len(selected_rows) > max_number:
            return selected_rows.sample(max_number)
        return selected_rows

    def make_narration(self, event_list):
        raise NotImplementedError('Required make_narration method')

    def make_title(self, row):
        raise NotImplementedError('Required make_title method')

    def fill_shell(self, shell, **kwargs):
        for key, value in kwargs.items():
            placeholder = '$' + key + '$'
            value = str(value)
            shell = shell.replace(placeholder, value)
        if '$' in shell:
            raise ValueError(f'Missing placeholder value:\n' + shell)
        shell = shell.replace('s\'s', 's\'')
        return shell

    def translate_symbol(self, symbol):
        symbol1, symbol2 = symbol.split('/')[0], symbol.split('/')[1]
        t_symbol1, t_symbol2 = self.symbol_translations[symbol1], self.symbol_translations[symbol2]
        return t_symbol1 + '/' + t_symbol2, t_symbol1, t_symbol2
    ################################################################
    # Fill headline news master sheet
    ################################################################
    def write_headline_news(self, sheet='Headlines'):
        table = self.workbook.sheet_to_df(sheet=sheet).to_dict('records')
        i = 0
        while i < len(table):
            row = table[i]
            search_phrase = row['search_phrase']
            if search_phrase == '':
                i += 1
                continue
            news_generator = self.ans.make_news(row['search_phrase'])
            for news_item in news_generator:
                if news_item == '':
                    row['headline'] = ''
                    row['headline_long'] = ''
                    row['headline_narration'] = ''
                    row['provider'] = ''
                    row['date_published'] = ''
                    row['source_link'] = ''
                    break
                row['headline'] = '0'
                row['headline_long'] = news_item['headline_name']
                row['headline_narration'] = news_item['headline_description']
                row['provider'] = news_item['provider']
                row['date_published'] = news_item['date_published']
                row['source_link'] = news_item['url']
                if i < len(table) - 1 and table[i+1]['search_phrase'] == '':
                    i += 1
                    row = table[i]
                else:
                    break
            i += 1
        self.workbook.df_to_sheet(pd.DataFrame(table)[['mark', 'search_phrase', 'headline', 'headline_long', 'headline_narration', 'provider', 'date_published', 'source_link']], sheet=sheet)

    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}-{quote_verbose}'

class EnglishAuthor(ShellManager):

    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/EN.yaml', **kwargs)

    def make_narration(self, event_list):
        shell = "$country_possesive$ $name$ will be released at $time$ GMT, $country_possesive$ $name$ at $time$ GMT, $country_possesive$ $name$ at $time$ GMT."
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]

    def make_title(self, row):
        if row['currencyCode'] == 'EUR' and row['countryCode'] != 'EMU':
            return f'{row["currencyCode"]} {row["countryCode"]} {row["translated_name"]}'
        elif str(row['currencyCode']) != 'nan' and str(row['countryCode']) != 'nan':
            return f'{row["currencyCode"]} {row["translated_name"]}'
        return ''

class JapaneseAuthor(ShellManager):
    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/JP.yaml', **kwargs)
        

    def make_narration(self, event_list):
        shell = "$country_possesive$ $name$は$time$に、$country_possesive$ $name$は$time$に、$country_possesive$ $name$は$time$グリニッジ時間にリリースされます。"
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['translated_name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]

    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            return f'{self.countries_possessive[row["countryCode"]]}{row["translated_name"]}'
        return ''
    
    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}/{quote_verbose}'

class HebrewAuthor(ShellManager):
    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/HE.yaml', **kwargs)
        
    def make_narration(self, event_list):
        shell = "פרטים אודות $country_possesive$ $name$ יפורסמו ב- $time$ GMT, $country_possesive$ $name$ ב- $time$ GMT, $country_possesive$ $name$ ב- $time$ GMT."
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]

    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            return f'{self.countries_possessive[row["countryCode"]]}: {row["translated_name"]}'
        return ''
    
    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}/{quote_verbose}'

class ThaiAuthor(ShellManager):
    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/TH.yaml', **kwargs)
    
    def make_narration(self, event_list):
        shell = "$country_possesive$ $name$ will be released at $time$ GMT, $country_possesive$ $name$ at $time$ GMT, $country_possesive$ $name$ at $time$ GMT."
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]
    
    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            return f'{self.countries_possessive[row["countryCode"]]}: {row["translated_name"]}'
        return ''
    
    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}/{quote_verbose}'

class MalaysianAuthor(ShellManager):
    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/MY.yaml', **kwargs)
    
    def make_narration(self, event_list):
        shell = "$country_possesive$ $name$ will be released at $time$ GMT, $country_possesive$ $name$ at $time$ GMT, $country_possesive$ $name$ at $time$ GMT."
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]
    
    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            return f'{self.countries_possessive[row["countryCode"]]}: {row["translated_name"]}'
        return ''
    
    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}/{quote_verbose}'

class ChineseAuthor(ShellManager):

    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/CN.yaml', **kwargs)
    
    def make_narration(self, event_list):
        shell = "$country_possesive$ $name$ will be released at $time$ GMT, $country_possesive$ $name$ at $time$ GMT, $country_possesive$ $name$ at $time$ GMT."
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]
    
    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            return f'{self.countries_possessive[row["countryCode"]]}: {row["translated_name"]}'
        return ''
    
    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}/{quote_verbose}'

class VietnameseAuthor(ShellManager):

    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/VN.yaml', **kwargs)
        

    def make_narration(self, event_list):
        shell = "$country_possesive$ $name$ sẽ được công bố lúc $time$ GMT, $country_possesive$ $name$ lúc $time$ GMT, $country_possesive$ $name$ lúc $time$ GMT."
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['translated_name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]

    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            return f'{self.countries_possessive[row["countryCode"]]}{row["translated_name"]}'
        return ''
    
    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}/{quote_verbose}'

class HungarianAuthor(ShellManager):

    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/HU.yaml', **kwargs)
        

    def make_narration(self, event_list):
        shell = "$country_possesive$ $name$ $time$ GMT-kor, $country_possesive$ $name$ $time$ GMT-kor, $country_possesive$ $name$ $time$ GMT-kor kerülnek nyilvánosságra."
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['translated_name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]

    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            return f'{self.countries_possessive[row["countryCode"]]} {row["translated_name"]}'
        return ''
    
    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}/{quote_verbose}'

class RussianAuthor(ShellManager):

    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/RU.yaml', **kwargs)
        

    def make_narration(self, event_list):
        shell = "Ожидаются публикации следующих индикаторов: $name$ $country_possesive$ в $time$ GMT, $name$ $country_possesive$ в $time$ GMT, $name$ $country_possesive$ в $time$ GMT."
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['translated_name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]

    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            return f'{row["translated_name"]} {self.countries_possessive[row["countryCode"]]}'
        return ''
    
    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}-{quote_verbose}'

class GermanAuthor(ShellManager):
    
    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/DE.yaml', **kwargs)

    def make_narration(self, event_list):
        shell = "$country_possesive$ $name$ will be released at $time$ GMT, $country_possesive$ $name$ at $time$ GMT, $country_possesive$ $name$ at $time$ GMT."
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]

    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            return f'{row["countryCode"]} {row["translated_name"]}'
        return ''

class RomanianAuthor(ShellManager):
    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/RO.yaml', **kwargs)
        
    def make_narration(self, event_list):
        shell = "$name$ $country_possesive$ se va publica la $time$ GMT, $name$ $country_possesive$ la $time$ GMT, $name$ $country_possesive$ la $time$ GMT."
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['translated_name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]

    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            result = f"{row['translated_name']} {self.countries_possessive[row['countryCode']]}"
            return result[0].upper() + result[1:]
        return ''
    
    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}-{quote_verbose}' 

class ArabicAuthor(ShellManager):
    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/AR.yaml', **kwargs)
        

    def make_narration(self, event_list):
        shell = "سيصدر $country_possesive$ $name$ على الساعة $time$ بتوقيت جرينتش, و $country_possesive$ $name$ على الساعة $ time$ بتوقيت جرينتش, و $country_possesive$ $name$ على الساعة $ time$ بتوقيت جرينتش."
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['translated_name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell

    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            return f'{row["translated_name"]}{self.countries_possessive[row["countryCode"]]}'
        return ''
    
    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}/{quote_verbose}'

class ItalianAuthor(ShellManager):
    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/IT.yaml', **kwargs)
        
    def make_narration(self, event_list):
        shell = " $name$ $country_possesive$ sarà rilasciato alle $time$ GMT, $name$  $country_possesive$ alle $time$ GMT, $name$ $country_possesive$ alle $time$ GMT."
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['translated_name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]

    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            return f'{self.countries_possessive[row["countryCode"]]} {row["translated_name"]}'
        return ''
    
    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}-{quote_verbose}'

class PortugueseAuthor(ShellManager):
    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/PT.yaml', **kwargs)
        

    def make_narration(self, event_list):
        shell = "$country_possesive$ $name$ será divulgado às $time$ GMT, $country_possesive$ $name$ às $time$ GMT, $country_possesive$ $name$ às $time$ GMT."
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['translated_name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]

    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            return f'{row["translated_name"]} {self.countries_possessive[row["countryCode"]]}'
        return ''
    
    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}-{quote_verbose}'

class SpanishAuthor(ShellManager):
    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/SP.yaml', **kwargs)
        

    def make_narration(self, event_list):
        shell = "$country_possesive$ $name$ se publicará a las $time$ GMT, $country_possesive$ $name$ a las $time$ GMT, $country_possesive$ $name$ a las $time$ GMT."
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['translated_name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]

    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            return f'{row["translated_name"]} {self.countries_possessive[row["countryCode"]]}'
        return ''
    
    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}-{quote_verbose}'

class CzechAuthor(ShellManager):
    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/CZ.yaml', **kwargs)
        

    def make_narration(self, event_list):
        shell = "$country_possesive$ $name$ bude vydáno v $time$ GMT, $country_possesive$ $name$ v $time$ GMT, $country_possesive$ $name$ v $time$ GMT."
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['translated_name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]

    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            return f'{self.countries_possessive[row["countryCode"]]} {row["translated_name"]}'
        return ''
    
    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}-{quote_verbose}'

class HindiAuthor(ShellManager):
    def __init__(self, workbook_name, **kwargs):
        super().__init__(workbook_name, './data/shells/HI.yaml', **kwargs)
        

    def make_narration(self, event_list):
        shell = "$country_possesive$ $name$ जारी होगा $time$ GMT पर , $country_possesive$ $name$ $time$ GMT पर , $country_possesive$ $name$  $time$ GMT पर|"
        for event in event_list:
            country_possesive = self.countries_possessive[event['countryCode']]
            previous = str(event['previous']) + (event['unit'] or "")
            time = event['dateUtc'].strftime('%H:%M')
            shell = shell.replace('$country_possesive$', country_possesive, 1)
            shell = shell.replace('$name$', event['translated_name'], 1)
            shell = shell.replace('$previous$', previous, 1)
            shell = shell.replace('$time$', time, 1)
        return shell[0].upper() + shell[1:]

    def make_title(self, row):
        if str(row['countryCode']) != 'nan':
            return f'{row["countryCode"]} {row["translated_name"]}'
        return ''
    
    def make_pair_verbose(self, base_verbose, quote_verbose):
        return f'{base_verbose}-{quote_verbose}'