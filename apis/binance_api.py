import time, json, hashlib, hmac, aiohttp
import requests as req

NAME = "binance"

def create_headers(params, api_params):
    api_secret, api_key = api_params['api_secret'], api_params['api_key']

    query_string = '&'.join([f"{key}={params[key]}" for key in params])
    signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    params['signature'] = signature

    headers = {'X-MBX-APIKEY': api_key}

    return params, headers

def set_order(symbol, side, _type, price, quantity, api_params):
    params = {
        'symbol': symbol,
        'side': side,
        'type': _type,
        'timeInForce': 'GTC',
        'quantity': float(quantity),
        'price': float(price),
        'recvWindow': 5000,
        'timestamp': int(time.time() * 1000)
    }

    if _type == "MARKET":
        params.pop("timeInForce")
        params.pop("recvWindow")
        params.pop("price")

    url = 'https://api.binance.com/api/v3/order'
    params, headers = create_headers(params, api_params)

    response = req.post(url, params=params, headers=headers)
    return response

def cancel_order(symbol, order_id, api_params):
    params = {
        'symbol': symbol,
        'orderId': order_id,
        'timestamp': int(time.time() * 1000)
    }

    url = 'https://api.binance.com/api/v3/order'
    params, headers = create_headers(params, api_params)

    response = req.delete(url, params=params, headers=headers)
    return response

def query_price(pair):
    url = f'https://api.binance.com/api/v3/ticker/price?symbol={pair.upper()}USDT'

    response = req.get(url)
    return response

def query_price_all():
    url = 'https://api.binance.com/api/v3/ticker/price'

    response = req.get(url)
    return response

def get_tickers():
    url = 'https://api.binance.com/api/v3/ticker/24hr'

    response = req.get(url)
    return response

def query_balances(api_params):
    params = {
        'timestamp': int(time.time() * 1000)
    }

    url = 'https://api.binance.com/api/v3/account'
    params, headers = create_headers(params, api_params)

    response = req.get(url, params=params, headers=headers)
    return response

def query_orders(api_params):
    params = {
        'timestamp': int(time.time() * 1000),
        'recvWindow': 5000
    }

    url = 'https://api.binance.com/api/v3/openOrders'
    params, headers = create_headers(params, api_params)

    response = req.get(url, params=params, headers=headers)
    return response