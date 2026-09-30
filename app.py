import contextlib
import ctypes
import io
import threading

import webview

import main as jarvis


HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MyAssistant</title>
<style>
*{box-sizing:border-box}
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#020106}
body{font-family:Consolas,"Segoe UI",sans-serif;color:#dffcff}
#app{position:relative;width:100%;height:100%;background:
 radial-gradient(circle at 50% 48%,rgba(70,20,110,.16),transparent 34%),
 radial-gradient(circle at 50% 48%,rgba(0,130,160,.08),transparent 55%),#020106}
#top{position:absolute;z-index:20;left:26px;top:20px;font-size:19px;font-weight:700;letter-spacing:1px}
#state{position:absolute;z-index:20;right:26px;top:22px;color:#67efff;font-size:11px;letter-spacing:1px}
#visual{position:absolute;inset:0 0 105px 0}
#visual canvas{display:block;width:100%;height:100%;cursor:grab}
#visual canvas.dragging{cursor:grabbing}
#command-area{position:absolute;z-index:30;left:24px;right:24px;bottom:22px;height:64px}
#command-box{height:58px;border:1px solid #17474d;background:rgba(3,20,23,.86);display:flex;align-items:center}
#command{flex:1;height:100%;border:0;outline:0;background:transparent;color:#d9ffff;padding:0 18px;font:13px "Segoe UI",sans-serif}
#command::placeholder{color:#38666b}
#send{height:42px;margin-right:8px;padding:0 22px;border:0;background:#062a2f;color:#5feaf2;font:bold 11px Consolas;cursor:pointer}
#send:hover{background:#0a4147}
#send:disabled{opacity:.45;cursor:default}
#log{position:absolute;left:2px;top:62px;color:#3f8d94;font-size:8px;white-space:nowrap;max-width:80%;overflow:hidden;text-overflow:ellipsis}
#core-label{position:absolute;z-index:10;left:50%;top:91%;transform:translate(-50%,-50%);text-align:center;color:#5d727c;font-size:10px;letter-spacing:2px;pointer-events:none}
#mode{position:absolute;z-index:20;left:50%;top:95px;transform:translateX(-50%);font-size:9px;color:#53636d;letter-spacing:2px}
</style>
</head>
<body>
<div id="app">
  <div id="top">MY ASSISTANT</div>
  <div id="state">● ONLINE</div>
  <div id="mode">LOCAL AI CORE</div>
  <div id="visual"></div>
  <div id="core-label">STANDBY</div>
  <div id="command-area">
    <div id="command-box">
      <input id="command" autocomplete="off" placeholder="Enter a command...">
      <button id="send">SEND</button>
    </div>
    <div id="log">SYSTEM READY</div>
  </div>
</div>

<script type="module">
import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js";

const visual=document.getElementById("visual");
const input=document.getElementById("command");
const send=document.getElementById("send");
const state=document.getElementById("state");
const label=document.getElementById("core-label");
const log=document.getElementById("log");

let apiReady=false;
window.pyReady=()=>{apiReady=true};

const scene=new THREE.Scene();
scene.fog=new THREE.FogExp2(0x020106,0.018);
const camera=new THREE.PerspectiveCamera(45,1,.1,100);
camera.position.set(0,0,8.2);

const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure=1.15;
visual.appendChild(renderer.domElement);

const root=new THREE.Group();
scene.add(root);
const core=new THREE.Group();
root.add(core);

const violet=new THREE.PointLight(0x8b4dff,7,8);
violet.position.set(0,0,1.5);
core.add(violet);
const cyan=new THREE.PointLight(0x24dfff,3,6);
cyan.position.set(-2,1,2);
core.add(cyan);

const honey=new THREE.Mesh(
  new THREE.IcosahedronGeometry(1.55,3),
  new THREE.MeshBasicMaterial({color:0xffc83d,wireframe:true,transparent:true,opacity:.82})
);
core.add(honey);

const inner=new THREE.Mesh(
  new THREE.IcosahedronGeometry(1.12,2),
  new THREE.MeshBasicMaterial({color:0xff9e27,wireframe:true,transparent:true,opacity:.24})
);
core.add(inner);

function wireSphere(radius,opacity,scaleY,color){
  const m=new THREE.Mesh(
    new THREE.IcosahedronGeometry(radius,2),
    new THREE.MeshBasicMaterial({color,wireframe:true,transparent:true,opacity})
  );
  m.scale.y=scaleY;
  core.add(m);
  return m;
}
const shellA=wireSphere(1.86,.34,1,0xdbe7ff);
const shellB=wireSphere(2.02,.18,.88,0xb9c8ff);
const shellC=wireSphere(2.18,.12,1.04,0x9da6ff);

const dotCount=4200;
const positions=new Float32Array(dotCount*3);
for(let i=0;i<dotCount;i++){
  const u=Math.random()*2-1,a=Math.random()*Math.PI*2,s=Math.sqrt(1-u*u);
  const r=2.14*(.97+Math.random()*.045);
  positions[i*3]=r*s*Math.cos(a);
  positions[i*3+1]=r*u;
  positions[i*3+2]=r*s*Math.sin(a);
}
const dotGeo=new THREE.BufferGeometry();
dotGeo.setAttribute("position",new THREE.BufferAttribute(positions,3));
const dotMat=new THREE.PointsMaterial({color:0xdce6ff,size:.012,transparent:true,opacity:.8,blending:THREE.AdditiveBlending,depthWrite:false});
const dots=new THREE.Points(dotGeo,dotMat);
core.add(dots);

for(let band=0;band<13;band++){
  const phi=-1.15+band*.19,rr=2.06*Math.cos(phi),yy=2.06*Math.sin(phi),count=120;
  const p=new Float32Array(count*3);
  for(let i=0;i<count;i++){
    const a=i/count*Math.PI*2;
    p[i*3]=rr*Math.cos(a);p[i*3+1]=yy;p[i*3+2]=rr*Math.sin(a);
  }
  const g=new THREE.BufferGeometry();
  g.setAttribute("position",new THREE.BufferAttribute(p,3));
  const m=new THREE.PointsMaterial({color:0xeaf1ff,size:.009,transparent:true,opacity:.42,blending:THREE.AdditiveBlending,depthWrite:false});
  core.add(new THREE.Points(g,m));
}

const orbits=[];
function makeOrbit(rx,ry,rz,tilt,color,offset){
  const pts=[];
  for(let i=0;i<220;i++){
    const a=i/220*Math.PI*2,w=1+.025*Math.sin(a*7+offset);
    pts.push(new THREE.Vector3(Math.cos(a)*rx*w,Math.sin(a)*ry*w,Math.sin(a*2+offset)*rz));
  }
  const curve=new THREE.CatmullRomCurve3(pts,true);
  const geo=new THREE.BufferGeometry().setFromPoints(curve.getPoints(320));
  const mat=new THREE.LineBasicMaterial({color,transparent:true,opacity:.9,blending:THREE.AdditiveBlending});
  const line=new THREE.LineLoop(geo,mat);
  line.rotation.set(tilt.x,tilt.y,tilt.z);
  core.add(line);
  const marker=new THREE.Mesh(new THREE.SphereGeometry(.065,10,10),new THREE.MeshBasicMaterial({color,transparent:true,blending:THREE.AdditiveBlending}));
  core.add(marker);
  orbits.push({curve,line,marker,phase:offset,speed:.25+Math.random()*.25});
}
makeOrbit(2.65,.70,.12,new THREE.Euler(.15,.15,.15),0xffc32e,.2);
makeOrbit(2.45,.62,.16,new THREE.Euler(1,-.2,.45),0xff9b2d,2.2);
makeOrbit(2.75,.48,.12,new THREE.Euler(-.7,.55,-.3),0xffd84a,4.1);
makeOrbit(2.35,.82,.1,new THREE.Euler(.35,-.9,.7),0xff6e3c,5.7);
makeOrbit(2.6,.55,.14,new THREE.Euler(-1,.2,-.6),0xffc83d,1.4);

const arcGroup=new THREE.Group();
core.add(arcGroup);
for(let i=0;i<22;i++){
  const r=1.7+Math.random()*.65,start=Math.random()*Math.PI*2,span=.25+Math.random()*.85,pts=[];
  for(let j=0;j<18;j++){
    const a=start+span*j/17;
    pts.push(new THREE.Vector3(Math.cos(a)*r,Math.sin(a)*r*(.42+Math.random()*.08),(Math.random()-.5)*.25));
  }
  const geo=new THREE.BufferGeometry().setFromPoints(pts);
  const mat=new THREE.LineBasicMaterial({color:i%3===0?0xb8b8ff:0xffffff,transparent:true,opacity:.45+Math.random()*.35,blending:THREE.AdditiveBlending});
  const l=new THREE.Line(geo,mat);
  l.rotation.set(Math.random()*2,Math.random()*2,Math.random()*2);
  arcGroup.add(l);
}

const glowCanvas=document.createElement("canvas");
glowCanvas.width=256;glowCanvas.height=256;
const gc=glowCanvas.getContext("2d");
const grd=gc.createRadialGradient(128,128,5,128,128,128);
grd.addColorStop(0,"rgba(100,50,255,.34)");
grd.addColorStop(.35,"rgba(80,30,220,.18)");
grd.addColorStop(1,"rgba(0,0,0,0)");
gc.fillStyle=grd;gc.fillRect(0,0,256,256);
const glow=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(glowCanvas),transparent:true,depthWrite:false,blending:THREE.AdditiveBlending}));
glow.scale.set(7.2,7.2,1);
core.add(glow);

