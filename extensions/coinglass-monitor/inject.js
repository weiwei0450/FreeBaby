(function(){
if(window._hi) clearInterval(window._hi);
window._ha = [];
var TH = 0.3;
function scan(){
  var c = document.querySelectorAll('canvas')[2];
  if(!c) return null;
  var sx = Math.floor(c.width * 0.75), W = c.width - sx, H = c.height;
  var d = c.getContext('2d').getImageData(sx, 0, W, H).data;
  var rM = 0, gM = 0, rS = 0, gS = 0;
  for(var y = 0; y < H; y++){
    var rC = 0, gC = 0;
    for(var x = 0; x < W; x++){
      var i = (y * W + x) * 4;
      if(d[i+3] < 10) continue;
      if(d[i] > 120 && d[i+1] < 80 && d[i+2] < 80) rC++;
      if(d[i+1] > 120 && d[i] < 80 && d[i+2] < 80) gC++;
    }
    rM = Math.max(rM, rC); gM = Math.max(gM, gC);
    rS += rC; gS += gC;
  }
  return {rM:rM, gM:gM, rS:rS, gS:gS};
}
function beep(){
  var ac = new (window.AudioContext || window.webkitAudioContext)();
  [880, 1100, 880].forEach(function(f, i){
    var o = ac.createOscillator(), g = ac.createGain();
    o.type = 'square'; o.frequency.value = f;
    g.gain.value = 0.3;
    o.connect(g); g.connect(ac.destination);
    o.start(ac.currentTime + i * 0.15);
    o.stop(ac.currentTime + i * 0.15 + 0.1);
  });
}
var base = scan();
if(base) window._hb = base;
window._hi = setInterval(function(){
  var cur = scan(), b = window._hb;
  if(!cur || !b) return;
  var alerts = [];
  if(b.rM > 0 && Math.abs(cur.rM - b.rM) / b.rM > TH)
    alerts.push('RED ' + b.rM + '->' + cur.rM);
  if(b.gM > 0 && Math.abs(cur.gM - b.gM) / b.gM > TH)
    alerts.push('GREEN ' + b.gM + '->' + cur.gM);
  if(alerts.length > 0){
    window._hb = cur;
    window._ha.push({t: new Date().toLocaleTimeString(), a: alerts});
    beep();
    document.title = '!! ALERT !! ' + alerts.join(' | ');
    console.warn('[HM ALERT]', alerts.join(' | '));
  }
}, 10000);
return 'monitor started, base: rM=' + (base?base.rM:0) + ' gM=' + (base?base.gM:0);
})();