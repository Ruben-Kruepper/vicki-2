from gspread_pandas import Client, Spread
import os
import json

CREDIT_FILE = os.path.join(os.path.dirname(__file__), '../data/credits/vicki_credits.json')

class Operator: 
    def __init__(self, workbook_name):
        with open(CREDIT_FILE, 'r') as f:
            credits = json.load(f)
        self.gspread_client = Client(config=credits)
        self.workbook       = Spread(workbook_name, client=self.gspread_client)