let working=false,coreState="idle",dragging=false,px=0,py=0;
let targetX=-.05,targetY=.15,currentX=targetX,currentY=targetY;

renderer.domElement.addEventListener("pointerdown",e=>{
  dragging=true;px=e.clientX;py=e.clientY;
  renderer.domElement.classList.add("dragging");
  renderer.domElement.setPointerCapture(e.pointerId);
});
renderer.domElement.addEventListener("pointermove",e=>{
  if(!dragging)return;
  targetY+=(e.clientX-px)*.006;
  targetX+=(e.clientY-py)*.006;
  targetX=Math.max(-1.15,Math.min(1.15,targetX));
  px=e.clientX;py=e.clientY;
});
renderer.domElement.addEventListener("pointerup",()=>{dragging=false;renderer.domElement.classList.remove("dragging")});

function setCoreState(next){
  coreState=next;
  working=next!=="idle";

  const states={
    idle:{status:"● ONLINE",statusColor:"#67efff",label:"STANDBY",logPrefix:"SYSTEM READY"},
    thinking:{status:"● THINKING",statusColor:"#ffc83d",label:"THINKING",logPrefix:"AI THINKING"},
    executing:{status:"● EXECUTING",statusColor:"#ff9f43",label:"EXECUTING",logPrefix:"COMMAND EXECUTING"},
    complete:{status:"● COMPLETE",statusColor:"#8dffb3",label:"COMPLETE",logPrefix:"COMMAND COMPLETE"}
  };

  const current=states[next]||states.idle;
  state.textContent=current.status;
  state.style.color=current.statusColor;
  label.textContent=current.label;
}

