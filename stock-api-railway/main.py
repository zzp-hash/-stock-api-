from flask import Flask, jsonify, request
import urllib.request

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({'status': 'ok', 'usage': '/quote?code=600519'})

@app.route('/quote')
def quote():
    code = request.args.get('code', '').strip()
    if not code:
        return jsonify({'error': '请提供股票代码，如 ?code=600519'}), 400
    try:
        data = fetch_sina(code)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def fetch_sina(code):
    if code.startswith('6'):
        symbol = 'sh' + code
    elif code.startswith(('0', '3')):
        symbol = 'sz' + code
    elif code.lower().startswith(('sh', 'sz')):
        symbol = code.lower()
    else:
        symbol = 'sh' + code

    url = f'http://hq.sinajs.cn/list={symbol}'
    req = urllib.request.Request(url, headers={
        'Referer': 'https://finance.sina.com.cn',
        'User-Agent': 'Mozilla/5.0'
    })
    with urllib.request.urlopen(req, timeout=5) as resp:
        raw = resp.read().decode('gbk')

    inner = raw.split('"')[1]
    if not inner:
        raise ValueError(f'未找到股票: {code}')

    fields = inner.split(',')
    name       = fields[0]
    prev_close = float(fields[2])
    open_p     = float(fields[1])
    current    = float(fields[3])
    high       = float(fields[4])
    low        = float(fields[5])
    volume     = int(fields[8])
    amount     = float(fields[9])
    date       = fields[30] if len(fields) > 30 else ''
    time_str   = fields[31] if len(fields) > 31 else ''
    change     = round(current - prev_close, 2)
    change_pct = round((current - prev_close) / prev_close * 100, 2) if prev_close else 0

    return {
        'code': code, 'symbol': symbol, 'name': name,
        'current': current, 'open': open_p, 'prev_close': prev_close,
        'high': high, 'low': low, 'change': change, 'change_pct': change_pct,
        'volume': volume, 'amount': round(amount / 1e8, 4),
        'date': date, 'time': time_str,
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
