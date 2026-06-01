from flask import Flask, jsonify, request
import urllib.request
import os

app = Flask(__name__)


@app.route("/")
def home():
    return """
    <html>
    <head>
        <meta charset="UTF-8">
        <title>AI买卖点分析助手</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 760px;
                margin: 60px auto;
                padding: 20px;
                background: #f5f6f8;
            }
            .card {
                background: white;
                padding: 30px;
                border-radius: 18px;
                box-shadow: 0 6px 20px rgba(0,0,0,0.1);
            }
            input {
                padding: 12px;
                font-size: 16px;
                width: 220px;
                border: 1px solid #ccc;
                border-radius: 8px;
            }
            button {
                padding: 12px 20px;
                font-size: 16px;
                border: none;
                border-radius: 8px;
                background: #111827;
                color: white;
                cursor: pointer;
            }
            .box {
                background: #f9fafb;
                padding: 18px;
                border-radius: 12px;
                margin-top: 16px;
            }
            .buy {
                border-left: 5px solid #16a34a;
            }
            .sell {
                border-left: 5px solid #dc2626;
            }
            .hold {
                border-left: 5px solid #f59e0b;
            }
            .small {
                color: #666;
                font-size: 14px;
            }
        </style>
    </head>

    <body>
        <div class="card">
            <h1>AI买卖点分析助手</h1>
            <p>输入A股代码，例如：600519、300750、000001</p>

            <input id="code" placeholder="输入股票代码">
            <button onclick="analyze()">分析买卖点</button>

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

                const res = await fetch("/trade?code=" + code);
                const data = await res.json();

                if (data.error) {
                    resultDiv.innerHTML = "错误：" + data.error;
                    return;
                }

                resultDiv.innerHTML = `
                    <h2>${data.name} ${data.code}</h2>
                    <p><b>当前价格：</b>${data.current}</p>
                    <p><b>今日涨跌：</b>${data.change} (${data.change_pct}%)</p>
                    <p><b>今日最高：</b>${data.high}　<b>今日最低：</b>${data.low}</p>

                    <div class="box buy">
                        <h3>买点判断</h3>
                        <p><b>支撑位：</b>${data.support}</p>
                        <p><b>距离支撑位：</b>${data.distance_to_support}%</p>
                        <p>${data.buy_advice}</p>
                    </div>

                    <div class="box sell">
                        <h3>卖点判断</h3>
                        <p><b>压力位：</b>${data.resistance}</p>
                        <p><b>距离压力位：</b>${data.distance_to_resistance}%</p>
                        <p>${data.sell_advice}</p>
                    </div>

                    <div class="box hold">
                        <h3>操作信号</h3>
                        <h2>${data.signal}</h2>
                        <p><b>趋势评分：</b>${data.score}/10</p>
                        <p><b>风险等级：</b>${data.risk}</p>
                    </div>

                    <div class="box">
                        <h3>AI总结</h3>
                        <p>${data.summary}</p>
                    </div>
                `;
            }
        </script>
    </body>
    </html>
    """


@app.route("/quote")
def quote():
    code = request.args.get("code", "").strip()
    if not code:
        return jsonify({"error": "请提供股票代码，如 ?code=600519"}), 400

    try:
        data = fetch_sina(code)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/trade")