function setWorking(v){
  setCoreState(v?"thinking":"idle");
}

function resize(){
  const w=visual.clientWidth,h=visual.clientHeight;
  renderer.setSize(w,h,false);
  camera.aspect=w/h;
  camera.updateProjectionMatrix();
}
addEventListener("resize",resize);
resize();

async function sendCommand(){
  if(working)return;
  const command=input.value.trim();
  if(!command)return;
  input.value="";
  log.textContent="COMMAND: "+command;
  if(command.toLowerCase()==="exit"){
    if(window.pywebview) await window.pywebview.api.close_app();
    return;
  }
  setCoreState("thinking");
  send.disabled=true;
  try{
    // Give the renderer a frame to show the THINKING state before the
    // Python bridge begins the synchronous assistant operation.
    await new Promise(requestAnimationFrame);
    setCoreState("executing");
    const result=await window.pywebview.api.run_command(command);
    log.textContent=(result||"Command completed.").replace(/\n/g," ");
    setCoreState("complete");
    await new Promise(resolve=>setTimeout(resolve,700));
  }catch(e){
    log.textContent="Assistant error: "+e;
    setCoreState("complete");
    await new Promise(resolve=>setTimeout(resolve,700));
  }
  setCoreState("idle");
  send.disabled=false;
  input.focus();
}
send.onclick=sendCommand;
input.addEventListener("keydown",e=>{if(e.key==="Enter")sendCommand()});

