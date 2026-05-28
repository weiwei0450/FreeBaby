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
        if (t.indexOf('🔥') >= 0 && t.length < 300 && t.length > 2) {
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