def trade():
    code = request.args.get("code", "").strip()
    if not code:
        return jsonify({"error": "请提供股票代码，如 ?code=600519"}), 400

    try:
        data = fetch_sina(code)

        current = data["current"]
        high = data["high"]
        low = data["low"]
        open_p = data["open"]
        prev_close = data["prev_close"]

        support = low
        resistance = high

        distance_to_support = round((current - support) / current * 100, 2) if current else 0
        distance_to_resistance = round((resistance - current) / current * 100, 2) if current else 0

        score = 5.0
        reasons = []

        if current > open_p:
            score += 1
            reasons.append("当前价格高于开盘价，日内走势偏强")
        else:
            score -= 0.5
            reasons.append("当前价格低于开盘价，日内走势偏弱")

        if data["change_pct"] > 1:
            score += 1
            reasons.append("今日涨幅超过1%，市场情绪偏积极")
        elif data["change_pct"] < -1:
            score -= 1
            reasons.append("今日跌幅超过1%，短期情绪偏谨慎")
        else:
            reasons.append("今日涨跌幅较小，处于震荡区间")

        if distance_to_support <= 1:
            score += 1
            buy_advice = "当前价格接近今日支撑位，可重点观察是否企稳。若成交量配合，可考虑小仓位分批试探。"
        elif distance_to_support <= 3:
            score += 0.5
            buy_advice = "当前价格距离支撑位不远，适合继续等待回踩，不建议追高。"
        else:
            score -= 0.5
            buy_advice = "当前价格距离支撑位较远，追高风险较大，建议等待更好的回调位置。"

        if distance_to_resistance <= 1:
            score -= 0.5
            sell_advice = "当前价格接近今日压力位，短线可考虑分批减仓或止盈观察。"
        elif distance_to_resistance <= 3:
            sell_advice = "当前价格距离压力位较近，继续上攻需要成交量配合。"
        else:
            sell_advice = "当前价格距离压力位较远，短线仍有一定上行空间，但需结合大盘情绪。"

        day_range_pct = round((high - low) / prev_close * 100, 2) if prev_close else 0

        if day_range_pct > 4:
            score -= 1
            risk = "中-高"
            reasons.append("日内波动较大，短线风险上升")
        elif day_range_pct > 2:
            risk = "中"
            reasons.append("日内波动中等")
        else:
            score += 0.5
            risk = "低-中"
            reasons.append("日内波动相对可控")

        score = max(1, min(10, round(score, 1)))

        if score >= 7:
            signal = "观望偏买入"
            summary = f"{data['name']}当前价格接近支撑位且走势相对稳定，短线可关注企稳信号。若后续放量反弹，可考虑分批买入；若跌破支撑位，则应谨慎。"
        elif score >= 5:
            signal = "观望"
            summary = f"{data['name']}目前处于震荡状态，买点和卖点都不算特别明确。建议继续观察支撑位{support}和压力位{resistance}附近的价格表现。"
        else:
            signal = "谨慎观望"
            summary = f"{data['name']}短期走势偏弱或波动较大，目前不适合盲目买入。建议等待价格回到支撑位附近并出现企稳信号后再考虑。"

        return jsonify({
            "code": data["code"],
            "name": data["name"],
            "current": current,
            "change": data["change"],
            "change_pct": data["change_pct"],
            "high": high,
            "low": low,
            "support": support,
            "resistance": resistance,
            "distance_to_support": distance_to_support,
            "distance_to_resistance": distance_to_resistance,
            "buy_advice": buy_advice,
            "sell_advice": sell_advice,
            "signal": signal,
            "score": score,
            "risk": risk,
            "summary": summary,
            "reasons": reasons
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def fetch_sina(code):
    if code.startswith("6"):
        symbol = "sh" + code
    elif code.startswith(("0", "3")):
        symbol = "sz" + code
    elif code.lower().startswith(("sh", "sz")):
        symbol = code.lower()
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
        raise ValueError(f"未找到股票: {code}")

    fields = inner.split(",")

    name = fields[0]
    open_p = float(fields[1])
    prev_close = float(fields[2])
    current = float(fields[3])
    high = float(fields[4])
    low = float(fields[5])
    volume = int(fields[8])
    amount = float(fields[9])
    date = fields[30] if len(fields) > 30 else ""
    time_str = fields[31] if len(fields) > 31 else ""

    change = round(current - prev_close, 2)
    change_pct = round((current - prev_close) / prev_close * 100, 2) if prev_close else 0

    return {
        "code": code,
        "symbol": symbol,
        "name": name,
        "current": current,
        "open": open_p,
        "prev_close": prev_close,
        "high": high,
        "low": low,
        "change": change,
        "change_pct": change_pct,
        "volume": volume,
        "amount": round(amount / 1e8, 4),
        "date": date,
        "time": time_str,
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
