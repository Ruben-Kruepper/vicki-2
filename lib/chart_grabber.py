from selenium                       import webdriver
from selenium.webdriver.support     import expected_conditions as EC
from selenium.webdriver.support.ui  import WebDriverWait
from selenium.webdriver.common.by   import By
from selenium.webdriver.common.keys import Keys

import datetime

from PIL import Image

from os.path import dirname, abspath, join
import os
import io
import time

ROOT = dirname(dirname(abspath(__file__)))

def chart_name(symbol):
    return ''.join(ch for ch in symbol if ch.isalnum()) + '.png'

class ChartGrabber:

    def __init__(self, url, username, password, save_path=ROOT):
        self.save_path = save_path + '/' + (datetime.datetime.today() + datetime.timedelta(days=1)).strftime('%d%m%y')
        os.makedirs(self.save_path, exist_ok=True)

        self.driver = webdriver.Edge(executable_path=join(ROOT, 'data', 'drivers', 'msedgedriver.exe'))
        self.driver.set_window_size(1920, 1080)

        self.driver.get('https://www.tradingview.com/#signin')
        self.driver.find_element_by_xpath('//span[text()="Email"]').click()
        time.sleep(1)
        username_input = self.driver.find_element_by_name('username')
        username_input.send_keys(username)
        password_input = self.driver.find_element_by_name('password')
        password_input.send_keys(password)
        password_input.send_keys(Keys.ENTER)
        time.sleep(3)
        self.driver.get(url)
        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, 'chart-markup-table')))
        try:
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, '//span[text()="Accept"]'))).find_element_by_xpath('./..').click()
        except:
            pass

    def make_chart(self, symbol, name=''):
        if not name:
            name = chart_name(symbol)
        if name in os.listdir(self.save_path):
            return
        symbol = symbol.lower().replace('/', '')
        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, 'chart-markup-table')))
        body = self.driver.find_element_by_xpath('//body')
        body.send_keys(symbol[0])
        input_field = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'search-Hsmn_0WX')))
        input_field.send_keys(symbol[1:])
        input_field.send_keys(Keys.ENTER)
        time.sleep(1)
        repeat_delete = True
        while repeat_delete:
            try:
                element = self.driver.find_element_by_css_selector("div[class*='toast']")
                self.driver.execute_script("""
                var element = arguments[0];
                element.parentNode.removeChild(element);
                """, element)
            except Exception as e:
                repeat_delete = False
        self.save_chart_png(name)

    def save_chart_png(self, name):
        chart = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, 'chart-markup-table')))
        image = Image.open(io.BytesIO(chart.screenshot_as_png))
        width, height = image.size
        
        image = image.crop((width-1730, height-730, width, height))

        with open(join(self.save_path, name), 'wb+') as f:
            image.save(f)
