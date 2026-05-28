#!/usr/bin/env python3
"""
coinglass_heatmap_monitor.py
Coinglass ETHUSDT 清算热力图实时监控
通过浏览器JS读取Canvas像素，检测红绿清算线条变化

用法: python scripts/coinglass_heatmap_monitor.py
前置: 浏览器已打开 legend.coinglass.com + web_setup_sop 已执行
"""
import time
import json
import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHECK_INTERVAL = 30
ALERT_THRESHOLD = 0.3

JS_SET_BASELINE = """(() => {
  var c = document.querySelectorAll('canvas')[2];
  if (!c) return 'no canvas';
  var ctx = c.getContext('2d');
  var sx = Math.floor(c.width * 0.75);
  var W = c.width - sx, H = c.height;
  var d = ctx.getImageData(sx, 0, W, H).data;
  var rMax = 0, gMax = 0, rSum = 0, gSum = 0;
  for (var y = 0; y < H; y++) {
    var rC = 0, gC = 0;
    for (var x = 0; x < W; x++) {
      var i = (y * W + x) * 4;
      if (d[i+3] < 10) continue;
      if (d[i] > 120 && d[i+1] < 80 && d[i+2] < 80) rC++;
      if (d[i+1] > 120 && d[i] < 80 && d[i+2] < 80) gC++;
    }
    rSum += rC; gSum += gC;
    if (rC > rMax) rMax = rC;
    if (gC > gMax) gMax = gC;
  }
  window._hmBase = {rMax: rMax, gMax: gMax, rSum: rSum, gSum: gSum};
  return JSON.stringify(window._hmBase);
})()"""

JS_CHECK = """(() => {
  var c = document.querySelectorAll('canvas')[2];
  if (!c) return JSON.stringify({err:'no canvas'});
  var ctx = c.getContext('2d');
  var sx = Math.floor(c.width * 0.75);
  var W = c.width - sx, H = c.height;
  var d = ctx.getImageData(sx, 0, W, H).data;
  var rMax = 0, gMax = 0, rSum = 0, gSum = 0;
  for (var y = 0; y < H; y++) {
    var rC = 0, gC = 0;
    for (var x = 0; x < W; x++) {
      var i = (y * W + x) * 4;
      if (d[i+3] < 10) continue;
      if (d[i] > 120 && d[i+1] < 80 && d[i+2] < 80) rC++;
      if (d[i+1] > 120 && d[i] < 80 && d[i+2] < 80) gC++;
    }
    rSum += rC; gSum += gC;
    if (rC > rMax) rMax = rC;
    if (gC > gMax) gMax = gC;
  }
  var cur = {rMax: rMax, gMax: gMax, rSum: rSum, gSum: gSum};
  var b = window._hmBase;
  if (!b) return JSON.stringify({st:'no_base', cur: cur});
  var alerts = [];
  var rc = b.rMax > 0 ? (cur.rMax - b.rMax) / b.rMax : 0;
  var gc = b.gMax > 0 ? (cur.gMax - b.gMax) / b.gMax : 0;
  if (Math.abs(rc) > 0.3) alerts.push('RED ' + (rc>0?'GROW':'SHRINK') + ' ' + b.rMax + '->' + cur.rMax + ' (' + (rc*100).toFixed(1) + '%)');
  if (Math.abs(gc) > 0.3) alerts.push('GREEN ' + (gc>0?'GROW':'SHRINK') + ' ' + b.gMax + '->' + cur.gMax + ' (' + (gc*100).toFixed(1) + '%)');
  if (alerts.length > 0) window._hmBase = cur;
  return JSON.stringify({st: alerts.length > 0 ? 'ALERT' : 'ok', alerts: alerts, b: b, cur: cur});
})()"""

def notify(title, msg):
    subprocess.run(["powershell", "-Command",
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$n = New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon = [System.Drawing.SystemIcons]::Information; "
        "$n.Visible = $true; "
        "$n.ShowBalloonTip(5000, '" + title + "', '" + msg + "', 'Info')"
    ], capture_output=True, timeout=10)

def main():
    print("=== Coinglass Heatmap Monitor ===")
    print("Interval: %ds | Threshold: %d%%" % (CHECK_INTERVAL, ALERT_THRESHOLD * 100))

    from memory.tmwebdriver_sop import TMWebDriver
    driver = TMWebDriver()

    tabs = driver.get_tabs()
    cg_tab = None
    for tab in tabs:
        if 'coinglass' in tab.get('url', '').lower() or 'coinglass' in tab.get('title', '').lower():
            cg_tab = tab
            break

    if not cg_tab:
        print("ERROR: Coinglass tab not found!")
        return

    print("Found: %s" % cg_tab['title'][:60])
    driver.switch_tab(cg_tab['id'])

    result = driver.execute_js(JS_SET_BASELINE)
    print("Baseline: %s" % result)

    count = 0
    while True:
        time.sleep(CHECK_INTERVAL)
        count += 1
        try:
            result = driver.execute_js(JS_CHECK)
            data = json.loads(result)
            ts = time.strftime('%H:%M:%S')

            if data.get('st') == 'ALERT':
                msg = ' | '.join(data['alerts'])
                print("[%s] ALERT #%d: %s" % (ts, count, msg))
                notify("Coinglass ALERT", msg)
            elif count % 10 == 0:
                c = data.get('cur', {})
                print("[%s] #%d stable R:%d G:%d" % (ts, count, c.get('rMax',0), c.get('gMax',0)))
        except Exception as e:
            print("[%s] Error: %s" % (time.strftime('%H:%M:%S'), e))

if __name__ == '__main__':
    main()