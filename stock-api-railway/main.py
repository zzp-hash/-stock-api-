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
        <title>AI股票买卖点分析助手 V5</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 900px; margin: 50px auto; padding: 20px; background: #f5f6f8; }
            .card { background: white; padding: 30px; border-radius: 18px; box-shadow: 0 6px 20px rgba(0,0,0,0.1); }
            input { padding: 12px; font-size: 16px; width: 220px; border: 1px solid #ccc; border-radius: 8px; }
            button { padding: 12px 20px; font-size: 16px; border: none; border-radius: 8px; background: #111827; color: white; cursor: pointer; }
            .box { background: #f9fafb; padding: 18px; border-radius: 12px; margin-top: 16px; }
            .ma { border-left: 5px solid #7c3aed; }
            .buy { border-left: 5px solid #16a34a; }
            .sell { border-left: 5px solid #dc2626; }
            .signal { border-left: 5px solid #f59e0b; }
            .summary { border-left: 5px solid #2563eb; }
            .small { color: #666; font-size: 14px; margin-top: 25px; }
            .tag { display: inline-block; padding: 6px 10px; background: #eef2ff; border-radius: 999px; margin-right: 8px; margin-top: 6px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>AI股票买卖点分析助手 V5</h1>
            <p>输入A股代码，例如：600519、300750、000001</p>

            <input id="code" placeholder="输入股票代码">
            <button onclick="analyze()">分析</button>

            <div id="result" style="margin-top:30px;"></div>

            <p class="small">提示：本工具仅用于学习和技术分析展示，不构成投资建议。</p>
        </div>

        <script>
            async function analyze() {
                const code = document.getElementById("code").value.trim();
                const resultDiv = document.getElementById("result");

                if (!code) {
                    resultDiv.innerHTML = "请输入股票代码";
                    return;
                }

                resultDiv.innerHTML = "正在分析中...";

                const res = await fetch("/analyze?code=" + code);
                const data = await res.json();

                if (data.error) {
                    resultDiv.innerHTML = "错误：" + data.error;
                    return;
                }

                resultDiv.innerHTML = `
                    <h2>${data.name} ${data.code}</h2>
                    <p><b>当前价格：</b>${data.current}</p>
                    <p><b>今日涨跌：</b>${data.change} (${data.change_pct}%)</p>
                    <p><b>数据来源：</b>${data.source}</p>

                    <div>
                        <span class="tag">趋势：${data.trend_level}</span>
                        <span class="tag">风险：${data.risk}</span>
                        <span class="tag">信号：${data.signal}</span>
                    </div>

                    <div class="box ma">
                        <h3>均线与MACD分析</h3>
                        <p><b>MA20：</b>${data.ma20}</p>
                        <p><b>MA60：</b>${data.ma60}</p>
                        <p><b>DIF：</b>${data.dif}</p>
                        <p><b>DEA：</b>${data.dea}</p>
                        <p><b>MACD：</b>${data.macd}</p>
                        <p>${data.tech_analysis}</p>
                    </div>

                    <div class="box buy">
                        <h3>买点判断</h3>
                        <p><b>支撑位：</b>${data.support}</p>
                        <p><b>理想买入区间：</b>${data.buy_zone}</p>
                        <p><b>止损位：</b>${data.stop_loss}</p>
                        <p>${data.buy_advice}</p>
                    </div>

                    <div class="box sell">
                        <h3>卖点判断</h3>
                        <p><b>压力位：</b>${data.resistance}</p>
                        <p><b>止盈参考位：</b>${data.take_profit}</p>
                        <p>${data.sell_advice}</p>
                    </div>

                    <div class="box signal">
                        <h3>操作信号</h3>
                        <h2>${data.signal}</h2>
                        <p><b>趋势评分：</b>${data.score}/10</p>
                        <p><b>风险等级：</b>${data.risk}</p>
                    </div>

                    <div class="box summary">
                        <h3>AI总结</h3>
                        <p>${data.summary}</p>
                    </div>
                `;
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
        hist = fetch_eastmoney_hist(code)

        if len(hist) < 60:
            return jsonify({"error": "历史K线数据不足，无法计算MA60"}), 400

        quote = None
        try:
            quote = fetch_sina(code)
        except Exception:
            quote = None

        latest = hist[-1]
        prev = hist[-2]

        if quote and quote.get("current", 0) > 0:
            name = quote["name"]
            current = quote["current"]
            change = quote["change"]
            change_pct = quote["change_pct"]
            source = "新浪实时行情"
        else:
            name = code
            current = latest["close"]
            change = round(current - prev["close"], 2)
            change_pct = round((current - prev["close"]) / prev["close"] * 100, 2)
            source = "东方财富K线兜底"

        closes = [x["close"] for x in hist]
        highs = [x["high"] for x in hist[-20:]]
        lows = [x["low"] for x in hist[-20:]]

        ma20 = round(sum(closes[-20:]) / 20, 2)
        ma60 = round(sum(closes[-60:]) / 60, 2)

        dif, dea, macd = calc_macd(closes)

        support = round(min(lows), 2)
        resistance = round(max(highs), 2)
        stop_loss = round(support * 0.97, 2)
        take_profit = round(resistance * 0.995, 2)
        buy_zone = f"{support} - {round(support * 1.015, 2)}"

        score = 5.0
        tech_notes = []

        if current > ma20:
            score += 1
            tech_notes.append("✓ 当前价格高于MA20，短期趋势偏强")
        else:
            score -= 1
            tech_notes.append("✗ 当前价格低于MA20，短期趋势偏弱")

        if current > ma60:
            score += 1
            tech_notes.append("✓ 当前价格高于MA60，中期趋势偏强")
        else:
            score -= 1
            tech_notes.append("✗ 当前价格低于MA60，中期趋势偏弱")

        if ma20 > ma60:
            score += 1
            tech_notes.append("✓ MA20高于MA60，均线结构偏多")
        else:
            score -= 1
            tech_notes.append("✗ MA20低于MA60，均线结构偏弱")

        if dif > dea and macd > 0:
            score += 1
            tech_notes.append("✓ MACD处于偏强状态，动能较好")
        elif dif < dea and macd < 0:
            score -= 1
            tech_notes.append("✗ MACD偏弱，短期需防回调")
        else:
            tech_notes.append("— MACD方向不强，仍需观察")

        distance_support = (current - support) / current * 100
        distance_resistance = (resistance - current) / current * 100

        if distance_support <= 2:
            score += 0.7
            buy_advice = "当前价格接近20日支撑区间，若企稳或放量反弹，可作为观察买点。"
        else:
            buy_advice = "当前价格距离支撑位较远，不建议追高，适合等待回踩。"

        if distance_resistance <= 2:
            score -= 0.5
            sell_advice = "当前价格接近压力位，若无法突破，可考虑减仓或止盈。"
        else:
            sell_advice = "距离压力位仍有空间，可继续观察上攻力度。"

        score = max(1, min(10, round(score, 1)))

        if score >= 7:
            signal = "观望偏买入"
            trend_level = "偏强"
            risk = "低-中"
        elif score >= 5:
            signal = "观望"
            trend_level = "震荡"
            risk = "中"
        else:
            signal = "谨慎观望"
            trend_level = "偏弱"
            risk = "中-高"

        tech_analysis = "；".join(tech_notes) + "。"

        summary = (
            f"{name}当前趋势为{trend_level}，趋势评分为{score}/10。"
            f"当前价格为{current}，MA20为{ma20}，MA60为{ma60}。"
            f"{tech_analysis}"
            f"支撑位约为{support}，压力位约为{resistance}。"
            f"{buy_advice}{sell_advice}"
        )

        return jsonify({
            "code": code,
            "name": name,
            "current": current,
            "change": change,
            "change_pct": change_pct,
            "source": source,
            "ma20": ma20,
            "ma60": ma60,
            "dif": round(dif, 3),
            "dea": round(dea, 3),
            "macd": round(macd, 3),
            "support": support,
            "resistance": resistance,
            "buy_zone": buy_zone,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "score": score,
            "signal": signal,
            "trend_level": trend_level,
            "risk": risk,
            "tech_analysis": tech_analysis,
            "buy_advice": buy_advice,
            "sell_advice": sell_advice,
            "summary": summary
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
    if code.startswith("6"):
        symbol = "sh" + code
    elif code.startswith(("0", "3")):
        symbol = "sz" + code
    else:
        symbol = "sh" + code

    url = f"http://hq.sinajs.cn/list={symbol}"
    req = urllib.request.Request(url, headers={
        "Referer": "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0"
    })

    with urllib.request.urlopen(req, timeout=5) as resp:
        raw = resp.read().decode("gbk")

    inner = raw.split('"')[1]
    if not inner:
        raise ValueError("未找到股票")

    fields = inner.split(",")

    name = fields[0]
    prev_close = float(fields[2])
    current = float(fields[3])

    if current <= 0:
        raise ValueError("实时价格无效")

    change = round(current - prev_close, 2)
    change_pct = round((current - prev_close) / prev_close * 100, 2) if prev_close else 0

    return {
        "code": code,
        "symbol": symbol,
        "name": name,
        "current": current,
        "prev_close": prev_close,
        "change": change,
        "change_pct": change_pct
    }


def fetch_eastmoney_hist(code):
    secid = "1." + code if code.startswith("6") else "0." + code

    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "beg": "20240101",
        "end": "20500101",
        "rtntype": "6",
        "secid": secid,
        "klt": "101",
        "fqt": "1"
    }

    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://quote.eastmoney.com/",
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive"
    })

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    klines = data.get("data", {}).get("klines", [])

    if not klines:
        raise ValueError("未获取到历史K线数据")

    result = []
    for item in klines:
        parts = item.split(",")
        result.append({
            "date": parts[0],
            "open": float(parts[1]),
            "close": float(parts[2]),
            "high": float(parts[3]),
            "low": float(parts[4])
        })

    return result


def ema(values, period):
    k = 2 / (period + 1)
    ema_values = [values[0]]

    for price in values[1:]:
        ema_values.append(price * k + ema_values[-1] * (1 - k))

    return ema_values


def calc_macd(closes):
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    dif_list = [a - b for a, b in zip(ema12, ema26)]
    dea_list = ema(dif_list, 9)

    dif = dif_list[-1]
    dea = dea_list[-1]
    macd = (dif - dea) * 2

    return dif, dea, macd


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
