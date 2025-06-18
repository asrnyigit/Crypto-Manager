import time, json, hashlib, hmac
import requests as req
import ast

NAME = 'mexc'

def query_price(pair):
    url = f'https://api.mexc.com/api/v3/ticker/price?symbol={pair.upper()}USDT'

    response = req.get(url)
    return response

def query_price_all():
    url = 'https://api.mexc.com/api/v3/ticker/price'

    response = req.get(url)
    return response

def get_tickers():
    url = 'https://api.mexc.com/api/v3/ticker/24hr'

    response = req.get(url)
    return response