const clock=new THREE.Clock();
let elapsed=0;
function animate(){
  requestAnimationFrame(animate);
  const dt=Math.min(clock.getDelta(),.05);
  elapsed+=dt;
  const intensity=coreState==="idle"?0:coreState==="thinking"?.65:coreState==="executing"?1:0.35;
  const speed=.55+1.25*intensity;

  if(!dragging){
    targetY+=dt*((.11+.27*intensity));
    targetX+=Math.sin(elapsed*((0.55+1.15*intensity)))*dt*((.025+.095*intensity));
  }
  currentX+=(targetX-currentX)*.055;
  currentY+=(targetY-currentY)*.055;
  root.rotation.x=currentX;
  root.rotation.y=currentY;

  const pulse=1+Math.sin(elapsed*((1.5+4*intensity)))*((.012+.023*intensity));
  root.scale.setScalar(pulse);

  honey.rotation.x+=dt*((.07+.15*intensity));
  honey.rotation.y+=dt*((.10+.24*intensity));
  inner.rotation.x-=dt*((.05+.10*intensity));
  inner.rotation.y+=dt*((.08+.18*intensity));
  shellA.rotation.x+=dt*((.045+.135*intensity));
  shellA.rotation.y-=dt*((.055+.165*intensity));
  shellB.rotation.z+=dt*((.035+.115*intensity));
  shellB.rotation.y+=dt*((.03+.08*intensity));
  shellC.rotation.x-=dt*((.025+.075*intensity));
  shellC.rotation.z+=dt*((.03+.10*intensity));
  dots.rotation.y+=dt*((.04+.14*intensity));
  dots.rotation.x+=dt*((.015+.055*intensity));
  arcGroup.rotation.y-=dt*((.045+.175*intensity));
  arcGroup.rotation.z+=dt*((.025+.105*intensity));

  dots.material.size=.012*((1+0.35*intensity));
  dots.material.opacity=(.78+.17*intensity);
  for(const o of orbits){
    o.line.rotation.y+=dt*((.055+.185*intensity));
    o.line.rotation.x+=dt*((.025+.085*intensity));
    o.phase+=dt*o.speed*((1+2*intensity));
    const t=(o.phase%(Math.PI*2))/(Math.PI*2);
    const pos=o.curve.getPointAt(t);
    o.marker.position.copy(pos);
    o.marker.position.applyEuler(o.line.rotation);
    o.marker.scale.setScalar((1+0.3*intensity));
  }
  glow.scale.setScalar(7.2*((1+0.16*intensity+Math.sin(elapsed*(2+3*intensity))*.05*intensity)));
  violet.intensity=(7+3*intensity);

  renderer.render(scene,camera);
}
animate();
</script>
</body>
</html>
"""


class Bridge:
    def __init__(self):
        self._hwnd = None

    def run_command(self, command):
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                result = jarvis.process_command(command)

            output = buffer.getvalue().strip()
            if not output:
                if result == "exit":
                    output = "Assistant: Shutting down."
                else:
                    output = "Assistant: Command completed."
            return output
        except Exception as error:
            return f"Assistant error: {error}"

    def close_app(self):
        # pywebview JS API methods execute on worker threads. Do not call
        # window.destroy() directly here because WebView2 native objects
        # must be accessed from the GUI thread. Post WM_CLOSE instead;
        # Windows delivers it through the window's normal UI message loop.
        if self._hwnd:
            ctypes.windll.user32.PostMessageW(self._hwnd, 0x0010, 0, 0)
        return "closed"


def _cache_native_handle(window, api):
    # Kept for compatibility with pywebview versions that pass the window.
    try:
        api._hwnd = int(window.native.Handle.ToInt64())
    except Exception:
        api._hwnd = None


def _cache_native_handle_noargs(window, api):
    # pywebview 6.2.x may invoke before_show without positional arguments.
    # The window is already available through this closure.
    try:
        api._hwnd = int(window.native.Handle.ToInt64())
    except Exception:
        api._hwnd = None


def main():
    # MyAssistant does not use browser navigation menus. Disabling pywebview's
    # default menus avoids unnecessary WebView2 back/forward state queries.
    webview.settings["SHOW_DEFAULT_MENUS"] = False

    api = Bridge()

    window = webview.create_window(
        "MyAssistant",
        html=HTML,
        js_api=api,
        width=1200,
        height=760,
        min_size=(900, 650),
        background_color="#020106",
    )

    window.events.before_show += lambda: _cache_native_handle_noargs(window, api)
    webview.start(gui="edgechromium", debug=False, http_server=False)


if __name__ == "__main__":
    main()
