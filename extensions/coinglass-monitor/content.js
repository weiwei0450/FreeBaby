// Coinglass OB Monitor v5 - 变化驱动 + 方向转折点
(function(){
'use strict';
if(window._obSI){clearInterval(window._obSI);window._obSI=null;}
if(document.getElementById('_obP'))document.getElementById('_obP').remove();

var S={h:[],al:[],prevOB:null,prevRatio:0,prevNR:0,prevWallCount:0,ot:document.title,PM:3000,WT:5000,lastDir:'-',CP:0.30,turns:[]};

function ob(){
  var p=document.querySelectorAll('.obv2-item-price'),a=document.querySelectorAll('.obv2-item-amount'),o=[],l=Math.min(p.length,a.length);
  for(var i=0;i<l;i++){var pp=parseFloat(p[i].innerText),aa=parseFloat(a[i].innerText);if(!isNaN(pp)&&!isNaN(aa))o.push({p:pp,a:aa});}
  if(o.length<6)return null;
  o.sort(function(x,y){return x.p-y.p});
  var md=o[Math.floor(o.length/2)].p,as=[],bd=[],ta=0,tb=0;
  for(var j=0;j<o.length;j++){if(o[j].p>=md)as.push(o[j]);else bd.push(o[j]);}
  for(var j=0;j<as.length;j++)ta+=as[j].a;
  for(var j=0;j<bd.length;j++)tb+=bd[j].a;
  var r=tb>0?ta/tb:0,nas=as.slice(0,3),nbd=bd.slice(-3).reverse(),nta=0,ntb=0;
  for(var j=0;j<nas.length;j++)nta+=nas[j].a;
  for(var j=0;j<nbd.length;j++)ntb+=nbd[j].a;
  var nr=ntb>0?nta/ntb:0,ws=[],bw=0,sw=0;
  for(var j=0;j<o.length;j++){if(o[j].a>=S.WT)ws.push(o[j]);if(o[j].p<md&&o[j].a>=S.WT)bw+=o[j].a;if(o[j].p>=md&&o[j].a>=S.WT)sw+=o[j].a;}
  return{ts:Date.now(),ob:o,ta:Math.round(ta),tb:Math.round(tb),r:Math.round(r*1000)/1000,nr:Math.round(nr*1000)/1000,ws:ws,wc:ws.length,lp:o[0].p,hp:o[o.length-1].p,bw:Math.round(bw),sw:Math.round(sw)};
}

function detectChanges(cur){
  if(!S.prevOB||!cur)return[];
  var prev=S.prevOB,changes=[],pM={};
  for(var i=0;i<prev.length;i++)pM[prev[i].p]=prev[i].a;
  for(var i=0;i<cur.length;i++){
    var pp=cur[i].p,ca=cur[i].a,pa=pM[pp];
    if(pa===undefined||pa===0)continue;
    var pct=Math.abs(ca-pa)/pa;
    if(pct>=S.CP){changes.push({p:pp,pa:pa,ca:ca,diff:Math.abs(ca-pa),pct:Math.round(pct*100),dir:ca>pa?'ADD':'REM'});}
    delete pM[pp];
  }
  for(var k in pM){if(pM[k]>1000)changes.push({p:parseFloat(k),pa:pM[k],ca:0,diff:pM[k],pct:100,dir:'VANISH'});}
  changes.sort(function(x,y){return y.diff-x.diff;});
  return changes.slice(0,10);
}

function detectTurns(d,changes){
  var signals=[];
  if(!d)return signals;

  // 1. Ratio reversal
  if(S.prevRatio>0){
    var rDelta=d.r-S.prevRatio;
    if(Math.abs(rDelta)>=0.1){
      signals.push({type:'R_REVERSAL',val:rDelta>0?'BEAR':'BULL',strength:Math.abs(rDelta),msg:'sell/buy '+(rDelta>0?'+':'')+rDelta.toFixed(3)});
    }
  }

  // 2. Near-ratio extreme flip
  if(S.prevNR>0){
    var nrDelta=d.nr-S.prevNR;
    if(Math.abs(nrDelta)>=0.5){
      signals.push({type:'NR_SHIFT',val:nrDelta>0?'BEAR':'BULL',strength:Math.abs(nrDelta),msg:'near ratio '+(nrDelta>0?'+':'')+nrDelta.toFixed(2)});
    }
  }

  // 3. Wall surge/disappear
  var wallDelta=d.wc-S.prevWallCount;
  if(Math.abs(wallDelta)>=5){
    signals.push({type:'WALL_SHIFT',val:wallDelta>0?'BEAR':'BULL',strength:Math.abs(wallDelta),msg:'walls '+(wallDelta>0?'+':'')+wallDelta});
  }

  // 4. Massive order pull (VANISH)
  var vanishes=changes.filter(function(c){return c.dir==='VANISH'&&c.diff>=5000;});
  if(vanishes.length>=3){
    var aboveMid=0,belowMid=0;
    var mid=d.lp+(d.hp-d.lp)/2;
    vanishes.forEach(function(v){if(v.p>=mid)aboveMid++;else belowMid++;});
    if(aboveMid>belowMid+1)signals.push({type:'PULL_SELL',val:'BULL',strength:aboveMid,msg:'sell wall pull x'+aboveMid});
    else if(belowMid>aboveMid+1)signals.push({type:'PULL_BUY',val:'BEAR',strength:belowMid,msg:'buy wall pull x'+belowMid});
  }

  // 5. Massive order appear
  var adds=changes.filter(function(c){return c.dir==='ADD'&&c.diff>=8000;});
  adds.forEach(function(a){
    var mid=d.lp+(d.hp-d.lp)/2;
    signals.push({type:'WALL_ADD',val:a.p>=mid?'BEAR':'BULL',strength:a.diff,msg:(a.p>=mid?'sell':'buy')+' wall +'+a.diff+'@'+a.p});
  });

  return signals;
}

function analyze(d,changes,turns){
  if(!d)return{dir:'-',conf:0,rs:['NO DATA']};
  var sc=0,rs=[];

  // Base scoring (same as v4)
  if(d.r>1.3){sc+=4;rs.push('\u5356\u538b\u5927['+d.r+']');}
  else if(d.r>1.15){sc+=2;rs.push('\u5356\u538b\u504f\u5927['+d.r+']');}
  else if(d.r<0.7){sc-=4;rs.push('\u4e70\u529b\u5f3a['+d.r+']');}
  else if(d.r<0.85){sc-=2;rs.push('\u4e70\u529b\u504f\u5f3a['+d.r+']');}
  if(d.nr>2){sc+=3;rs.push('\u8fd1\u7aef\u5356\u538b['+d.nr+']');}
  else if(d.nr>1.5){sc+=1;rs.push('\u8fd1\u7aef\u5356\u504f\u5927');}
  else if(d.nr<0.5){sc-=3;rs.push('\u8fd1\u7aef\u4e70\u62a2['+d.nr+']');}
  else if(d.nr<0.7){sc-=1;rs.push('\u8fd1\u7aef\u4e70\u504f\u5f3a');}
  if(d.sw>d.bw*1.5){sc+=2;rs.push('\u5356\u5899\u538b\u5236');}
  else if(d.bw>d.sw*1.5){sc-=2;rs.push('\u4e70\u5899\u62a4\u76d8');}

  // Turn signals (high weight - these are the KEY signals)
  for(var i=0;i<turns.length;i++){
    var t=turns[i];
    if(t.val==='BEAR')sc+=Math.min(t.strength*3, 4);
    else sc-=Math.min(t.strength*3, 4);
    rs.push('\u26a0'+t.msg);
  }

  // Order changes
  if(changes.length>0){
    var big=changes.filter(function(c){return c.diff>=3000;});
    if(big.length>0){
      var s=big.map(function(c){return(c.dir==='ADD'?'+':'-')+c.diff+'@'+c.p;}).join(',');
      rs.push('\u6302\u5355\u53d8\u52a8:'+s);
      var van=big.filter(function(c){return c.dir==='VANISH';});
      if(van.length>0)sc+=2;
    }
  }

  // Trend
  S.h.push({r:d.r,nr:d.nr,s:sc});
  if(S.h.length>30)S.h=S.h.slice(-30);
  if(S.h.length>=3){var l3=S.h.slice(-3),cnt=0;for(var i=0;i<3;i++){if(l3[i].s>0)cnt++;if(l3[i].s<0)cnt--;}if(cnt>=2){sc+=1;rs.push('\u6301\u7eed\u5356\u538b');}else if(cnt<=-2){sc-=1;rs.push('\u6301\u7eed\u4e70\u529b');}}

  var dir='NEUTRAL',dc='#aaa',em='\u2195';
  if(sc>=4){dir='STRONG SHORT';dc='#f22';em='\ud83d\udcc9';}
  else if(sc>=2){dir='SHORT';dc='#f66';em='\u2b07\ufe0f';}
  else if(sc<=-4){dir='STRONG LONG';dc='#0f0';em='\ud83d\udcc8';}
  else if(sc<=-2){dir='LONG';dc='#0c0';em='\u2b06\ufe0f';}
  var cf=Math.min(Math.abs(sc)/6*100,100);
  return{dir:dir,dc:dc,em:em,sc:sc,cf:Math.round(cf),rs:rs,turns:turns};
}

// Create panel
var p=document.createElement('div');p.id='_obP';
p.style.cssText='position:fixed;top:10px;right:10px;width:340px;background:rgba(0,0,0,0.95);color:#0f0;font:11px/1.5 monospace;padding:12px 14px;border-radius:10px;z-index:99999;border:1px solid #444;cursor:move;box-shadow:0 6px 30px rgba(0,0,0,0.6);max-height:90vh;overflow-y:auto;';
p.innerHTML=
  '<div id="_obM" style="position:absolute;top:4px;right:10px;cursor:pointer;font-size:16px;color:#888;">_</div>'+
  '<div style="color:#0cf;font-size:14px;font-weight:bold;margin-bottom:6px;">OB Monitor v5</div>'+
  '<div id="_obSt" style="margin-bottom:4px;"></div>'+
  '<div style="background:rgba(255,255,255,0.05);border-radius:6px;padding:8px 10px;margin-bottom:8px;">'+
    '<div style="font-size:12px;color:#888;margin-bottom:2px;">DIRECTION</div>'+
    '<div id="_obDir" style="font-size:18px;font-weight:bold;">-</div>'+
    '<div id="_obConf" style="font-size:10px;color:#888;">-</div>'+
    '<div id="_obReasons" style="font-size:10px;color:#aaa;margin-top:3px;line-height:1.3;"></div>'+
    '<div id="_obScore" style="font-size:10px;color:#666;margin-top:2px;"></div></div>'+
  '<div style="color:#888;font-size:10px;border-bottom:1px solid #333;padding-bottom:2px;margin-bottom:3px;">SIGNALS</div>'+
  '<div id="_obTurns" style="font-size:10px;line-height:1.4;min-height:20px;"></div>'+
  '<div style="color:#888;font-size:10px;border-bottom:1px solid #333;padding-bottom:2px;margin:6px 0 3px;">CHANGES</div>'+
  '<div id="_obChg" style="font-size:10px;line-height:1.3;"></div>'+
  '<div style="color:#888;font-size:10px;border-bottom:1px solid #333;padding-bottom:2px;margin:6px 0 3px;">ORDER BOOK</div>'+
  '<div>R:<span id="_obR" style="font-weight:bold;">-</span><span id="_obRt" style="font-size:10px;color:#666;"></span> NR:<span id="_obNr" style="color:#ff0;">-</span></div>'+
  '<div>walls:<span id="_obW">-</span></div>'+
  '<div id="_obAl" style="margin-top:6px;border-top:1px solid #333;padding-top:4px;font-size:10px;line-height:1.3;"></div>';
document.body.appendChild(p);
document.getElementById('_obM').onclick=function(){var m=p.style.height==='24px';p.style.height=m?'':'24px';p.style.overflow=m?'':'hidden';this.textContent=m?'_':'\u25a1';};
var ox,oy,dg=false;
p.onmousedown=function(e){if(e.target.id==='_obM')return;dg=true;ox=e.clientX-p.offsetLeft;oy=e.clientY-p.offsetTop;e.preventDefault();};
document.onmousemove=function(e){if(!dg)return;p.style.left=(e.clientX-ox)+'px';p.style.top=(e.clientY-oy)+'px';p.style.right='auto';};
document.onmouseup=function(){dg=false;};

function tk(){
  var d=ob(),changes=detectChanges(d),turns=detectTurns(d,changes),an=analyze(d,changes,turns);

  if(an.cf>=30&&an.dir!==S.lastDir){S.lastDir=an.dir;S.al.push({t:new Date().toLocaleTimeString(),m:an.dir+'('+an.cf+'%) '+an.rs[0]});if(S.al.length>50)S.al=S.al.slice(-50);}
  if(turns.length>0){for(var i=0;i<turns.length;i++){S.turns.push({t:new Date().toLocaleTimeString(),m:turns[i].val+' '+turns[i].msg});}if(S.turns.length>20)S.turns=S.turns.slice(-20);}
  if(an.cf>=60&&an.dir!=='NEUTRAL'){document.title=an.em+' '+an.dir+' | '+S.ot;setTimeout(function(){document.title=S.ot;},3000);}

  if(!d){document.getElementById('_obSt').innerHTML='<span style="color:#f44">NO DATA</span>';return;}
  document.getElementById('_obSt').innerHTML='<span style="color:#0c0;font-size:10px;">'+new Date().toLocaleTimeString()+'</span>';
  var de=document.getElementById('_obDir');de.textContent=an.em+' '+an.dir;de.style.color=an.dc;
  document.getElementById('_obConf').innerHTML='confidence:<span style="color:'+an.dc+'">'+an.cf+'%</span>';
  document.getElementById('_obReasons').textContent=an.rs.join(' | ');
  document.getElementById('_obScore').textContent='score:'+an.sc;

  // Turn signals
  var te=document.getElementById('_obTurns');
  if(turns.length>0){
    te.innerHTML=turns.map(function(t){
      var co=t.val==='BULL'?'#0f0':t.val==='BEAR'?'#f44':'#fa0';
      return '<div style="color:'+co+';font-weight:bold;">'+t.val+' '+t.msg+'</div>';
    }).join('');
  }else te.innerHTML='<div style="color:#555">-</div>';

  // Changes
  var chEl=document.getElementById('_obChg');
  if(changes.length>0){chEl.innerHTML=changes.slice(0,6).map(function(c){var co=c.dir==='ADD'?'#0c0':c.dir==='VANISH'?'#f22':'#f80';var ic=c.dir==='ADD'?'+':c.dir==='VANISH'?'X':'-';return '<div style="color:'+co+'">'+ic+' '+c.diff+' @ '+c.p+' ('+c.pct+'%)</div>';}).join('');}else chEl.innerHTML='<div style="color:#555">-</div>';

  // OB
  var re=document.getElementById('_obR');re.textContent=d.r.toFixed(3);re.style.color=d.r>1.2?'#f44':d.r<0.8?'#0c0':'#0f0';
  var trend='';if(S.h.length>=5){var l5=S.h.slice(-5),f=l5[0].s,la=l5[l5.length-1].s;if(la>f)trend=' \u2191';else if(la<f)trend=' \u2193';}
  document.getElementById('_obRt').textContent=trend;
  document.getElementById('_obNr').textContent=d.nr.toFixed(3);
  document.getElementById('_obW').textContent=d.wc+'('+d.ws.slice(0,3).map(function(w){return w.a.toFixed(0)+'@'+w.p;}).join(',')+')';

  var ae=document.getElementById('_obAl');
  if(S.al.length>0)ae.innerHTML=S.al.slice(-5).map(function(a){return '<div style="color:#f88">'+a.t+' '+a.m+'</div>';}).join('');

  S.prevOB=d.ob; S.prevRatio=d.r; S.prevNR=d.nr; S.prevWallCount=d.wc;
}
tk();window._obSI=setInterval(tk,S.PM);
return 'OB Monitor v5 running';