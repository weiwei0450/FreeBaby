#!/usr/bin/env python3
"""
coinglass_ob_monitor.py
CoinGlass ETH-USDT 合并挂单订单簿监控
浏览器JS注入方案，3秒刷新周期
"""
import time
import json
import sys
import os
import subprocess
import statistics
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# === CONFIG ===
TAB_ID = '1550444965'
POLL_SEC = 3
HISTORY_LEN = 200
WALL_THRESHOLD_ETH = 5000
RATIO_ALERT_HIGH = 1.5
RATIO_ALERT_LOW = 0.67

# === INJECT JS ===
INJECT_JS = r"""
(function(){
    var prices = document.querySelectorAll('.obv2-item-price');
    var amounts = document.querySelectorAll('.obv2-item-amount');
    var totals = document.querySelectorAll('.obv2-item-total');
    var ob = [];
    var len = Math.min(prices.length, amounts.length, totals.length);
    for (var i = 0; i < len; i++) {
        var p = parseFloat(prices[i].innerText);
        var a = parseFloat(amounts[i].innerText);
        var t = parseFloat(totals[i].innerText);
        if (!isNaN(p)) ob.push({p:p, a:a, t:t});
    }
    var allDivs = document.querySelectorAll('div');
    var bigOrders = [];
    allDivs.forEach(function(el) {
        var t = el.innerText.trim();
        if (t.indexOf('\ud83d\udd25') >= 0 && t.length < 300 && t.length > 2) {
            bigOrders.push(t.substring(0, 120));
        }
    });
    var statsText = document.body.innerText;
    var volM = statsText.match(/成交额\$([0-9,]+)/);
    var oiM = statsText.match(/持仓\$([0-9,]+)/);
    var liqM = statsText.match(/爆仓\$([0-9,]+)/);
    var lsM = statsText.match(/多空比([\d.]+)%\/([\d.]+)%/);
    return JSON.stringify({
        ts: Date.now(),
        ob: ob,
        bigOrders: bigOrders.slice(0, 10),
        stats: {
            vol: volM ? volM[1] : null,
            oi: oiM ? oiM[1] : null,
            liq: liqM ? liqM[1] : null,
            ls: lsM ? [lsM[1], lsM[2]] : null
        }
    });
})()
"""

def fetch_data():
    """Inject JS into browser tab and parse order book data."""
    try:
        result = subprocess.run(
            ['python', '-c', f'''
import sys, json
sys.path.insert(0, r"..")
from extensions.TMWebDriver import TMWebDriver
tm = TMWebDriver()
data = tm.execute_js({TAB_ID!r}, {INJECT_JS!r})
print(data)
'''],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.join(os.path.dirname(__file__), '..')
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception as e:
        print("[%s] fetch error: %s" % (time.strftime('%H:%M:%S'), e))
    return None

def analyze(data, history):
    """Analyze order book data, return metrics and alerts."""
    if not data or not data.get('ob'):
        return None, []

    ob = data['ob']
    alerts = []
    metrics = {}

    # Split into asks (above mid) and bids (below mid)
    # Find approximate midpoint
    prices = [x['p'] for x in ob]
    mid = statistics.median(prices) if prices else 0

    asks = [x for x in ob if x['p'] > mid]
    bids = [x for x in ob if x['p'] <= mid]

    total_ask = sum(x['a'] for x in asks)
    total_bid = sum(x['a'] for x in bids)
    ratio = total_ask / total_bid if total_bid > 0 else 0

    metrics['total_ask'] = total_ask
    metrics['total_bid'] = total_bid
    metrics['ratio'] = round(ratio, 3)

    # Find walls (single price level > threshold)
    walls = [x for x in ob if x['a'] >= WALL_THRESHOLD_ETH]
    metrics['walls'] = walls

    # Near-price imbalance (first 3 levels each side)
    near_asks = sorted(asks, key=lambda x: x['p'])[:3]
    near_bids = sorted(bids, key=lambda x: -x['p'])[:3]
    near_ask_total = sum(x['a'] for x in near_asks)
    near_bid_total = sum(x['a'] for x in near_bids)
    near_ratio = near_ask_total / near_bid_total if near_bid_total > 0 else 0
    metrics['near_ratio'] = round(near_ratio, 3)

    # Price from data
    if ob:
        prices_only = sorted([x['p'] for x in ob])
        metrics['spread_low'] = prices_only[0] if prices_only else 0
        metrics['spread_high'] = prices_only[-1] if prices_only else 0

    # Alerts
    if ratio >= RATIO_ALERT_HIGH:
        alerts.append("SELL PRESSURE HIGH: ratio=%.2f" % ratio)
    elif ratio <= RATIO_ALERT_LOW:
        alerts.append("BUY PRESSURE HIGH: ratio=%.2f" % ratio)

    for w in walls:
        alerts.append("WALL: %s ETH @ %s" % (w['a'], w['p']))

    # Trend from history
    if len(history) >= 5:
        recent_ratios = [h.get('ratio', 0) for h in list(history)[-5:]]
        if all(r > 1.3 for r in recent_ratios):
            alerts.append("SUSTAINED SELL PRESSURE (5 ticks)")
        elif all(r < 0.75 for r in recent_ratios):
            alerts.append("SUSTAINED BUY PRESSURE (5 ticks)")

    return metrics, alerts

def main():
    print("=" * 60)
    print("  CoinGlass ETH-USDT Order Book Monitor")
    print("  Tab: %s | Poll: %ds" % (TAB_ID, POLL_SEC))
    print("=" * 60)

    history = deque(maxlen=HISTORY_LEN)
    count = 0

    while True:
        count += 1
        ts = time.strftime('%H:%M:%S')
        data = fetch_data()

        if not data:
            print("[%s] #%d NO DATA" % (ts, count))
            time.sleep(POLL_SEC)
            continue

        metrics, alerts = analyze(data, history)

        if metrics:
            history.append(metrics)
            ratio = metrics.get('ratio', 0)
            near = metrics.get('near_ratio', 0)
            ask_t = metrics.get('total_ask', 0)
            bid_t = metrics.get('total_bid', 0)
            walls = metrics.get('walls', [])
            vol = data.get('stats', {}).get('vol', '?')
            oi = data.get('stats', {}).get('oi', '?')
            ls = data.get('stats', {}).get('ls', '?')
            big = len(data.get('bigOrders', []))

            # Print summary line
            print("[%s] #%d R:%.2f NR:%.2f Ask:%d Bid:%d Walls:%d Big:%d Vol:$%s OI:$%s LS:%s" % (
                ts, count, ratio, near, ask_t, bid_t, len(walls), big, vol, oi, ls))

        # Print alerts
        for a in alerts:
            print("[%s] *** ALERT: %s ***" % (ts, a))

        time.sleep(POLL_SEC)

if __name__ == '__main__':
    main()