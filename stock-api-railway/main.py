from flask import Flask, jsonify, request
import urllib.request
import urllib.parse
import json
import os
import ssl
import math

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <html>
    <head>
        <meta charset="UTF-8">
        <title>AI股票买卖点分析助手 V10</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1050px; margin: 50px auto; padding: 20px; background: #f5f6f8; }
            .card { background: white; padding: 30px; border-radius: 18px; box-shadow: 0 6px 20px rgba(0,0,0,0.1); }
            input { padding: 12px; font-size: 16px; width: 220px; border: 1px solid #ccc; border-radius: 8px; }
            button { padding: 12px 20px; font-size: 16px; border: none; border-radius: 8px; background: #111827; color: white; cursor: pointer; }
            .box { background: #f9fafb; padding: 18px; border-radius: 12px; margin-top: 16px; }
            .rating  { border-left: 5px solid #f97316; }
            .ma      { border-left: 5px solid #7c3aed; }
            .extra   { border-left: 5px solid #0ea5e9; }
            .money   { border-left: 5px solid #10b981; }
            .buy     { border-left: 5px solid #16a34a; }
            .sell    { border-left: 5px solid #dc2626; }
            .signal  { border-left: 5px solid #f59e0b; }
            .summary { border-left: 5px solid #2563eb; }
            .chart   { border-left: 5px solid #111827; }
            .small { color: #666; font-size: 14px; margin-top: 25px; }
            .tag { display: inline-block; padding: 6px 10px; background: #eef2ff; border-radius: 999px; margin-right: 8px; margin-top: 6px; }
            .bull { color: #16a34a; font-weight: bold; }
            .bear { color: #dc2626; font-weight: bold; }
            .neutral { color: #f59e0b; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>AI股票买卖点分析助手 V10</h1>
            <p>输入A股代码，例如：600519、300750、000001</p>
            <input id="code" placeholder="输入股票代码" onkeydown="if(event.key==='Enter')analyze()">
            <button onclick="analyze()">分析</button>
            <div id="result" style="margin-top:30px;"></div>
            <p class="small">⚠️ 本工具仅用于学习和技术分析展示，资金行为分析为基于公开K线和成交量的概率模型，不构成投资建议。</p>
        </div>
        <script>
            let priceChart = null;
            async function analyze() {
                const code = document.getElementById("code").value.trim();
                const resultDiv = document.getElementById("result");
                if (!code) { resultDiv.innerHTML = "请输入股票代码"; return; }
                resultDiv.innerHTML = "<p>正在获取数据并分析，请稍候...</p>";
                try {
                    const res = await fetch("/analyze?code=" + code);
                    const data = await res.json();
                    if (data.error) { resultDiv.innerHTML = "错误：" + data.error; return; }

                    const mfiColor = data.mfi > 80 ? "bear" : data.mfi < 20 ? "bull" : "neutral";
                    const obvColor = data.obv_trend === "上升" ? "bull" : data.obv_trend === "下降" ? "bear" : "neutral";
                    const vwapColor = data.current > data.vwap ? "bull" : "bear";
                    const mainColor = data.main_force_action === "吸筹" ? "bull" : data.main_force_action === "出货" ? "bear" : "neutral";

                    resultDiv.innerHTML = `
                        <h2>${data.name} (${data.code})</h2>
                        <p><b>当前价格：</b>¥${data.current}　<b>今日涨跌：</b>${data.change} (${data.change_pct}%)</p>
                        <p><b>数据来源：</b>${data.source}</p>
                        <div>
                            <span class="tag">趋势：${data.trend_level}</span>
                            <span class="tag">风险：${data.risk}</span>
                            <span class="tag">信号：${data.signal}</span>
                        </div>

                        <div class="box rating">
                            <h3>综合评级</h3>
                            <h2>${data.star_rating}</h2>
                            <p><b>综合得分：</b>${data.score100}/100</p>
                            <p><b>技术面：</b>${data.tech_score}/100　<b>趋势面：</b>${data.trend_score}/100　<b>风险面：</b>${data.risk_score}/100</p>
                        </div>

                        <div class="box chart">
                            <h3>K线趋势图（收盘价 + MA20 / MA60 / MA89）</h3>
                            <canvas id="priceChart" height="120"></canvas>
                        </div>

                        <div class="box money">
                            <h3>💰 主力/散户资金行为分析（概率模型）</h3>
                            <p><b>主力行为判断：</b><span class="${mainColor}">${data.main_force_action}</span>　<b>置信度：</b>${data.main_force_confidence}</p>
                            <p><b>量价结构：</b>${data.vol_price_structure}</p>
                            <p><b>MFI（资金流向）：</b><span class="${mfiColor}">${data.mfi}</span>　${data.mfi_text}</p>
                            <p><b>OBV趋势：</b><span class="${obvColor}">${data.obv_trend}</span>　${data.obv_text}</p>
                            <p><b>VWAP：</b>¥${data.vwap}　<span class="${vwapColor}">当前价${data.current > data.vwap ? "高于" : "低于"}VWAP</span>　${data.vwap_text}</p>
                            <p><b>大单/小单行为：</b>${data.order_behavior}</p>
                            <p><b>综合资金判断：</b>${data.money_summary}</p>
                        </div>

                        <div class="box ma">
                            <h3>均线、MACD 与 KDJ 分析</h3>
                            <p><b>MA20：</b>${data.ma20}　<b>MA60：</b>${data.ma60}　<b>MA89：</b>${data.ma89}</p>
                            <p><b>DIF：</b>${data.dif}　<b>DEA：</b>${data.dea}　<b>MACD：</b>${data.macd}</p>
                            <p><b>K：</b>${data.k}　<b>D：</b>${data.d}　<b>J：</b>${data.j}　<b>KDJ信号：</b>${data.kdj_signal}</p>
                            <p>${data.tech_analysis}</p>
                            <p>${data.kdj_analysis}</p>
                        </div>

                        <div class="box extra">
                            <h3>RSI、布林带、ATR与成交量</h3>
                            <p><b>RSI(14)：</b>${data.rsi}　${data.rsi_analysis}</p>
                            <p><b>布林上轨：</b>${data.bb_upper}　<b>中轨：</b>${data.bb_middle}　<b>下轨：</b>${data.bb_lower}</p>
                            <p>${data.bollinger_text}</p>
                            <p><b>ATR：</b>${data.atr}　<b>波动率：</b>${data.volatility}　<b>均线交叉：</b>${data.cross_signal}</p>
                            <p><b>成交量：</b>${data.volume_signal} — ${data.volume_analysis}</p>
                        </div>

                        <div class="box buy">
                            <h3>📗 买点判断</h3>
                            <p><b>支撑位：</b>¥${data.support}　<b>买入区间：</b>¥${data.buy_zone}　<b>止损位：</b>¥${data.stop_loss}</p>
                            <p><b>盈亏比：</b>${data.risk_reward_ratio} : 1</p>
                            <p>${data.buy_advice}</p>
                        </div>

                        <div class="box sell">
                            <h3>📕 卖点判断</h3>
                            <p><b>压力位：</b>¥${data.resistance}　<b>止盈参考：</b>¥${data.take_profit}</p>
                            <p>${data.sell_advice}</p>
                        </div>

                        <div class="box signal">
                            <h3>操作信号</h3>
                            <h2>${data.signal}</h2>
                            <p><b>趋势评分：</b>${data.score}/10　<b>风险等级：</b>${data.risk}</p>
                            <p><b>${data.position_advice}</b></p>
                        </div>

                        <div class="box summary">
                            <h3>综合总结</h3>
                            <p>${data.summary}</p>
                        </div>`;

                    drawChart(data.chart);
                } catch(e) {
                    resultDiv.innerHTML = "请求失败，请刷新后重试：" + e.message;
                }
            }

            function drawChart(chartData) {
                const ctx = document.getElementById("priceChart");
                if (priceChart) priceChart.destroy();
                priceChart = new Chart(ctx, {
                    type: "line",
                    data: {
                        labels: chartData.dates,
                        datasets: [
                            { label:"收盘价", data:chartData.close, borderColor:"#111827", borderWidth:2, pointRadius:0, fill:false },
                            { label:"MA20",  data:chartData.ma20,  borderColor:"#f97316", borderWidth:1.5, pointRadius:0, borderDash:[4,2], fill:false },
                            { label:"MA60",  data:chartData.ma60,  borderColor:"#7c3aed", borderWidth:1.5, pointRadius:0, borderDash:[4,2], fill:false },
                            { label:"MA89",  data:chartData.ma89,  borderColor:"#0ea5e9", borderWidth:1.5, pointRadius:0, borderDash:[4,2], fill:false },
                            { label:"VWAP",  data:chartData.vwap,  borderColor:"#10b981", borderWidth:1.5, pointRadius:0, borderDash:[2,4], fill:false }
                        ]
                    },
                    options: {
                        responsive:true,
                        plugins:{ legend:{ display:true } },
                        scales:{
                            x:{ ticks:{ maxTicksLimit:8 } },
                            y:{ beginAtZero:false }
                        }
                    }
                });
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
        if len(hist) < 89:
            return jsonify({"error": f"历史数据不足（仅{len(hist)}条），无法计算MA89"}), 400

        quote = None
        try:
            quote = fetch_sina(code)
        except Exception:
            pass

        latest = hist[-1]; prev = hist[-2]
        if quote and quote.get("current", 0) > 0:
            name=quote["name"]; current=quote["current"]
            change=quote["change"]; change_pct=quote["change_pct"]
            source="新浪财经实时行情"
        else:
            name=code; current=latest["close"]
            change=round(current-prev["close"],2)
            change_pct=round((current-prev["close"])/prev["close"]*100,2)
            source="历史K线收盘价"

        closes  = [x["close"]         for x in hist]
        highs   = [x["high"]          for x in hist]
        lows    = [x["low"]           for x in hist]
        volumes = [x.get("volume",0)  for x in hist]

        ma20 = round(sum(closes[-20:])/20,2)
        ma60 = round(sum(closes[-60:])/60,2)
        ma89 = round(sum(closes[-89:])/89,2)

        dif,dea,macd_val               = calc_macd(closes)
        rsi                             = calc_rsi(closes)
        k,d,j                           = calc_kdj(hist)
        volume_signal,volume_analysis   = calc_volume_signal(volumes)
        bb_upper,bb_middle,bb_lower     = calc_bollinger(closes)
        atr                             = calc_atr(hist)
        cross_signal                    = check_cross(ma20,ma60)

        # ── 资金行为指标 ──
        mfi,mfi_text                    = calc_mfi(hist)
        obv_trend,obv_text              = calc_obv(hist)
        vwap                            = calc_vwap(hist)
        vwap_text = ("价格高于VWAP，短期买方力量较强。" if current > vwap
                     else "价格低于VWAP，短期卖方力量较强，谨慎追多。")
        vol_price_structure             = calc_vol_price_structure(hist)
        main_force_action,main_force_confidence,order_behavior = calc_main_force(hist,closes,volumes)
        money_summary                   = make_money_summary(main_force_action,mfi,obv_trend,current,vwap,vol_price_structure)

        support    = round(min(lows[-20:]),2)
        resistance = round(max(highs[-20:]),2)
        stop_loss  = round(support*0.97,2)
        take_profit= round(resistance*0.995,2)
        buy_zone   = f"{support} - {round(support*1.015,2)}"

        if current>=bb_upper:
            bollinger_text="当前价格接近或突破布林上轨，短线偏热，注意回调风险。"
        elif current<=bb_lower:
            bollinger_text="当前价格接近或跌破布林下轨，可能存在超跌反弹机会。"
        else:
            bollinger_text="当前价格位于布林带中部，暂未出现极端波动信号。"

        volatility=("低波动" if atr<current*0.02 else ("中波动" if atr<current*0.05 else "高波动"))

        score=5.0; tech_notes=[]

        if current>ma20:  score+=1;   tech_notes.append("✓ 价格高于MA20，短期偏强")
        else:             score-=1;   tech_notes.append("✗ 价格低于MA20，短期偏弱")
        if current>ma60:  score+=1;   tech_notes.append("✓ 价格高于MA60，中期偏强")
        else:             score-=1;   tech_notes.append("✗ 价格低于MA60，中期偏弱")
        if current>ma89:  score+=0.7; tech_notes.append("✓ 价格高于MA89，长期趋势有支撑")
        else:             score-=0.7; tech_notes.append("✗ 价格低于MA89，长期趋势偏弱")
        if ma20>ma60:     score+=1;   tech_notes.append("✓ MA20高于MA60，均线多头排列")
        else:             score-=1;   tech_notes.append("✗ MA20低于MA60，均线空头排列")
        if dif>dea and macd_val>0:  score+=1;  tech_notes.append("✓ MACD金叉偏强，动能较好")
        elif dif<dea and macd_val<0:score-=1;  tech_notes.append("✗ MACD死叉偏弱，注意回调")
        else:                                   tech_notes.append("— MACD方向不明，继续观察")

        if rsi>=70:   score-=0.7; rsi_analysis="RSI超买，短线不宜追高"
        elif rsi<=30: score+=0.7; rsi_analysis="RSI超卖，可能存在反弹机会"
        else:         rsi_analysis="RSI中性区间，无明显超买超卖"

        if k>d and j<80:  score+=0.5; kdj_analysis="KDJ偏多，短线动能有所改善。"
        elif k<d and j>20:score-=0.5; kdj_analysis="KDJ偏弱，短线仍需谨慎。"
        elif j>=90:       score-=0.5; kdj_analysis="J值过高，短线存在超买回落风险。"
        elif j<=10:       score+=0.5; kdj_analysis="J值过低，短线存在超卖反弹可能。"
        else:             kdj_analysis="KDJ处于中性状态，暂无极端信号。"

        if k>d and j>k:   kdj_signal="KDJ短线偏强"
        elif k<d and j<k: kdj_signal="KDJ短线偏弱"
        elif j>=90:       kdj_signal="KDJ超买警惕回调"
        elif j<=10:       kdj_signal="KDJ超卖关注反弹"
        else:             kdj_signal="KDJ中性观察"

        # 资金行为加分
        if main_force_action=="吸筹":    score+=0.8
        elif main_force_action=="出货":  score-=0.8
        if mfi<=20:  score+=0.5
        elif mfi>=80:score-=0.5
        if obv_trend=="上升": score+=0.3
        elif obv_trend=="下降":score-=0.3
        if current>vwap: score+=0.2
        else:            score-=0.2

        if volume_signal=="放量":  score+=0.3
        elif volume_signal=="缩量":score-=0.2

        dist_sup=(current-support)/current*100
        dist_res=(resistance-current)/current*100
        if dist_sup<=2: score+=0.7; buy_advice="价格接近支撑位，若放量企稳可考虑分批买入。"
        else:           buy_advice="价格距支撑位较远，建议等待回踩支撑再介入。"
        if dist_res<=2: score-=0.5; sell_advice="价格接近压力位，若无法突破建议减仓或止盈。"
        else:           sell_advice=f"距压力位约{round(dist_res,1)}%空间，可观察突破力度。"

        risk_reward_ratio=round(max(take_profit-current,0.01)/max(current-stop_loss,0.01),2)
        score=max(1,min(10,round(score,1))); score100=int(round(score*10))

        if score>=8:   position_advice="建议仓位：60%-70%"
        elif score>=7: position_advice="建议仓位：40%-50%"
        elif score>=5: position_advice="建议仓位：20%-30%"
        else:          position_advice="建议仓位：0%-10%，以观察为主"

        if score>=7:   signal="📈 偏向买入"; trend_level="偏强"; risk="低-中"
        elif score>=5: signal="➡ 观望为主";  trend_level="震荡"; risk="中"
        else:          signal="📉 谨慎观望"; trend_level="偏弱"; risk="中-高"

        star_rating=make_star_rating(score100)
        tech_score,trend_score,risk_score=make_sub_scores(current,ma20,ma60,ma89,dif,dea,macd_val,rsi)
        tech_analysis="；".join(tech_notes)+"。"
        chart=make_chart_data(hist,vwap)

        summary=(
            f"{name}当前趋势{trend_level}，综合评分{score100}/100。"
            f"当前价¥{current}，MA20={ma20}，MA60={ma60}，MA89={ma89}。"
            f"{tech_analysis}"
            f"RSI={rsi}，{rsi_analysis}。"
            f"KDJ：K={k}，D={d}，J={j}，{kdj_analysis}"
            f"布林带：上{bb_upper} 中{bb_middle} 下{bb_lower}，{bollinger_text}"
            f"ATR={atr}，{volatility}。成交量{volume_signal}，{volume_analysis}"
            f"资金：{money_summary}"
            f"支撑¥{support}，压力¥{resistance}，盈亏比{risk_reward_ratio}:1。"
            f"{buy_advice}{sell_advice}"
        )

        return jsonify({
            "code":code,"name":name,"current":current,
            "change":change,"change_pct":change_pct,"source":source,
            "ma20":ma20,"ma60":ma60,"ma89":ma89,
            "dif":round(dif,3),"dea":round(dea,3),"macd":round(macd_val,3),
            "rsi":rsi,"rsi_analysis":rsi_analysis,
            "k":k,"d":d,"j":j,"kdj_analysis":kdj_analysis,"kdj_signal":kdj_signal,
            "volume_signal":volume_signal,"volume_analysis":volume_analysis,
            "bb_upper":bb_upper,"bb_middle":bb_middle,"bb_lower":bb_lower,
            "bollinger_text":bollinger_text,"atr":atr,"volatility":volatility,
            "cross_signal":cross_signal,
            "mfi":mfi,"mfi_text":mfi_text,
            "obv_trend":obv_trend,"obv_text":obv_text,
            "vwap":vwap,"vwap_text":vwap_text,
            "vol_price_structure":vol_price_structure,
            "main_force_action":main_force_action,
            "main_force_confidence":main_force_confidence,
            "order_behavior":order_behavior,
            "money_summary":money_summary,
            "support":support,"resistance":resistance,
            "buy_zone":buy_zone,"stop_loss":stop_loss,"take_profit":take_profit,
            "risk_reward_ratio":risk_reward_ratio,
            "score":score,"score100":score100,"star_rating":star_rating,
            "tech_score":tech_score,"trend_score":trend_score,"risk_score":risk_score,
            "signal":signal,"trend_level":trend_level,"risk":risk,
            "position_advice":position_advice,
            "tech_analysis":tech_analysis,"buy_advice":buy_advice,
            "sell_advice":sell_advice,"summary":summary,"chart":chart
        })
    except Exception as e:
        return jsonify({"error":str(e)}),500

@app.route("/quote")
def quote():
    code=request.args.get("code","").strip()
    if not code: return jsonify({"error":"请提供股票代码"}),400
    try: return jsonify(fetch_sina(code))
    except Exception as e: return jsonify({"error":str(e)}),500

# ── 数据获取（三重保障）────────────────────────────────────

def _ssl_ctx():
    ctx=ssl.create_default_context()
    ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    return ctx

def fetch_sina(code):
    symbol=("sh" if code.startswith("6") else "sz")+code
    url=f"http://hq.sinajs.cn/list={symbol}"
    req=urllib.request.Request(url,headers={"Referer":"https://finance.sina.com.cn","User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req,timeout=8) as resp: raw=resp.read().decode("gbk")
    inner=raw.split('"')[1]
    if not inner: raise ValueError("未找到股票")
    f=inner.split(","); name=f[0]; prev_close=float(f[2]); current=float(f[3])
    if current<=0: raise ValueError("实时价格无效")
    change=round(current-prev_close,2)
    change_pct=round((current-prev_close)/prev_close*100,2) if prev_close else 0
    return {"code":code,"symbol":symbol,"name":name,"current":current,
            "prev_close":prev_close,"change":change,"change_pct":change_pct}

def fetch_hist(code):
    errors=[]
    for fn in [fetch_yahoo_hist,fetch_sina_hist,fetch_eastmoney_hist]:
        try:
            r=fn(code)
            if len(r)>=89: return r
        except Exception as e: errors.append(f"{fn.__name__}:{e}")
    raise ValueError("所有数据源均失败 — "+" | ".join(errors))

def fetch_yahoo_hist(code):
    suffix=".SS" if code.startswith("6") else ".SZ"
    url=f"https://query1.finance.yahoo.com/v8/finance/chart/{code}{suffix}?interval=1d&range=1y"
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=15,context=_ssl_ctx()) as resp:
        data=json.loads(resp.read().decode("utf-8"))
    chart=data["chart"]["result"][0]; ohlcv=chart["indicators"]["quote"][0]
    result=[]
    for i,ts in enumerate(chart["timestamp"]):
        o,c,h,l,v=ohlcv["open"][i],ohlcv["close"][i],ohlcv["high"][i],ohlcv["low"][i],ohlcv["volume"][i]
        if None in (o,c,h,l): continue
        result.append({"date":str(ts),"open":round(o,2),"close":round(c,2),
                       "high":round(h,2),"low":round(l,2),"volume":v or 0})
    if not result: raise ValueError("Yahoo数据为空")
    return result

def fetch_sina_hist(code):
    symbol=("sh" if code.startswith("6") else "sz")+code
    url=(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php"
         f"/CN_MarketData.getKLineData?symbol={symbol}&scale=240&datalen=160&ma=no")
    req=urllib.request.Request(url,headers={"Referer":"https://finance.sina.com.cn","User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req,timeout=10) as resp: raw=resp.read().decode("gbk")
    data=json.loads(raw)
    if not data: raise ValueError("新浪历史数据为空")
    return [{"date":x["d"],"open":float(x["o"]),"close":float(x["c"]),
             "high":float(x["h"]),"low":float(x["l"]),"volume":float(x.get("v",0))} for x in data]

def fetch_eastmoney_hist(code):
    secid=("1." if code.startswith("6") else "0.")+code
    params={"fields1":"f1,f2,f3,f4,f5,f6","fields2":"f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "beg":"20230101","end":"20500101","rtntype":"6","secid":secid,"klt":"101","fqt":"1"}
    url="https://push2his.eastmoney.com/api/qt/stock/kline/get?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                                             "Referer":"https://quote.eastmoney.com/","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=15,context=_ssl_ctx()) as resp:
        data=json.loads(resp.read().decode("utf-8"))
    klines=data.get("data",{}).get("klines",[])
    if not klines: raise ValueError("东方财富数据为空")
    return [{"date":p[0],"open":float(p[1]),"close":float(p[2]),
             "high":float(p[3]),"low":float(p[4]),"volume":float(p[5])}
            for p in (item.split(",") for item in klines)]

# ── 技术指标 ──────────────────────────────────────────────

def ema(values,period):
    k=2/(period+1); e=[values[0]]
    for v in values[1:]: e.append(v*k+e[-1]*(1-k))
    return e

def calc_macd(closes):
    e12=ema(closes,12); e26=ema(closes,26)
    dif=[a-b for a,b in zip(e12,e26)]; dea=ema(dif,9)
    return dif[-1],dea[-1],(dif[-1]-dea[-1])*2

def calc_rsi(closes,period=14):
    if len(closes)<period+1: return 50
    gains,losses=[],[]
    for i in range(-period,0):
        d=closes[i]-closes[i-1]; gains.append(max(d,0)); losses.append(max(-d,0))
    ag,al=sum(gains)/period,sum(losses)/period
    return 100 if al==0 else round(100-100/(1+ag/al),2)

def calc_kdj(hist,period=9):
    if len(hist)<period: return 50,50,50
    k=d=50
    for i in range(period-1,len(hist)):
        w=hist[i-period+1:i+1]
        lo=min(x["low"] for x in w); hi=max(x["high"] for x in w)
        c=hist[i]["close"]
        rsv=50 if hi==lo else (c-lo)/(hi-lo)*100
        k=2/3*k+1/3*rsv; d=2/3*d+1/3*k
    return round(k,2),round(d,2),round(3*k-2*d,2)

def calc_bollinger(closes,period=20):
    ma=sum(closes[-period:])/period
    std=(sum((x-ma)**2 for x in closes[-period:])/period)**0.5
    return round(ma+2*std,2),round(ma,2),round(ma-2*std,2)

def calc_atr(hist,period=14):
    trs=[]
    for i in range(1,len(hist)):
        h=hist[i]["high"]; l=hist[i]["low"]; pc=hist[i-1]["close"]
        trs.append(max(h-l,abs(h-pc),abs(l-pc)))
    return round(sum(trs[-period:])/period,2)

def calc_volume_signal(volumes):
    if len(volumes)<20: return "未知","成交量数据不足。"
    r5=sum(volumes[-5:])/5; r20=sum(volumes[-20:])/20
    if r20==0: return "未知","无法判断成交量。"
    ratio=r5/r20
    if ratio>=1.3: return "放量","近5日成交量明显高于均量，资金关注度提升。"
    if ratio<=0.7: return "缩量","近5日成交量低于均量，市场参与度偏弱。"
    return "正常","成交量处于正常区间，市场活跃度一般。"

def check_cross(ma20,ma60):
    if ma20>ma60: return "黄金交叉区域（多头）"
    if ma20<ma60: return "死亡交叉区域（空头）"
    return "均线重合"

# ── 资金行为指标 ──────────────────────────────────────────

def calc_mfi(hist, period=14):
    """Money Flow Index — 用典型价格×成交量计算"""
    if len(hist) < period+1:
        return 50, "MFI数据不足。"
    pos_flow = neg_flow = 0
    for i in range(-period, 0):
        tp  = (hist[i]["high"]+hist[i]["low"]+hist[i]["close"])/3
        ptp = (hist[i-1]["high"]+hist[i-1]["low"]+hist[i-1]["close"])/3
        mf  = tp * hist[i].get("volume",0)
        if tp >= ptp: pos_flow += mf
        else:         neg_flow += mf
    if neg_flow == 0:
        mfi = 100
    else:
        mfi = round(100 - 100/(1 + pos_flow/neg_flow), 1)
    if mfi >= 80:   text = "MFI处于超买区，资金流入过热，注意回调。"
    elif mfi <= 20: text = "MFI处于超卖区，资金流出明显，关注企稳反弹。"
    elif mfi >= 60: text = "MFI偏强，资金净流入。"
    elif mfi <= 40: text = "MFI偏弱，资金净流出。"
    else:           text = "MFI中性，资金流向平衡。"
    return mfi, text

def calc_obv(hist):
    """On-Balance Volume — 累积成交量趋势"""
    if len(hist) < 10:
        return "未知", "OBV数据不足。"
    obv = 0; obvs = []
    for i in range(1, len(hist)):
        if hist[i]["close"] > hist[i-1]["close"]:   obv += hist[i].get("volume",0)
        elif hist[i]["close"] < hist[i-1]["close"]: obv -= hist[i].get("volume",0)
        obvs.append(obv)
    if len(obvs) < 10:
        return "未知", "OBV数据不足。"
    recent5  = sum(obvs[-5:])/5
    recent20 = sum(obvs[-20:])/20 if len(obvs)>=20 else sum(obvs)/len(obvs)
    if recent5 > recent20 * 1.05:
        return "上升", "OBV持续上升，成交量支撑价格上涨，多头有效。"
    elif recent5 < recent20 * 0.95:
        return "下降", "OBV持续下降，量价背离，需警惕下跌风险。"
    else:
        return "横盘", "OBV趋势平稳，资金方向不明确。"

def calc_vwap(hist, period=20):
    """Volume Weighted Average Price — 近N日成交量加权均价"""
    recent = hist[-period:]
    total_vp = sum((x["high"]+x["low"]+x["close"])/3 * x.get("volume",1) for x in recent)
    total_v  = sum(x.get("volume",1) for x in recent)
    if total_v == 0: return round((hist[-1]["high"]+hist[-1]["low"]+hist[-1]["close"])/3, 2)
    return round(total_vp/total_v, 2)

def calc_vol_price_structure(hist, period=10):
    """量价结构判断：涨时放量/跌时缩量 = 健康；涨时缩量/跌时放量 = 背离"""
    if len(hist) < period+1:
        return "数据不足"
    up_vol=up_cnt=dn_vol=dn_cnt=0
    for i in range(-period,0):
        chg = hist[i]["close"]-hist[i-1]["close"]
        vol = hist[i].get("volume",0)
        if chg>0: up_vol+=vol; up_cnt+=1
        elif chg<0: dn_vol+=vol; dn_cnt+=1
    avg_up = up_vol/up_cnt   if up_cnt   else 0
    avg_dn = dn_vol/dn_cnt   if dn_cnt   else 0
    if avg_up > avg_dn*1.2:
        return "涨时放量跌时缩量，量价结构健康，上涨动能较强。"
    elif avg_dn > avg_up*1.2:
        return "涨时缩量跌时放量，量价背离，需警惕主力出货。"
    else:
        return "量价结构中性，暂无明显放量或缩量特征。"

def calc_main_force(hist, closes, volumes, period=20):
    """
    主力行为概率模型（基于公开K线）：
    - 阴线放量 + 价格不跌 → 吸筹概率高
    - 阳线缩量上涨后突然放量下跌 → 出货概率高
    - 大阳线+大成交量 + 次日跳空高开低走 → 出货
    - 价格在低位震荡 + 成交量逐步萎缩 → 洗盘/吸筹
    """
    if len(hist) < period+1:
        return "无法判断","低","数据不足"

    avg_vol = sum(volumes[-period:])/period
    recent  = hist[-10:]
    score   = 0

    # 低位震荡缩量 → 吸筹信号
    price_range = max(x["close"] for x in recent) - min(x["close"] for x in recent)
    avg_price   = sum(x["close"] for x in recent)/len(recent)
    volatility  = price_range/avg_price if avg_price else 0
    if volatility < 0.05:
        score += 1  # 低位震荡

    # 阴线但成交量缩减 → 洗盘
    down_days_low_vol = sum(1 for i in range(-5,0)
                            if hist[i]["close"]<hist[i-1]["close"]
                            and hist[i].get("volume",0)<avg_vol*0.8)
    score += down_days_low_vol * 0.5

    # 近期是否出现大阳线后快速下跌
    for i in range(-5,-1):
        body = hist[i]["close"]-hist[i]["open"]
        if body>0 and body>(hist[i]["high"]-hist[i]["low"])*0.7:
            if hist[i+1]["close"] < hist[i]["open"]:
                score -= 2  # 出货信号

    # 价格是否在相对低位（近60日）
    closes60 = closes[-60:]
    pct_rank = sum(1 for c in closes60 if c < closes[-1])/len(closes60)
    if pct_rank < 0.3:  score += 1.5  # 低位
    elif pct_rank > 0.7:score -= 1.5  # 高位

    # 近期成交量是否温和放大
    recent_vol = sum(volumes[-5:])/5
    if avg_vol > 0 and 1.1 < recent_vol/avg_vol < 1.8:
        score += 0.5

    if score >= 2:
        action="吸筹"; conf="中等"
        order="量能温和放大，大单流入迹象，散户观望为主。"
    elif score <= -1:
        action="出货"; conf="中等"
        order="放量滞涨或高位大阳线后快速回落，警惕主力减仓。"
    else:
        action="震荡"; conf="低"
        order="成交量无明显异动，主力方向不明，建议观望。"

    return action, conf, order

def make_money_summary(action, mfi, obv_trend, current, vwap, vol_price):
    parts = []
    if action=="吸筹":   parts.append("主力行为偏向吸筹")
    elif action=="出货": parts.append("主力行为偏向出货，需谨慎")
    else:                parts.append("主力方向不明，观望为宜")
    if mfi>=60:          parts.append("资金净流入")
    elif mfi<=40:        parts.append("资金净流出")
    if obv_trend=="上升":parts.append("OBV上升支撑多头")
    elif obv_trend=="下降":parts.append("OBV下降量价背离")
    if current>vwap:     parts.append("价格在VWAP上方偏强")
    else:                parts.append("价格在VWAP下方偏弱")
    return "；".join(parts)+"。"

# ── 评级与图表 ────────────────────────────────────────────

def make_star_rating(s):
    if s>=85: return "★★★★★"
    if s>=70: return "★★★★☆"
    if s>=55: return "★★★☆☆"
    if s>=40: return "★★☆☆☆"
    return "★☆☆☆☆"

def make_sub_scores(current,ma20,ma60,ma89,dif,dea,macd_val,rsi):
    tech=50; trend=50; risk=70
    if current>ma20: trend+=12
    else: trend-=12
    if current>ma60: trend+=12
    else: trend-=12
    if current>ma89: trend+=10
    else: trend-=10
    if ma20>ma60: trend+=8
    else: trend-=8
    if dif>dea and macd_val>0: tech+=20
    elif dif<dea and macd_val<0: tech-=20
    if 40<=rsi<=60: risk+=10
    elif rsi>=75 or rsi<=25: risk-=20
    elif rsi>=70 or rsi<=30: risk-=10
    return max(1,min(100,int(tech))),max(1,min(100,int(trend))),max(1,min(100,int(risk)))

def rolling_ma(values,period):
    result=[]
    for i in range(len(values)):
        if i+1<period: result.append(None)
        else: result.append(round(sum(values[i+1-period:i+1])/period,2))
    return result

def make_chart_data(hist, vwap_val):
    recent=hist[-120:]
    closes=[x["close"] for x in recent]
    dates=[x["date"][-5:] if "-" in str(x["date"]) else str(x["date"]) for x in recent]
    return {"dates":dates,"close":closes,
            "ma20":rolling_ma(closes,20),
            "ma60":rolling_ma(closes,60),
            "ma89":rolling_ma(closes,89),
            "vwap":[vwap_val]*len(closes)}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
