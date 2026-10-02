from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QObject, Slot, Signal
from PySide6.QtGui import QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MyAssistant</title>
<style>
*{box-sizing:border-box}
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:transparent}
body{font-family:Consolas,"Segoe UI",sans-serif;color:#dffcff}
#app{position:relative;width:100%;height:100%;background:
 transparent}
#top{position:absolute;z-index:20;left:26px;top:20px;font-size:19px;font-weight:700;letter-spacing:1px}
#state{position:absolute;z-index:20;right:26px;top:22px;color:#67efff;font-size:11px;letter-spacing:1px}
#visual{position:absolute;inset:0 0 105px 0}
#visual canvas{display:block;width:100%;height:100%;cursor:grab}
#visual canvas.dragging{cursor:grabbing}
#visual canvas.moving-window{cursor:move}
#command-area{position:absolute;z-index:30;left:24px;right:24px;bottom:22px;height:64px}
#command-box{height:58px;border:1px solid #17474d;background:rgba(3,20,23,.72);display:flex;align-items:center}
#command{flex:1;min-width:0;height:100%;border:0;outline:0;background:transparent;color:#d9ffff;padding:0 18px;font:13px "Segoe UI",sans-serif}
#command::placeholder{color:#38666b}
#send{flex:0 0 auto;height:42px;margin-right:8px;padding:0 22px;border:0;background:#062a2f;color:#5feaf2;font:bold 11px Consolas;cursor:pointer}
#send:hover{background:#0a4147}
#voice{flex:0 0 auto;height:42px;margin-right:6px;padding:0 16px;border:1px solid #17474d;background:#041d21;color:#8df7ff;font:bold 11px Consolas;cursor:pointer}
#voice:hover{background:#08343a}
#voice:disabled{opacity:.45;cursor:default}
#send:disabled{opacity:.45;cursor:default}
#log{position:absolute;left:2px;top:62px;color:#3f8d94;font-size:8px;white-space:nowrap;max-width:80%;overflow:hidden;text-overflow:ellipsis}
#core-label{position:absolute;z-index:10;left:50%;top:91%;transform:translate(-50%,-50%);text-align:center;color:#5d727c;font-size:10px;letter-spacing:2px;pointer-events:none}
#mode{position:absolute;z-index:20;left:50%;top:95px;transform:translateX(-50%);font-size:9px;color:#53636d;letter-spacing:2px}
</style>
</head>
<body>
<div id="app">

  <div id="state">● ONLINE</div>
  <div id="mode">LOCAL AI CORE</div>
  <div id="visual"></div>
  <div id="core-label">STANDBY</div>
  <div id="command-area">
    <div id="command-box">
      <input id="command" autocomplete="off" placeholder="Enter a command...">
      <button id="voice" title="Voice command">🎙 VOICE</button>
      <button id="send">SEND</button>
    </div>
    <div id="log">SYSTEM READY</div>
  </div>
</div>

<script type="module">
import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js";

const webChannelScript=document.createElement("script");
webChannelScript.src="qrc:///qtwebchannel/qwebchannel.js";
document.head.appendChild(webChannelScript);

let nativeBridge=null;
let assistantBridge=null;
function waitForNativeBridge(){
  if(typeof QWebChannel === "undefined"){ setTimeout(waitForNativeBridge,50); return; }
  new QWebChannel(qt.webChannelTransport, channel=>{
    nativeBridge=channel.objects.bridge;
    assistantBridge=channel.objects.assistant;
  });
}
waitForNativeBridge();


function waitForAssistantSignals(){
  if(!assistantBridge){ setTimeout(waitForAssistantSignals,50); return; }

  assistantBridge.commandFinished.connect(output=>{
    log.textContent=(output||"Command completed.").replace(/\\n/g," ");
    setCoreState("complete");
    setTimeout(()=>{
      setCoreState("idle");
      send.disabled=false;
      voice.disabled=false;
      input.focus();
    },700);
  });

  assistantBridge.voiceFinished.connect(text=>{
    if(!text){
      log.textContent="No voice command detected.";
      setCoreState("idle");
      send.disabled=false;
      voice.disabled=false;
      return;
    }

    if(text.startsWith("__VOICE_ERROR__:")){
      log.textContent=text.substring("__VOICE_ERROR__:".length);
      setCoreState("idle");
      send.disabled=false;
      voice.disabled=false;
      return;
    }

    input.value=text;
    log.textContent="VOICE: "+text;

    if(text.trim().toLowerCase()==="exit"){
      assistantBridge.closeApp();
      return;
    }

    setCoreState("thinking");
    setCoreState("executing");
    assistantBridge.runCommand(text);
  });
}
waitForAssistantSignals();

