import time, json, hashlib, hmac
import requests as req

def create_headers(params, api_secret, api_key):
    query_string = '&'.join([f"{key}={params[key]}" for key in params])
    signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    params['signature'] = signature

    headers = {'X-MBX-APIKEY': api_key}

    return params, headers

def set_order(symbol, side, _type, price, quantity, api_secret, api_key):
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


    params, headers = create_headers(params, api_secret, api_key)
    response = req.post('https://api.binance.com/api/v3/order', params=params, headers=headers)

    return response


def cancel_order(symbol, order_id, api_secret, api_key):
    params = {
        'symbol': symbol,
        'orderId': order_id,
        'timestamp': int(time.time() * 1000)
    }

    params, headers = create_headers(params, api_secret, api_key)
    response = req.delete('https://api.binance.com/api/v3/order', params=params, headers=headers)

    return response

def query_price(pair):
    response = req.get('https://api.binance.com/api/v3/ticker/price?symbol=' + pair.upper() + "USDT")

    return response

def query_balances(api_secret, api_key):
    params = {
        'timestamp': int(time.time() * 1000)
    }

    params, headers = create_headers(params, api_secret, api_key)
    response = req.get('https://api.binance.com/api/v3/account', params=params, headers=headers)

    return response

def query_orders(api_secret, api_key):
    params = {
        'timestamp': int(time.time() * 1000),
        'recvWindow': 5000
    }

    params, headers = create_headers(params, api_secret, api_key)
    response = req.get('https://api.binance.com/api/v3/openOrders', params=params, headers=headers)

    return response
