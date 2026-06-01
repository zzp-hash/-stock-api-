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
        <title>AI股票分析助手</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 700px;
                margin: 60px auto;
                padding: 20px;
                background: #f7f7f7;
            }
            .card {
                background: white;
                padding: 30px;
                border-radius: 16px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }
            input {
                padding: 10px;
                font-size: 16px;
                width: 200px;
            }
            button {
                padding: 10px 18px;
                font-size: 16px;
                cursor: pointer;
            }
            .note {
                color: #666;
                font-size: 14px;
                margin-top: 20px;
            }
        </style>
    </head>

    <body>
        <div class="card">
            <h1>AI股票分析助手</h1>
            <p>输入A股代码，例如：600519、300750、000001</p>

            <input id="code" placeholder="输入股票代码">
            <button onclick="analyze()">分析</button>

            <div id="result" style="margin-top:30px;"></div>

            <p class="note">提示：本页面仅用于学习和技术分析展示，不构成投资建议。</p>
        </div>

        <script>
            async function analyze() {
                const code = document.getElementById("code").value;
                const resultDiv = document.getElementById("result");

                if (!code) {
                    resultDiv.innerHTML = "请输入股票代码";
                    return;
                }

                resultDiv.innerHTML = "正在分析中...";

                const res = await fetch("/analysis?code=" + code);
                const data = await res.json();

                if (data.error) {
                    resultDiv.innerHTML = "错误：" + data.error;
                    return;
                }

                resultDiv.innerHTML = `
                    <h2>${data.name} ${data.code}</h2>
                    <p><b>当前价格：</b>${data.current}</p>
                    <p><b>涨跌：</b>${data.change} (${data.change_pct}%)</p>
                    <p><b>成交额：</b>${data.amount} 亿元</p>

                    <h3>技术分析</h3>
                    <ul>
                        ${data.signals.map(s => `<li>${s}</li>`).join("")}
                    </ul>

                    <h3>趋势评分：${data.score}/10</h3>
                    <h3>风险等级：${data.risk}</h3>

                    <h3>AI总结</h3>
                    <p>${data.summary}</p>
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


@app.route("/analysis")
def analysis():
    code = request.args.get("code", "").strip()
    if not code:
        return jsonify({"error": "请提供股票代码，如 ?code=600519"}), 400

    try:
        data = fetch_sina(code)

        score = 5.0
        signals = []

        if data["current"] > data["open"]:
            score += 1
            signals.append("✓ 当前价格高于开盘价，日内走势偏强")
        else:
            score -= 0.5
            signals.append("✗ 当前价格低于开盘价，日内走势偏弱")

        if data["change_pct"] > 0:
            score += 1
            signals.append("✓ 今日上涨，市场情绪偏积极")
        elif data["change_pct"] < 0:
            score -= 0.5
            signals.append("✗ 今日下跌，短期情绪偏谨慎")
        else:
            signals.append("— 今日基本持平，方向暂不明确")

        if data["amount"] > 10:
            score += 0.5
            signals.append("✓ 成交额较活跃，市场关注度较高")
        else:
            signals.append("— 成交额一般，市场关注度中等")

        day_range = data["high"] - data["low"]
        if day_range / data["prev_close"] > 0.03:
            score -= 0.5
            signals.append("✗ 日内波动较大，短期风险增加")
        else:
            signals.append("✓ 日内波动相对可控")

        score = max(1, min(10, round(score, 1)))

        if score >= 7:
            risk = "低-中"
            summary = "该股票今日表现相对较强，市场情绪偏积极，可继续观察趋势延续情况。"
        elif score >= 5:
            risk = "中"
            summary = "该股票目前处于震荡状态，短期方向并不明确，适合继续观察关键支撑位和成交量变化。"
        else:
            risk = "中-高"
            summary = "该股票短期表现偏弱，波动风险较高，建议谨慎观察，不宜盲目追高或重仓操作。"

        return jsonify({
            "code": data["code"],
            "name": data["name"],
            "current": data["current"],
            "change": data["change"],
            "change_pct": data["change_pct"],
            "amount": data["amount"],
            "score": score,
            "risk": risk,
            "signals": signals,
            "summary": summary
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