const visual=document.getElementById("visual");
const input=document.getElementById("command");
const send=document.getElementById("send");
const voice=document.getElementById("voice");
const state=document.getElementById("state");
const label=document.getElementById("core-label");
const log=document.getElementById("log");

let apiReady=false;
window.pyReady=()=>{apiReady=true};

const scene=new THREE.Scene();
const camera=new THREE.PerspectiveCamera(45,1,.1,100);
camera.position.set(0,0,8.2);

const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.setClearColor(0x000000,0);
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

let working=false,coreState="idle",dragging=false,movingWindow=false,px=0,py=0,lastScreenX=0,lastScreenY=0;
let targetX=-.05,targetY=.15,currentX=targetX,currentY=targetY;

const coreHitRadius=78;

function isUiControl(target){
  return !!target.closest("#command-area, input, button, textarea, select, a");
}

function isCoreHit(e){
  if(e.target!==renderer.domElement)return false;
  const rect=renderer.domElement.getBoundingClientRect();
  const cx=rect.left+rect.width/2;
  const cy=rect.top+rect.height/2;
  const dx=e.clientX-cx;
  const dy=e.clientY-cy;
  return Math.hypot(dx,dy)<=coreHitRadius;
}

renderer.domElement.addEventListener("pointerdown",e=>{
  e.preventDefault();
  e.stopPropagation();

  if(isCoreHit(e)){
    dragging=true;
    movingWindow=false;
    px=e.clientX;py=e.clientY;
    renderer.domElement.classList.add("dragging");
    renderer.domElement.setPointerCapture(e.pointerId);
    return;
  }

  movingWindow=true;
  dragging=false;
  lastScreenX=e.screenX;
  lastScreenY=e.screenY;
  renderer.domElement.classList.add("moving-window");
  renderer.domElement.setPointerCapture(e.pointerId);
});

renderer.domElement.addEventListener("pointermove",e=>{
  if(dragging){
    e.preventDefault();
    e.stopPropagation();
    targetY+=(e.clientX-px)*.006;
    targetX+=(e.clientY-py)*.006;
    px=e.clientX;py=e.clientY;
    return;
  }

  if(movingWindow){
    e.preventDefault();
    e.stopPropagation();
    const dx=e.screenX-lastScreenX;
    const dy=e.screenY-lastScreenY;
    if(nativeBridge && (dx||dy)) nativeBridge.moveBy(dx,dy);
    lastScreenX=e.screenX;
    lastScreenY=e.screenY;
  }
});

function stopPointerDrag(e){
  if(e){
    e.preventDefault();
    e.stopPropagation();
  }
  dragging=false;
  movingWindow=false;
  renderer.domElement.classList.remove("dragging","moving-window");
  if(e && renderer.domElement.hasPointerCapture?.(e.pointerId)){
    renderer.domElement.releasePointerCapture(e.pointerId);
  }
}

renderer.domElement.addEventListener("pointerup",stopPointerDrag);
renderer.domElement.addEventListener("pointercancel",stopPointerDrag);
renderer.domElement.addEventListener("lostpointercapture",()=>{
  dragging=false;
  movingWindow=false;
  renderer.domElement.classList.remove("dragging","moving-window");
});

// Empty transparent space outside the 3D core moves the whole HUD.
document.addEventListener("pointerdown",e=>{
  if(isUiControl(e.target))return;
  if(e.target===renderer.domElement)return;
  if(!nativeBridge)return;
  e.preventDefault();
  lastScreenX=e.screenX;
  lastScreenY=e.screenY;
  movingWindow=true;
});

document.addEventListener("pointermove",e=>{
  if(!movingWindow || dragging || isUiControl(e.target))return;
  const dx=e.screenX-lastScreenX;
  const dy=e.screenY-lastScreenY;
  if(nativeBridge && (dx||dy)) nativeBridge.moveBy(dx,dy);
  lastScreenX=e.screenX;
  lastScreenY=e.screenY;
});

document.addEventListener("pointerup",()=>{
  movingWindow=false;
});

