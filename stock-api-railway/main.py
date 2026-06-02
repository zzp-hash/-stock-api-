from flask import Flask, jsonify, request
import urllib.request
import urllib.parse
import json
import os
import ssl

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <html>
    <head>
        <meta charset="UTF-8">
        <title>AI股票买卖点分析助手 V6</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 950px; margin: 50px auto; padding: 20px; background: #f5f6f8; }
            .card { background: white; padding: 30px; border-radius: 18px; box-shadow: 0 6px 20px rgba(0,0,0,0.1); }
            input { padding: 12px; font-size: 16px; width: 220px; border: 1px solid #ccc; border-radius: 8px; }
            button { padding: 12px 20px; font-size: 16px; border: none; border-radius: 8px; background: #111827; color: white; cursor: pointer; }
            .box { background: #f9fafb; padding: 18px; border-radius: 12px; margin-top: 16px; }
            .ma { border-left: 5px solid #7c3aed; }
            .buy { border-left: 5px solid #16a34a; }
            .sell { border-left: 5px solid #dc2626; }
            .signal { border-left: 5px solid #f59e0b; }
            .summary { border-left: 5px solid #2563eb; }
            .extra { border-left: 5px solid #0ea5e9; }
            .small { color: #666; font-size: 14px; margin-top: 25px; }
            .tag { display: inline-block; padding: 6px 10px; background: #eef2ff; border-radius: 999px; margin-right: 8px; margin-top: 6px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>AI股票买卖点分析助手 V6</h1>
            <p>输入A股代码，例如：600519、300750、000001</p>
            <input id="code" placeholder="输入股票代码" onkeydown="if(event.key==='Enter')analyze()">
            <button onclick="analyze()">分析</button>
            <div id="result" style="margin-top:30px;"></div>
            <p class="small">提示：本工具仅用于学习和技术分析展示，不构成投资建议。</p>
        </div>
        <script>
            async function analyze() {
                const code = document.getElementById("code").value.trim();
                const resultDiv = document.getElementById("result");
                if (!code) { resultDiv.innerHTML = "请输入股票代码"; return; }
                resultDiv.innerHTML = "<p>正在获取数据并分析，请稍候...</p>";
                try {
                    const res = await fetch("/analyze?code=" + code);
                    const data = await res.json();
                    if (data.error) { resultDiv.innerHTML = "错误：" + data.error; return; }
                    resultDiv.innerHTML = `
                        <h2>${data.name} (${data.code})</h2>
                        <p><b>当前价格：</b>¥${data.current}</p>
                        <p><b>今日涨跌：</b>${data.change} (${data.change_pct}%)</p>
                        <p><b>数据来源：</b>${data.source}</p>
                        <div>
                            <span class="tag">趋势：${data.trend_level}</span>
                            <span class="tag">风险：${data.risk}</span>
                            <span class="tag">信号：${data.signal}</span>
                        </div>
                        <div class="box ma">
                            <h3>均线与MACD分析</h3>
                            <p><b>MA20：</b>${data.ma20} &nbsp; <b>MA60：</b>${data.ma60}</p>
                            <p><b>DIF：</b>${data.dif} &nbsp; <b>DEA：</b>${data.dea} &nbsp; <b>MACD：</b>${data.macd}</p>
                            <p>${data.tech_analysis}</p>
                        </div>
                        <div class="box extra">
                            <h3>RSI与成交量分析</h3>
                            <p><b>RSI(14)：</b>${data.rsi} &nbsp; ${data.rsi_analysis}</p>
                            <p><b>成交量：</b>${data.volume_signal} — ${data.volume_analysis}</p>
                        </div>
                        <div class="box buy">
                            <h3>📗 买点判断</h3>
                            <p><b>支撑位：</b>¥${data.support} &nbsp; <b>买入区间：</b>¥${data.buy_zone} &nbsp; <b>止损位：</b>¥${data.stop_loss}</p>
                            <p>${data.buy_advice}</p>
                        </div>
                        <div class="box sell">
                            <h3>📕 卖点判断</h3>
                            <p><b>压力位：</b>¥${data.resistance} &nbsp; <b>止盈参考：</b>¥${data.take_profit}</p>
                            <p>${data.sell_advice}</p>
                        </div>
                        <div class="box signal">
                            <h3>操作信号</h3>
                            <h2>${data.signal}</h2>
                            <p><b>趋势评分：</b>${data.score}/10 &nbsp; <b>风险等级：</b>${data.risk}</p>
                        </div>
                        <div class="box summary">
                            <h3>综合总结</h3>
                            <p>${data.summary}</p>
                        </div>`;
                } catch(e) {
                    resultDiv.innerHTML = "请求失败，请刷新后重试：" + e.message;
                }
            }
        </script>
    </body>
    </html>
    """

@app.route("/analyze")
def analyze():
    code = request.args.get("code", "").strip()
    if not code:
        return jsonify({"error": "请提供股票代码"}), 400
    try:
        hist = fetch_hist(code)
        if len(hist) < 60:
            return jsonify({"error": f"历史数据不足（仅{len(hist)}条），无法计算MA60"}), 400

        quote = None
        try:
            quote = fetch_sina(code)
        except Exception:
            pass

        latest = hist[-1]
        prev   = hist[-2]
        if quote and quote.get("current", 0) > 0:
            name       = quote["name"]
            current    = quote["current"]
            change     = quote["change"]
            change_pct = quote["change_pct"]
            source     = "新浪财经实时行情"
        else:
            name       = code
            current    = latest["close"]
            change     = round(current - prev["close"], 2)
            change_pct = round((current - prev["close"]) / prev["close"] * 100, 2)
            source     = "历史K线收盘价"

        closes  = [x["close"]            for x in hist]
        highs   = [x["high"]             for x in hist[-20:]]
        lows    = [x["low"]              for x in hist[-20:]]
        volumes = [x.get("volume", 0)    for x in hist]

        ma20     = round(sum(closes[-20:]) / 20, 2)
        ma60     = round(sum(closes[-60:]) / 60, 2)
        dif, dea, macd_val = calc_macd(closes)
        rsi      = calc_rsi(closes)
        volume_signal, volume_analysis = calc_volume_signal(volumes)

        support    = round(min(lows), 2)
        resistance = round(max(highs), 2)
        stop_loss  = round(support * 0.97, 2)
        take_profit = round(resistance * 0.995, 2)
        buy_zone   = f"{support} - {round(support * 1.015, 2)}"

        score = 5.0
        tech_notes = []

        if current > ma20:
            score += 1;   tech_notes.append("✓ 价格高于MA20，短期偏强")
        else:
            score -= 1;   tech_notes.append("✗ 价格低于MA20，短期偏弱")

        if current > ma60:
            score += 1;   tech_notes.append("✓ 价格高于MA60，中期偏强")
        else:
            score -= 1;   tech_notes.append("✗ 价格低于MA60，中期偏弱")

        if ma20 > ma60:
            score += 1;   tech_notes.append("✓ MA20高于MA60，均线多头排列")
        else:
            score -= 1;   tech_notes.append("✗ MA20低于MA60，均线空头排列")

        if dif > dea and macd_val > 0:
            score += 1;   tech_notes.append("✓ MACD金叉偏强，动能较好")
        elif dif < dea and macd_val < 0:
            score -= 1;   tech_notes.append("✗ MACD死叉偏弱，注意回调")
        else:
            tech_notes.append("— MACD方向不明，继续观察")

        if rsi >= 70:
            score -= 0.7; rsi_analysis = "RSI超买，短线不宜追高"
        elif rsi <= 30:
            score += 0.7; rsi_analysis = "RSI超卖，可能存在反弹机会"
        else:
            rsi_analysis = "RSI中性区间，无明显超买超卖"

        if volume_signal == "放量":
            score += 0.3
        elif volume_signal == "缩量":
            score -= 0.2

        dist_sup = (current - support) / current * 100
        dist_res = (resistance - current) / current * 100

        if dist_sup <= 2:
            score += 0.7
            buy_advice = "价格接近支撑位，若放量企稳可考虑分批买入。"
        else:
            buy_advice = "价格距支撑位较远，建议等待回踩支撑再介入。"

        if dist_res <= 2:
            score -= 0.5
            sell_advice = "价格接近压力位，若无法突破建议减仓或止盈。"
        else:
            sell_advice = f"距压力位约{round(dist_res,1)}%空间，可观察突破力度。"

        score = max(1, min(10, round(score, 1)))

        if score >= 7:
            signal = "📈 偏向买入"; trend_level = "偏强"; risk = "低-中"
        elif score >= 5:
            signal = "➡ 观望为主"; trend_level = "震荡"; risk = "中"
        else:
            signal = "📉 谨慎观望"; trend_level = "偏弱"; risk = "中-高"

        tech_analysis = "；".join(tech_notes) + "。"
        summary = (
            f"{name}当前趋势{trend_level}，评分{score}/10。"
            f"当前价¥{current}，MA20={ma20}，MA60={ma60}。"
            f"{tech_analysis}"
            f"RSI={rsi}，{rsi_analysis}。"
            f"成交量{volume_signal}，{volume_analysis}"
            f"支撑位¥{support}，压力位¥{resistance}。"
            f"{buy_advice}{sell_advice}"
        )

        return jsonify({
            "code": code, "name": name, "current": current,
            "change": change, "change_pct": change_pct, "source": source,
            "ma20": ma20, "ma60": ma60,
            "dif": round(dif, 3), "dea": round(dea, 3), "macd": round(macd_val, 3),
            "rsi": rsi, "rsi_analysis": rsi_analysis,
            "volume_signal": volume_signal, "volume_analysis": volume_analysis,
            "support": support, "resistance": resistance,
            "buy_zone": buy_zone, "stop_loss": stop_loss, "take_profit": take_profit,
            "score": score, "signal": signal, "trend_level": trend_level, "risk": risk,
            "tech_analysis": tech_analysis, "buy_advice": buy_advice,
            "sell_advice": sell_advice, "summary": summary
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/quote")
def quote():
    code = request.args.get("code", "").strip()
    if not code:
        return jsonify({"error": "请提供股票代码"}), 400
    try:
        return jsonify(fetch_sina(code))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def fetch_sina(code):
    symbol = ("sh" if code.startswith("6") else "sz") + code
    url = f"http://hq.sinajs.cn/list={symbol}"
    req = urllib.request.Request(url, headers={
        "Referer": "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0"
    })
    with urllib.request.urlopen(req, timeout=8) as resp:
        raw = resp.read().decode("gbk")
    inner = raw.split('"')[1]
    if not inner:
        raise ValueError("未找到股票")
    f = inner.split(",")
    name = f[0]
    prev_close = float(f[2])
    current    = float(f[3])
    if current <= 0:
        raise ValueError("实时价格无效")
    change     = round(current - prev_close, 2)
    change_pct = round((current - prev_close) / prev_close * 100, 2) if prev_close else 0
    return {"code": code, "symbol": symbol, "name": name,
            "current": current, "prev_close": prev_close,
            "change": change, "change_pct": change_pct}

def fetch_hist(code):
    """依次尝试三个数据源"""
    errors = []
    for fn in [fetch_yahoo_hist, fetch_sina_hist, fetch_eastmoney_hist]:
        try:
            result = fn(code)
            if len(result) >= 60:
                return result
        except Exception as e:
            errors.append(str(e))
    raise ValueError("所有数据源均失败：" + " | ".join(errors))

def fetch_yahoo_hist(code):
    """Yahoo Finance — 对境外服务器最友好"""
    suffix = ".SS" if code.startswith("6") else ".SZ"
    symbol = code + suffix
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=6mo"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    })
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    chart = data["chart"]["result"][0]
    timestamps = chart["timestamp"]
    ohlcv = chart["indicators"]["quote"][0]
    result = []
    for i, ts in enumerate(timestamps):
        o = ohlcv["open"][i]
        c = ohlcv["close"][i]
        h = ohlcv["high"][i]
        l = ohlcv["low"][i]
        v = ohlcv["volume"][i]
        if None in (o, c, h, l):
            continue
        result.append({"date": str(ts), "open": round(o,2), "close": round(c,2),
                        "high": round(h,2), "low": round(l,2), "volume": v or 0})
    if not result:
        raise ValueError("Yahoo数据为空")
    return result

def fetch_sina_hist(code):
    symbol = ("sh" if code.startswith("6") else "sz") + code
    url = (f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php"
           f"/CN_MarketData.getKLineData?symbol={symbol}&scale=240&datalen=100&ma=no")
    req = urllib.request.Request(url, headers={
        "Referer": "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0"
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read().decode("gbk")
    data = json.loads(raw)
    if not data:
        raise ValueError("新浪历史数据为空")
    return [{"date": x["d"], "open": float(x["o"]), "close": float(x["c"]),
             "high": float(x["h"]), "low": float(x["l"]),
             "volume": float(x.get("v", 0))} for x in data]

def fetch_eastmoney_hist(code):
    secid = ("1." if code.startswith("6") else "0.") + code
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "beg": "20230101", "end": "20500101",
        "rtntype": "6", "secid": secid, "klt": "101", "fqt": "1"
    }
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://quote.eastmoney.com/",
        "Accept": "application/json"
    })
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    klines = data.get("data", {}).get("klines", [])
    if not klines:
        raise ValueError("东方财富数据为空")
    result = []
    for item in klines:
        p = item.split(",")
        result.append({"date": p[0], "open": float(p[1]), "close": float(p[2]),
                        "high": float(p[3]), "low": float(p[4]), "volume": float(p[5])})
    return result

def ema(values, period):
    k = 2 / (period + 1)
    e = [values[0]]
    for v in values[1:]:
        e.append(v * k + e[-1] * (1 - k))
    return e

def calc_macd(closes):
    e12 = ema(closes, 12)
    e26 = ema(closes, 26)
    dif_list = [a - b for a, b in zip(e12, e26)]
    dea_list = ema(dif_list, 9)
    return dif_list[-1], dea_list[-1], (dif_list[-1] - dea_list[-1]) * 2

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(-period, 0):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0)); losses.append(max(-d, 0))
    ag = sum(gains) / period
    al = sum(losses) / period
    if al == 0:
        return 100
    return round(100 - 100 / (1 + ag / al), 2)

def calc_volume_signal(volumes):
    if len(volumes) < 20:
        return "未知", "成交量数据不足。"
    r5  = sum(volumes[-5:])  / 5
    r20 = sum(volumes[-20:]) / 20
    if r20 == 0:
        return "未知", "无法判断成交量。"
    ratio = r5 / r20
    if ratio >= 1.3:
        return "放量", "近5日成交量明显高于均量，资金关注度提升。"
    elif ratio <= 0.7:
        return "缩量", "近5日成交量低于均量，市场参与度偏弱。"
    else:
        return "正常", "成交量处于正常区间，市场活跃度一般。"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
