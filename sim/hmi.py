#!/usr/bin/env python3
"""WTS-100 operator interface.

Run:  python3 hmi.py       then open http://127.0.0.1:8080

Reads status.json, which the controller writes every second, and serves an
operator screen: plant mimic with live values, trends, and an alarm banner.

Styled to ISA-101 high performance HMI principles, which are worth knowing
because most people get this wrong:

  - Grey background, dark text.  Not black, not a photorealistic 3D plant.
  - COLOUR IS RESERVED FOR ABNORMAL CONDITIONS.  A screen where everything is
    red, green and blue all the time means colour carries no information, and
    an operator cannot spot the one thing that is wrong.  On this screen a
    healthy plant is entirely grey.
  - Numbers are large and consistently placed, because operators read values,
    not pictures.
"""
import json, http.server, socketserver, pathlib, sys

PORT = 8080
HERE = pathlib.Path(__file__).resolve().parent

PAGE = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>WTS-100 Operator Interface</title>
<style>
 :root{--bg:#b8bcc0;--panel:#c8ccd0;--line:#6b7075;--txt:#1a1d20;--dim:#4a4f54;
       --alarm:#c0392b;--warn:#d68910;--ok:#1e6b3a}
 *{box-sizing:border-box;margin:0;padding:0}
 body{background:var(--bg);color:var(--txt);
      font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;font-size:13px}
 .bar{background:var(--panel);border-bottom:2px solid var(--line);
      padding:8px 14px;display:flex;align-items:center;gap:22px}
 .bar h1{font-size:15px;letter-spacing:.5px}
 .state{font-size:15px;font-weight:700;padding:3px 14px;border:2px solid var(--line);background:#fff}
 .wrap{display:grid;grid-template-columns:1fr 420px;gap:10px;padding:10px}
 .panel{background:var(--panel);border:1px solid var(--line);padding:10px}
 .panel h2{font-size:11px;letter-spacing:1px;border-bottom:1px solid var(--line);
           padding-bottom:4px;margin-bottom:8px;font-weight:700}
 table{width:100%;border-collapse:collapse}
 td{padding:3px 4px;font-size:12.5px}
 td.k{color:var(--dim)}
 td.v{text-align:right;font-weight:700;font-variant-numeric:tabular-nums;font-size:15px}
 td.u{width:52px;color:var(--dim);font-size:11px}
 .pill{display:inline-block;padding:1px 8px;border:1px solid var(--line);
       background:#fff;font-size:11px;font-weight:700}
 .bad{background:var(--alarm);color:#fff;border-color:var(--alarm)}
 .banner{margin:0 10px 10px;padding:8px 12px;border:2px solid var(--line);
         background:var(--panel);font-weight:700;font-size:13px}
 .banner.act{background:var(--alarm);color:#fff;border-color:#7d1f14}
 ul{list-style:none;font-size:11.5px;line-height:1.7}
 svg{display:block}
 .ev{font-family:Menlo,monospace;font-size:11px;line-height:1.65;color:var(--dim)}
 .ev b{color:var(--txt)}
</style></head><body>

<div class="bar">
  <h1>WTS-100 WATER TREATMENT AND TRANSFER SKID</h1>
  <span>STATE</span><span class="state" id="state">--</span>
  <span id="clock" style="margin-left:auto;color:var(--dim)"></span>
</div>

<div class="banner" id="banner">NO ACTIVE ALARMS</div>

<div class="wrap">
  <div>
    <div class="panel"><h2>PLANT</h2><div id="mimic"></div></div>
    <div class="panel" style="margin-top:10px"><h2>TRENDS</h2><div id="trend"></div></div>
  </div>

  <div>
    <div class="panel"><h2>MEASUREMENTS</h2><table id="meas"></table></div>
    <div class="panel" style="margin-top:10px"><h2>OUTPUTS</h2><table id="outs"></table></div>
    <div class="panel" style="margin-top:10px"><h2>PERMISSIVES</h2><table id="perm"></table></div>
    <div class="panel" style="margin-top:10px"><h2>EVENT LOG</h2><div class="ev" id="events"></div></div>
  </div>
</div>

<script>
const H=[];                       // trend history
const N=(v,d=1)=>v==null?"--":Number(v).toFixed(d);

function row(k,v,u){return `<tr><td class="k">${k}</td><td class="v">${v}</td><td class="u">${u||""}</td></tr>`}

function mimic(d){
  const lvl=(mm,max)=>Math.max(0,Math.min(1,mm/max));
  const t1=lvl(d.LT_101_mm,3000), t2=lvl(d.LT_102_mm,2500);
  const on=b=>b?"#1a1d20":"#c8ccd0";              // filled when running
  return `<svg viewBox="0 0 760 300" width="100%">
   <rect x="30" y="70" width="110" height="190" fill="none" stroke="#1a1d20" stroke-width="2"/>
   <rect x="32" y="${70+188*(1-t1)}" width="106" height="${188*t1}" fill="#8fa3b0"/>
   <text x="85" y="60" text-anchor="middle" font-size="12" font-weight="700">T-101</text>
   <text x="85" y="${282}" text-anchor="middle" font-size="12">${N(d.LT_101_mm,0)} mm</text>

   <circle cx="210" cy="130" r="20" fill="${on(d.MTR_101A)}" stroke="#1a1d20" stroke-width="2"/>
   <text x="210" y="168" text-anchor="middle" font-size="11">P-101A</text>
   <circle cx="210" cy="210" r="20" fill="${on(d.MTR_101B)}" stroke="#1a1d20" stroke-width="2"/>
   <text x="210" y="248" text-anchor="middle" font-size="11">P-101B</text>
   <line x1="140" y1="170" x2="190" y2="170" stroke="#1a1d20" stroke-width="3"/>
   <line x1="230" y1="130" x2="300" y2="130" stroke="#1a1d20" stroke-width="3"/>
   <line x1="230" y1="210" x2="300" y2="210" stroke="#1a1d20" stroke-width="3"/>
   <line x1="300" y1="130" x2="300" y2="210" stroke="#1a1d20" stroke-width="3"/>
   <line x1="300" y1="170" x2="360" y2="170" stroke="#1a1d20" stroke-width="3"/>

   <polygon points="360,158 360,182 392,158 392,182" fill="${d.XV_101?'#1a1d20':'#fff'}" stroke="#1a1d20" stroke-width="2"/>
   <text x="376" y="200" text-anchor="middle" font-size="11">FCV-101</text>
   <text x="376" y="150" text-anchor="middle" font-size="11" font-weight="700">${N(d.FCV_101_pct,0)}%</text>
   <line x1="392" y1="170" x2="450" y2="170" stroke="#1a1d20" stroke-width="3"/>

   <rect x="450" y="70" width="150" height="190" fill="none" stroke="#1a1d20" stroke-width="2"/>
   <rect x="452" y="${70+188*(1-t2)}" width="146" height="${188*t2}" fill="#8fa3b0"/>
   <text x="525" y="60" text-anchor="middle" font-size="12" font-weight="700">T-102</text>
   <text x="525" y="282" text-anchor="middle" font-size="12">${N(d.LT_102_mm,0)} mm    ${N(d.TT_102_C,1)} degC</text>
   <path d="M 470 240 l 0 -22 l 22 0 l 0 22 l 22 0 l 0 -22 l 22 0"
         fill="none" stroke="${d.HTR_EN?'#c0392b':'#6b7075'}" stroke-width="3"/>
   <text x="525" y="${168}" text-anchor="middle" font-size="11">HTR ${N(d.HTR_101_pct,0)}%</text>

   <line x1="600" y1="230" x2="660" y2="230" stroke="#1a1d20" stroke-width="3"/>
   <polygon points="660,218 660,242 692,218 692,242" fill="${d.XV_102?'#1a1d20':'#fff'}" stroke="#1a1d20" stroke-width="2"/>
   <text x="676" y="260" text-anchor="middle" font-size="11">XV-102</text>
   <line x1="692" y1="230" x2="740" y2="230" stroke="#1a1d20" stroke-width="3"/>
   <text x="726" y="220" text-anchor="middle" font-size="10">OUT</text>
  </svg>`;
}

function trend(){
  if(!H.length) return "";
  const W=700,Hh=170,P=34;
  const series=[["LT_102_mm",2500,"#1a1d20"],["TT_102_C",100,"#c0392b"],["FT_101_m3h",50,"#1e6b3a"]];
  let g=`<svg viewBox="0 0 ${W} ${Hh}" width="100%">
    <rect x="${P}" y="6" width="${W-P-8}" height="${Hh-30}" fill="#dfe2e5" stroke="#6b7075"/>`;
  for(let i=1;i<4;i++){const y=6+(Hh-30)*i/4;
    g+=`<line x1="${P}" y1="${y}" x2="${W-8}" y2="${y}" stroke="#c0c4c8"/>`}
  series.forEach(([k,max,col])=>{
    const pts=H.map((d,i)=>{
      const x=P+(W-P-8)*i/Math.max(1,H.length-1);
      const y=6+(Hh-30)*(1-Math.min(1,(d[k]||0)/max));
      return `${x.toFixed(1)},${y.toFixed(1)}`}).join(" ");
    g+=`<polyline points="${pts}" fill="none" stroke="${col}" stroke-width="1.6"/>`});
  g+=`<text x="${P}" y="${Hh-8}" font-size="10.5">LT-102 level</text>
      <text x="${P+110}" y="${Hh-8}" font-size="10.5" fill="#c0392b">TT-102 temperature</text>
      <text x="${P+250}" y="${Hh-8}" font-size="10.5" fill="#1e6b3a">FT-101 flow</text>
      <text x="4" y="14" font-size="10">100%</text><text x="10" y="${Hh-26}" font-size="10">0</text></svg>`;
  return g;
}

async function tick(){
  let d; try{ d=await (await fetch("status.json?"+Date.now())).json(); }
  catch(e){ document.getElementById("state").textContent="NO DATA"; return; }

  H.push(d); if(H.length>240) H.shift();
  document.getElementById("state").textContent=d.state;
  document.getElementById("clock").textContent=d.iso_time+"   t+"+N(d.elapsed_s,0)+" s";
  document.getElementById("mimic").innerHTML=mimic(d);
  document.getElementById("trend").innerHTML=trend();

  document.getElementById("meas").innerHTML=
    row("LT-101 raw level",N(d.LT_101_mm,0),"mm")+
    row("LT-102 treat level",N(d.LT_102_mm,0),"mm")+
    row("TT-102 temperature",N(d.TT_102_C,1),"degC")+
    row("FT-101 inlet flow",N(d.FT_101_m3h,1),"m3/h")+
    row("FT-103 dose flow",N(d.FT_103_lh,0),"L/h")+
    row("PT-101 pressure",N(d.PT_101_bar,2),"bar");

  document.getElementById("outs").innerHTML=
    row("FCV-101 valve",N(d.FCV_101_pct,0),"%")+
    row("HTR-101 heater",N(d.HTR_101_pct,0),"%")+
    row("P-103 dosing",N(d.P_103_pct,0),"%")+
    row("P-102 discharge",N(d.P_102_pct,0),"%")+
    row("flow setpoint",N(d.flow_sp_m3h,1),"m3/h")+
    row("level setpoint",N(d.level_sp_mm,0),"mm")+
    row("temp setpoint",N(d.temp_sp_C,1),"degC");

  const pill=(t,ok)=>`<span class="pill${ok?"":" bad"}">${ok?t:t+" BLOCKED"}</span>`;
  document.getElementById("perm").innerHTML=
    `<tr><td colspan="3">${pill("RAW PUMPS",d.perm_pumps)} ${pill("HEATER",d.perm_heater)} ${pill("INLET",d.perm_inlet)}</td></tr>`+
    `<tr><td colspan="3" style="padding-top:8px">${d.trip?'<span class="pill bad">TRIPPED, first out I'+d.first_out+'</span>':'<span class="pill">NO TRIP</span>'}</td></tr>`;

  const b=document.getElementById("banner");
  if(d.alarm_names && d.alarm_names.length){
    b.className="banner act";
    b.textContent=d.alarm_names.length+" ACTIVE   |   FIRST OUT: "+d.alarm_names[0]
                 +(d.alarm_names.length>1?"   |   "+d.alarm_names.slice(1).join("   "):"");
  } else { b.className="banner"; b.textContent="NO ACTIVE ALARMS"; }

  document.getElementById("events").innerHTML =
    (d.events||[]).slice().reverse().map(e=>`<b>t+${e[0]}s</b>  ${e[1]}  ${e[2]}`).join("<br>");
}
setInterval(tick,500); tick();
</script></body></html>"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(HERE), **k)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def log_message(self, *a):
        pass                                  # keep the console clean


if __name__ == "__main__":
    if not (HERE / "status.json").exists():
        print("note: status.json not found yet.  Start plant_server.py and plc.py,")
        print("      the screen will populate once the controller is running.\n")
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as s:
        print(f"WTS-100 operator interface on http://127.0.0.1:{PORT}")
        print("Ctrl+C to stop")
        try:
            s.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