function setCoreState(next){
  coreState=next;
  working=next!=="idle";

  const states={
    idle:{status:"● ONLINE",statusColor:"#67efff",label:"STANDBY",logPrefix:"SYSTEM READY"},
    listening:{status:"● LISTENING",statusColor:"#67efff",label:"LISTENING",logPrefix:"LISTENING FOR VOICE"},
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

async function listenVoice(){
  if(working)return;

  setCoreState("listening");
  send.disabled=true;
  voice.disabled=true;
  input.value="";
  log.textContent="LISTENING FOR VOICE...";

  if(!assistantBridge){
    log.textContent="Assistant bridge is not ready.";
    setCoreState("idle");
    send.disabled=false;
    voice.disabled=false;
    return;
  }

  assistantBridge.listenForVoice();
}

async function sendCommand(){
  if(working)return;

  const command=input.value.trim();
  if(!command)return;

  input.value="";
  log.textContent="COMMAND: "+command;

  if(command.toLowerCase()==="exit"){
    if(assistantBridge) assistantBridge.closeApp();
    return;
  }

  if(!assistantBridge){
    log.textContent="Assistant bridge is not ready.";
    return;
  }

  setCoreState("thinking");
  send.disabled=true;
  voice.disabled=true;

  await new Promise(requestAnimationFrame);
  setCoreState("executing");
  assistantBridge.runCommand(command);
}

send.onclick=sendCommand;
voice.onclick=listenVoice;
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


import contextlib
import io
import sys
import threading

import main as jarvis

from PySide6.QtCore import Qt, QUrl, QObject, Slot, Signal
from PySide6.QtGui import QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView


class TransparentWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundColor(QColor(0, 0, 0, 0))


class WindowBridge(QObject):
    def __init__(self, window):
        super().__init__()
        self.window = window

    @Slot(int, int)
    def moveBy(self, dx, dy):
        self.window.move(
            self.window.x() + int(dx),
            self.window.y() + int(dy)
        )


class AssistantBridge(QObject):
    """Expose the real MyAssistant brain to the transparent HUD."""

    commandFinished = Signal(str)
    voiceFinished = Signal(str)

    def __init__(self, window):
        super().__init__()
        self.window = window

    def _run_command_worker(self, command):
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

            # Use the real TTS engine when available. Only human-facing
            # Assistant lines are spoken.
            speech_lines = []
            for line in output.splitlines():
                line = line.strip()
                if line.lower().startswith("assistant:"):
                    speech_lines.append(line[len("assistant:"):].strip())

            if speech_lines and hasattr(jarvis, "speak_text_async"):
                jarvis.speak_text_async(" ".join(speech_lines))

            self.commandFinished.emit(output)

        except Exception as error:
            self.commandFinished.emit(f"Assistant error: {error}")

    @Slot(str, result=str)
    def runCommand(self, command):
        threading.Thread(
            target=self._run_command_worker,
            args=(command,),
            daemon=True,
        ).start()
        return "__COMMAND_STARTED__"

    def _listen_voice_worker(self):
        try:
            text = jarvis.listen_for_voice()
            self.voiceFinished.emit(str(text or ""))
        except Exception as error:
            self.voiceFinished.emit(f"__VOICE_ERROR__:{error}")

    @Slot(result=str)
    def listenForVoice(self):
        threading.Thread(
            target=self._listen_voice_worker,
            daemon=True,
        ).start()
        return "__VOICE_STARTED__"

    @Slot(result=str)
    def closeApp(self):
        try:
            self.window.close()
        except Exception:
            QApplication.quit()
        return "closed"


class AssistantWindow(QWebEngineView):
    """Frameless transparent HUD window."""
    pass


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL, True)

    window = AssistantWindow()
    window.setWindowTitle("MyAssistant")
    window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    window.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
    window.setWindowFlags(
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
    )
    window.setStyleSheet("background: transparent; border: none;")

    page = TransparentWebEnginePage(window)
    window.setPage(page)

    bridge = WindowBridge(window)
    assistant = AssistantBridge(window)

    channel = QWebChannel(page)
    channel.registerObject("bridge", bridge)
    channel.registerObject("assistant", assistant)
    page.setWebChannel(channel)

    window.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
    window.resize(360, 250)

    # Start in the upper-left corner with a 20 px margin.
    screen = app.primaryScreen()
    if screen:
        available = screen.availableGeometry()
        margin = 20
        x = available.left() + margin
        y = available.top() + margin
        window.move(x, y)

    window.show()
    page.setBackgroundColor(QColor(0, 0, 0, 0))
    page.setHtml(HTML, QUrl("about:blank"))

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
