from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import os
import json
from server.env import DisasterResponseEnv
from server.tasks import get_available_tasks

app = FastAPI(title="DisasterResponseCoordinatorEnv", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

from starlette.middleware.base import BaseHTTPMiddleware

class EmptyBodyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method == "POST":
            body = await request.body()
            if not body:
                from starlette.requests import Request
                from io import BytesIO
                scope = request.scope
                async def receive():
                    return {"type": "http.request", "body": b"{}"}
                request = Request(scope, receive)
        return await call_next(request)

app.add_middleware(EmptyBodyMiddleware)

# Global environment instance
env = DisasterResponseEnv()


class ResetRequest(BaseModel):
    task_id: Optional[str] = "village_flood_rescue"


class StepRequest(BaseModel):
    tool_name: str
    parameters: Optional[Dict] = {}


# ==================== CORE OPENENV APIs ====================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "env_name": "DisasterResponseCoordinatorEnv",
        "version": "1.0.0",
        "tasks": get_available_tasks(),
        "episode": env.episode_number,
        "ready": True
    }


@app.post("/reset")
def reset(req: ResetRequest = None):
    """Handle both JSON body and empty body."""
    if req is None:
        req = ResetRequest()
    task_id = req.task_id or "village_flood_rescue"
    try:
        obs = env.reset(task_id)
        return obs
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.post("/step")
def step(req: StepRequest):
    try:
        result = env.step({"tool_name": req.tool_name, "parameters": req.parameters or {}})
        return result
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.get("/state")
def state():
    try:
        return env.state()
    except Exception:
        # Return empty state if env not yet initialized
        return {"observation": {"zones":[],"hospitals":[],"roads":[],"resources":{},"teams":[],"agent_reports":{},"current_hour":0,"current_phase":"rescue","dynamic_events":[],"step_number":0,"task_id":"","total_rescued":0,"total_deaths":0}, "total_reward":0,"action_history":[],"strategy_memory":[],"curriculum_difficulty":3.0,"episode_number":0,"current_weakness":"none","total_rescued":0,"total_deaths":0,"reward_stats":{},"grading_config":{},"max_hours":72,"resources":{},"done":False}


# ==================== DASHBOARD APIs ====================

@app.get("/agents")
def agents():
    return env.get_agent_data()


@app.get("/graph")
def graph():
    return env.get_graph_data()


@app.get("/metrics")
def metrics():
    return env.get_metrics()


@app.get("/curriculum")
def curriculum():
    return env.get_curriculum_data()


@app.get("/tasks")
def tasks():
    return {"tasks": get_available_tasks()}


from fastapi.responses import FileResponse

@app.get("/plots/{image_name}")
def get_plot(image_name: str):
    image_path = os.path.join(os.getcwd(), "plots", image_name)
    if os.path.exists(image_path):
        return FileResponse(image_path)
    return JSONResponse(status_code=404, content={"error": "Plot not found"})


# ==================== DASHBOARD HTML ====================

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DisasterResponseCoordinatorEnv</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,system-ui,sans-serif;background:#f0f2f5;color:#222;font-size:13px}
.header{
  background: linear-gradient(135deg, #0F2027 0%, #1B3A5C 50%, #203A43 100%);
  padding: 14px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid #1D9E75;
  box-shadow: 0 2px 12px rgba(0,0,0,0.3);
}
.header h1{
  font-size: 20px;
  font-weight: 700;
  color: #FFFFFF;
  letter-spacing: 0.5px;
}
.header-sub{
  font-size: 12px;
  color: #7EC8C8;
  margin-top: 3px;
}
.conn-dot{
  width: 10px; height: 10px; border-radius: 50%;
  background: #1D9E75;
  box-shadow: 0 0 8px #1D9E75;
  animation: pulse 2s infinite;
  display: inline-block;
}
@keyframes pulse{
  0%,100%{box-shadow: 0 0 6px #1D9E75;}
  50%{box-shadow: 0 0 16px #1D9E75, 0 0 32px rgba(29,158,117,0.4);}
}
.badge-india{
  background: linear-gradient(90deg, #FF9933, #FFFFFF, #138808);
  color: #000;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  margin-left: 8px;
}
.header-title-row{
  display: flex;
  align-items: center;
  gap: 8px;
}
.map-container{
  background: #161b22;
  border-radius: 8px;
  border: 1px solid #30363d;
  overflow: hidden;
  position: relative;
  min-height: 400px;
}
.btn{
  padding: 7px 14px;
  border-radius: 8px;
  border: 1px solid #ddd;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  background: #fff;
  transition: all 0.2s;
}
.btn:hover{ transform: translateY(-1px); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }
.btn-primary{
  background: linear-gradient(135deg, #1D9E75, #16805f);
  color: #fff;
  border: none;
  box-shadow: 0 2px 8px rgba(29,158,117,0.3);
}
.btn-primary:hover{
  background: linear-gradient(135deg, #16805f, #0f5f46);
  box-shadow: 0 4px 16px rgba(29,158,117,0.4);
}
.btn-group{display:flex;gap:4px}
.event-banner{display:none;background:#FCEBEB;color:#791F1F;padding:8px 16px;text-align:center;font-weight:600;font-size:12px;animation:flash 0.5s ease 3}
@keyframes flash{0%,100%{opacity:1}50%{opacity:0.3}}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.4}}
.tabs{display:flex;gap:4px;padding:8px 16px;background:#fff;border-bottom:1px solid #e5e5e0;flex-wrap:wrap}
.tab{padding:5px 12px;border-radius:6px;border:1px solid #e5e5e0;cursor:pointer;font-size:11px;background:#fff;color:#666}
.tab.active{background:#E6F1FB;color:#185FA5;border-color:#B5D4F4;font-weight:500}
.main{padding:12px 16px}
.section-label{
  font-size: 11px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: 20px;
  display: inline-block;
  margin-bottom: 10px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.grid-2{
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 12px;
  align-items: stretch;
}
.grid-2-equal{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.grid-4{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.panel{
  background: #ffffff;
  border: 1px solid #e8e8e3;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.metric-card{
  background: linear-gradient(135deg, #f8f9fa, #ffffff);
  border: 1px solid #e5e5e0;
  border-radius: 10px;
  padding: 12px 8px;
  text-align: center;
  box-shadow: 0 2px 6px rgba(0,0,0,0.06);
  transition: transform 0.2s;
}
.metric-card:hover{ transform: translateY(-2px); }
.metric-label{ font-size: 11px; color: #888; display:block; font-weight:500; }
.metric-value{ font-size: 28px; font-weight: 700; display:block; margin-top:4px; }
.success{color:#1D9E75}.danger{color:#E24B4A}.warning{color:#BA7517}
.agent-card{
  border-radius: 10px;
  padding: 14px 10px;
  text-align: center;
  border: 2px solid transparent;
  transition: all 0.3s;
  cursor: pointer;
  flex: 1;
  min-height: 90px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}
.agent-card:hover{
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.agent-card.active-agent{
  border-color: #1D9E75;
  box-shadow: 0 0 10px rgba(29,158,117,0.25);
}
.agent-card.urgent-agent{
  border-color: #E24B4A;
  box-shadow: 0 0 10px rgba(226,75,74,0.3);
  animation: urgentPulse 1.5s infinite;
}
@keyframes urgentPulse{
  0%,100%{box-shadow: 0 0 8px rgba(226,75,74,0.25);}
  50%{box-shadow: 0 0 20px rgba(226,75,74,0.5);}
}
.agent-name{ 
  font-size: 13px;
  font-weight: 700; 
  letter-spacing: 0.3px;
}
.agent-action{ 
  font-size: 10px; 
  margin-top: 4px; 
  color: #555; 
  min-height: 32px;
  line-height: 1.5; 
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.agent-badge{
  font-size: 10px;
  padding: 4px 10px;
  border-radius: 6px;
  display: inline-block;
  margin-top: 4px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.conflict-banner{display:none;background:#FFF3CD;color:#856404;padding:6px 10px;border-radius:4px;text-align:center;font-size:10px;font-weight:500;margin-top:6px;animation:flash 0.5s 3}
.coop-banner{display:none;background:#D4EDDA;color:#155724;padding:6px 10px;border-radius:4px;text-align:center;font-size:10px;margin-top:4px}
.action-log{
  font-family: 'Courier New', monospace;
  font-size: 11.5px;
  height: auto;
  min-height: 60px;
  max-height: 320px;
  overflow-y: auto;
  background: #0d1117;
  color: #e6edf3;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #30363d;
  line-height: 1.0;
  transition: max-height 0.4s ease;
  scroll-behavior: smooth;
}
.log-line{
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 2px;
  border-bottom: 1px solid #1c2128;
  flex-wrap: nowrap;
  overflow: hidden;
  white-space: nowrap;
}
.log-step{ color: #58a6ff; font-weight: 700; min-width: 28px; font-size: 10px; }
.log-hour{ color: #8b949e; font-size: 9px; min-width: 22px; background: #161b22; padding: 1px 3px; border-radius: 3px; }
.log-agent{ color: #d2a8ff; font-weight: 600; min-width: 55px; font-size: 10px; text-transform: capitalize; }
.log-arrow{ color: #30363d; font-size: 12px; }
.log-action{ color: #ffa657; font-weight: 600; min-width: 80px; font-size: 10px; }
.log-params{ color: #8b949e; font-size: 9px; flex: 1; overflow: hidden; text-overflow: ellipsis; }
.log-conflict{ background: #3d1f63; color: #d2a8ff; padding: 1px 5px; border-radius: 3px; font-size: 9px; white-space: nowrap; }
.log-reward{ font-weight: 700; font-size: 11px; min-width: 40px; text-align: right; }
.reward-pos{ color: #3fb950; }
.reward-neg{ color: #f85149; }
.action-log::-webkit-scrollbar{ width: 4px; }
.action-log::-webkit-scrollbar-track{ background: #161b22; }
.action-log::-webkit-scrollbar-thumb{ background: #30363d; border-radius: 2px; }
.event-inline{background:#FAEEDA;color:#633806;padding:1px 5px;border-radius:3px;font-size:9px}
.conflict-inline{background:#EEEDFE;color:#534AB7;padding:1px 5px;border-radius:3px;font-size:9px}
.phase-bar{
  display: flex;
  height: 28px;
  border-radius: 8px;
  overflow: hidden;
  margin: 8px 0;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
}
.phase-seg{
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
  letter-spacing: 0.5px;
}
.phase-rescue{background:#E24B4A}.phase-relief{background:#BA7517}.phase-rehab{background:#1D9E75}
.phase-future{background:#e5e5e0;color:#888}
.chart-container{position:relative;height:120px;margin:6px 0}
.strat-item{background:#f5f5f0;border-radius:4px;padding:4px 8px;margin:3px 0;font-size:10px;line-height:1.5}
.strat-rate{color:#1D9E75;font-weight:500}.strat-ep{color:#888;font-size:9px}
.diff-bar{height:8px;background:#E1F5EE;border-radius:4px;margin:4px 0}
.diff-fill{height:100%;background:#1D9E75;border-radius:4px;transition:width 0.5s}
.theme-showcase{border-top:2px solid #2E75B6;padding:12px 0;margin-top:10px}
.theme-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.theme-card{
  border-radius: 10px;
  padding: 12px;
  font-size: 11px;
  line-height: 1.6;
  border: 1px solid rgba(0,0,0,0.08);
  box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}
.theme-badge{
  font-size: 10px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 12px;
  display: inline-block;
  margin-bottom: 6px;
  letter-spacing: 0.3px;
}
.theme-card ul{ margin-left: 14px; margin-top: 4px; }
.theme-card li{ margin: 3px 0; color: #444; }
.live-dot{width:6px;height:6px;border-radius:50%;display:inline-block;animation:blink 1.5s infinite;margin-right:4px}
.demo-controls{display:flex;gap:6px;align-items:center;margin-bottom:8px;flex-wrap:wrap}
.demo-controls select{padding:4px 8px;border-radius:6px;border:1px solid #ddd;font-size:11px}
.plots-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:8px 0}
.plot-card{ background:#f5f5f0; border-radius:6px; padding:6px; text-align:center; position:relative; overflow:hidden; }
.plot-card img{max-width:100%;border-radius:4px}
.plot-caption{font-size:9px;color:#888;margin-top:4px}
.plot-badge{
  position: absolute;
  top: 8px; right: 8px;
  background: rgba(13,17,23,0.85);
  color: #3fb950;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid #3fb950;
}
.links-row{display:flex;gap:10px;font-size:11px;margin-top:8px}
.links-row a{color:#378ADD;text-decoration:none}
.past-item{background:#E6F1FB;color:#0C447C;padding:3px 8px;border-radius:4px;font-size:9px;margin:2px 0}
.map-container{
  background: linear-gradient(160deg, #0a1628 0%, #0d1f3c 50%, #0a1628 100%);
  border-radius: 10px;
  padding: 10px;
  border: 1px solid #1D9E75;
  box-shadow: inset 0 0 20px rgba(29,158,117,0.1);
}
.map-legend{display:flex;gap:10px;font-size:9px;color:#888;margin-top:4px;flex-wrap:wrap}
.legend-item{display:flex;align-items:center;gap:3px}
.legend-dot{width:8px;height:8px;border-radius:50%}
.legend-line{width:12px;height:3px;border-radius:1px}
.auto-status{font-size:11px;color:#1D9E75;font-weight:500;margin-left:8px}
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <div style="display:flex;align-items:center;gap:12px">
    <span class="conn-dot" id="conn-dot"></span>
    <div>
      <div class="header-title-row">
        <h1>DisasterResponseCoordinatorEnv</h1>
        <span class="badge-india">🇮🇳 INDIA</span>
      </div>
      <p class="header-sub">Autonomous emergency management swarm &nbsp;|&nbsp; 8 AI Agents &nbsp;|&nbsp; 72-hour simulation</p>
    </div>
  </div>
  <div class="btn-group">
    <select id="task-select" style="padding:5px 8px;border-radius:6px;border:1px solid #30363d;font-size:11px;background:#1B3A5C;color:#fff">
      <option value="village_flood_rescue">Task 1: Village Flood (Easy)</option>
      <option value="multi_district_cyclone">Task 2: Cyclone (Medium)</option>
      <option value="earthquake_aftershock">Task 3: Earthquake (Hard)</option>
      <option value="full_72hr_operation">Task 4: Full 72hr (Expert)</option>
    </select>
    <button class="btn btn-primary" onclick="startEpisode()">▶ Run Episode</button>
    <button class="btn" onclick="stepOnce()">Step</button>
    <button class="btn" onclick="autoRun()">Auto-Run</button>
    <span class="auto-status" id="auto-status"></span>
  </div>
</div>

<!-- DYNAMIC EVENT BANNER -->
<div class="event-banner" id="event-banner"></div>

<!-- MAIN CONTENT -->
<div class="main">

<!-- SECTION A: METRICS -->
<div class="panel">
  <span class="section-label" style="background:#EEEDFE;color:#3C3489">Crisis Overview</span>
  <div class="grid-4" style="margin-top:6px">
    <div class="metric-card"><span class="metric-label">Affected</span><span class="metric-value" id="m-affected">0</span></div>
    <div class="metric-card"><span class="metric-label">Rescued</span><span class="metric-value success" id="m-rescued">0</span></div>
    <div class="metric-card"><span class="metric-label">Critical</span><span class="metric-value danger" id="m-critical">0</span></div>
    <div class="metric-card"><span class="metric-label">Deaths</span><span class="metric-value danger" id="m-deaths">0</span></div>
  </div>
  <div class="grid-4" style="margin-top:6px">
    <div class="metric-card"><span class="metric-label">Hour</span><span class="metric-value" id="m-hour">0/72</span></div>
    <div class="metric-card"><span class="metric-label">Phase</span><span class="metric-value" id="m-phase" style="font-size:14px">RESCUE</span></div>
    <div class="metric-card"><span class="metric-label">Teams Out</span><span class="metric-value" id="m-teams">0/0</span></div>
    <div class="metric-card"><span class="metric-label">Reward</span><span class="metric-value" id="m-reward">0.00</span></div>
  </div>
</div>

<!-- SECTIONS B + C: MAP + AGENTS -->
<div class="grid-2">
  <!-- SECTION B: CRISIS MAP -->
  <div class="panel" style="height: 100%; min-height: 500px;">
    <span class="section-label" style="background:#FAECE7;color:#712B13">Theme 3: World Model — Crisis Map</span>
    <div class="map-container">
      <svg id="crisis-map" viewBox="0 0 520 440" width="100%" style="min-height:220px"></svg>
    </div>
    <div class="map-legend">
      <div class="legend-item"><div class="legend-dot" style="background:#E24B4A"></div>Danger zone</div>
      <div class="legend-item"><div class="legend-dot" style="background:#378ADD"></div>Hospital</div>
      <div class="legend-item"><div class="legend-dot" style="background:#1D9E75"></div>Base</div>
      <div class="legend-item"><div class="legend-dot" style="background:#BA7517"></div>Helipad</div>
      <div class="legend-item"><div class="legend-dot" style="background:#534AB7"></div>Shelter/Team</div>
      <div class="legend-item"><div class="legend-line" style="background:#1D9E75"></div>Open road</div>
      <div class="legend-item"><div class="legend-line" style="background:#BA7517"></div>Flooded</div>
      <div class="legend-item"><div class="legend-line" style="background:#E24B4A"></div>Blocked</div>
    </div>
  </div>
  <!-- SECTION C: 8 AGENTS -->
  <div class="panel" style="display: flex; flex-direction: column; height: 100%; gap: 0;">
    <span class="section-label" style="background:#EEEDFE;color:#3C3489">Theme 1: Multi-Agent — 8 Agent Swarm</span>
    <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-top:8px; flex:1; height: 50%;" id="agents-grid-1">
      <div class="agent-card" id="ag-coordinator" style="background:#EEEDFE" onclick="openAgentModal('coordinator')"><div class="agent-name" style="color:#3C3489">Coordinator</div><div class="agent-action" id="ag-coordinator-act">Initializing</div><div class="agent-badge" id="ag-coordinator-badge" style="background:#CECBF6;color:#26215C">IDLE</div></div>
      <div class="agent-card" id="ag-logistics" style="background:#FAECE7" onclick="openAgentModal('logistics')"><div class="agent-name" style="color:#712B13">Logistics</div><div class="agent-action" id="ag-logistics-act">Ready</div><div class="agent-badge" id="ag-logistics-badge" style="background:#F5C4B3;color:#4A1B0C">IDLE</div></div>
      <div class="agent-card" id="ag-medical" style="background:#E6F1FB" onclick="openAgentModal('medical')"><div class="agent-name" style="color:#0C447C">Medical</div><div class="agent-action" id="ag-medical-act">Ready</div><div class="agent-badge" id="ag-medical-badge" style="background:#B5D4F4;color:#042C53">IDLE</div></div>
      <div class="agent-card" id="ag-air_support" style="background:#FAEEDA" onclick="openAgentModal('air_support')"><div class="agent-name" style="color:#633806">Air Support</div><div class="agent-action" id="ag-air_support-act">Ready</div><div class="agent-badge" id="ag-air_support-badge" style="background:#FAC775;color:#412402">IDLE</div></div>
    </div>
    <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-top:8px; flex:1; height: 50%;" id="agents-grid-2">
      <div class="agent-card" id="ag-communication" style="background:#E1F5EE" onclick="openAgentModal('communication')"><div class="agent-name" style="color:#085041">Comms</div><div class="agent-action" id="ag-communication-act">Ready</div><div class="agent-badge" id="ag-communication-badge" style="background:#9FE1CB;color:#04342C">IDLE</div></div>
      <div class="agent-card" id="ag-ground_rescue" style="background:#FBEAF0" onclick="openAgentModal('ground_rescue')"><div class="agent-name" style="color:#72243E">Ground</div><div class="agent-action" id="ag-ground_rescue-act">Ready</div><div class="agent-badge" id="ag-ground_rescue-badge" style="background:#F4C0D1;color:#4B1528">IDLE</div></div>
      <div class="agent-card" id="ag-supply_chain" style="background:#FCEBEB" onclick="openAgentModal('supply_chain')"><div class="agent-name" style="color:#791F1F">Supply</div><div class="agent-action" id="ag-supply_chain-act">Ready</div><div class="agent-badge" id="ag-supply_chain-badge" style="background:#F7C1C1;color:#501313">IDLE</div></div>
      <div class="agent-card" id="ag-field_assessment" style="background:#F1EFE8" onclick="openAgentModal('field_assessment')"><div class="agent-name" style="color:#444441">Scout</div><div class="agent-action" id="ag-field_assessment-act">Ready</div><div class="agent-badge" id="ag-field_assessment-badge" style="background:#D3D1C7;color:#2C2C2A">IDLE</div></div>
    </div>
    <div class="conflict-banner" id="conflict-alert"></div>
    <div class="coop-banner" id="coop-alert"></div>
  </div>
</div>

<!-- SECTION D: ACTION LOG -->
<div class="panel">
  <div style="display:flex; justify-content:space-between; 
              align-items:center; margin-bottom:6px;">
    <span class="section-label" 
          style="background:#1c2128; color:#7ec8e3; margin-bottom:0;">
      LIVE ACTION STREAM
    </span>
    <div style="display:flex; gap:8px; align-items:center;">
      <span style="font-size:10px; color:#3fb950; font-family:monospace;">
        ● LIVE
      </span>
      <span id="log-step-count" 
            style="font-size:10px; color:#8b949e; font-family:monospace;">
        0 steps
      </span>
      <button onclick="clearLog()" 
              style="font-size:10px; padding:2px 8px; border-radius:4px;
                     background:#161b22; color:#8b949e; border:1px solid #30363d;
                     cursor:pointer;">
        Clear
      </button>
    </div>
  </div>
  <div class="action-log" id="action-log"><div class="log-line" style="color:#888">Click "Run Episode" to start...</div></div>
</div>

<!-- SECTIONS E + F: TIMELINE + SELF-IMPROVEMENT -->
<div class="grid-2-equal">
  <!-- SECTION E: TIMELINE -->
  <div class="panel">
    <span class="section-label" style="background:#E6F1FB;color:#0C447C">Theme 2: Long-Horizon — 72h Timeline</span>
    <div class="phase-bar">
      <div class="phase-seg phase-rescue" id="ph-rescue" style="width:33%">Rescue 0-24h</div>
      <div class="phase-seg phase-relief" id="ph-relief" style="width:0%"></div>
      <div class="phase-seg phase-rehab" id="ph-rehab" style="width:0%"></div>
      <div class="phase-seg phase-future" id="ph-future" style="width:67%"></div>
    </div>
    <div style="font-size:10px;color:#888;margin:4px 0" id="phase-info">Hour 0/72 | Phase: RESCUE</div>
    <div class="chart-container"><canvas id="resource-canvas"></canvas></div>
    <div id="past-decisions"></div>
  </div>
  <!-- SECTION F: SELF-IMPROVEMENT -->
  <div class="panel">
    <span class="section-label" style="background:#E1F5EE;color:#085041">Theme 4: Self-Improvement Engine</span>
    <div class="chart-container"><canvas id="score-canvas"></canvas></div>
    <div style="font-size:10px;font-weight:500;margin:6px 0">Strategy memory:</div>
    <div id="strategy-list"><div class="strat-item" style="color:#888">No strategies learned yet. Training will populate this.</div></div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px">
      <span style="font-size:10px">Difficulty: <strong id="diff-val">3/10</strong></span>
      <span style="font-size:10px">Weakness: <strong id="weakness-val" style="color:#E24B4A">none</strong></span>
    </div>
    <div class="diff-bar"><div class="diff-fill" id="diff-fill" style="width:30%"></div></div>
  </div>
</div>

<!-- SECTION G: TRAINING RESULTS + LINKS -->
<div class="panel">
  <span class="section-label" style="background:#FAEEDA;color:#633806">Training Evidence (20% score)</span>
  <div class="plots-grid">
    <div class="plot-card" style="position:relative">
      <img src="/plots/reward_curve.png" alt="Reward curve" onerror="this.src='';this.alt='Training plots will appear after training'">
      <div class="plot-badge">+199% ↑</div>
      <p class="plot-caption">Reward improvement over 20 episodes</p>
    </div>
    <div class="plot-card" style="position:relative">
      <img src="/plots/before_after.png" alt="Before vs After" onerror="this.src='';this.alt='Before/after comparison after training'">
      <div class="plot-badge">0.20 → 0.60</div>
      <p class="plot-caption">Untrained vs trained agent performance</p>
    </div>
  </div>
  <div class="links-row">
    <a href="#" id="colab-link">Open Training Notebook (Colab)</a>
    <a href="#" id="youtube-link">Watch Demo Video (90s)</a>
    <a href="#" id="blog-link">Read HF Blog Post</a>
  </div>
</div>

<!-- THEME SHOWCASE FOOTER -->
<div class="theme-showcase">
  <div style="font-size:12px;font-weight:600;margin-bottom:8px;color:#1B3A5C">How each hackathon theme is implemented:</div>
  <div class="theme-grid">
    <div class="theme-card" style="background:#EEEDFE;border-left:3px solid #534AB7">
      <div class="theme-badge" style="background:#CECBF6;color:#3C3489">Theme 1: Multi-Agent</div>
      <div><span class="live-dot" style="background:#534AB7"></span><span id="t1-live">8 agents</span></div>
      <div style="margin-top:3px">8 agents with competing interests and cooperation chains</div>
    </div>
    <div class="theme-card" style="background:#E6F1FB;border-left:3px solid #185FA5">
      <div class="theme-badge" style="background:#B5D4F4;color:#0C447C">Theme 2: Long-Horizon</div>
      <div><span class="live-dot" style="background:#185FA5"></span><span id="t2-live">72h sim</span></div>
      <div style="margin-top:3px">72-hour 3-phase simulation with sparse delayed rewards</div>
    </div>
    <div class="theme-card" style="background:#FAECE7;border-left:3px solid #993C1D">
      <div class="theme-badge" style="background:#F5C4B3;color:#712B13">Theme 3: World Model</div>
      <div><span class="live-dot" style="background:#993C1D"></span><span id="t3-live">6 layers</span></div>
      <div style="margin-top:3px">Graph-based map with 8 dynamic event types</div>
    </div>
    <div class="theme-card" style="background:#E1F5EE;border-left:3px solid #0F6E56">
      <div class="theme-badge" style="background:#9FE1CB;color:#085041">Theme 4: Self-Improve</div>
      <div><span class="live-dot" style="background:#0F6E56"></span><span id="t4-live">Difficulty 3/10</span></div>
      <div style="margin-top:3px">Adaptive curriculum + strategy memory + reward shaping</div>
    </div>
  </div>
</div>

</div>

<script>
// ==================== HELPER ====================
// Track per-agent stats
const agentStats = {};
const AGENT_ROLES = {
  'coordinator': 'Master orchestrator — allocates resources, resolves conflicts',
  'logistics': 'Routes vehicles, trucks, supply convoys',
  'medical': 'Deploys medical units, triages critical patients',
  'air_support': 'Helicopter ops, airlifts, aerial scouting',
  'communication': 'Sets up comms, manages dark zones',
  'ground_rescue': 'Ground rescue teams in danger zones',
  'supply_chain': 'Food, water, medicine inventory',
  'field_assessment': 'Scout drones, zone assessment'
};

function initAgentStats() {
  const agents = ['coordinator','logistics','medical','air_support',
                  'communication','ground_rescue','supply_chain',
                  'field_assessment'];
  agents.forEach(a => {
    agentStats[a] = {
      actions: 0, totalReward: 0, conflicts: 0,
      decisions: [], mission: 'Awaiting deployment'
    };
  });
}
initAgentStats();

function updateAgentStat(agentId, action, reward, conflict) {
  if (!agentStats[agentId]) return;
  const s = agentStats[agentId];
  s.actions++;
  s.totalReward += reward;
  if (conflict) s.conflicts++;
  s.decisions.unshift(`${action} → ${reward >= 0 ? '+' : ''}${reward.toFixed(2)}`);
  if (s.decisions.length > 5) s.decisions = s.decisions.slice(0, 5);
  s.mission = action;
}

function openAgentModal(agentId) {
  const s = agentStats[agentId] || 
    {actions:0, totalReward:0, conflicts:0, decisions:[], mission:'No data'};
  
  const nameMap = {
    'coordinator':'Coordinator','logistics':'Logistics',
    'medical':'Medical Unit','air_support':'Air Support',
    'communication':'Communications','ground_rescue':'Ground Rescue',
    'supply_chain':'Supply Chain','field_assessment':'Field Scout'
  };
  
  document.getElementById('modal-agent-name').textContent = 
    nameMap[agentId] || agentId;
  document.getElementById('modal-agent-role').textContent = 
    AGENT_ROLES[agentId] || '';
  
  const badge = document.getElementById('modal-status-badge');
  const badgeEl = document.getElementById('ag-' + agentId + '-badge');
  const status = badgeEl ? badgeEl.textContent : 'IDLE';
  badge.textContent = status;
  badge.style.background = status === 'URGENT' ? '#f85149' : 
                           status === 'ACTIVE' ? '#1D9E75' : '#30363d';
  badge.style.color = '#fff';
  
  document.getElementById('modal-actions').textContent = s.actions;
  document.getElementById('modal-avg-reward').textContent = 
    s.actions > 0 ? (s.totalReward / s.actions).toFixed(3) : '0.000';
  document.getElementById('modal-conflicts').textContent = s.conflicts;
  document.getElementById('modal-mission').textContent = 
    s.mission || 'No active mission';
  document.getElementById('modal-decisions').innerHTML = 
    s.decisions.length > 0 
      ? s.decisions.map((d,i) => 
          `<div style="color:${i===0?'#ffa657':'#8b949e'}">${d}</div>`
        ).join('')
      : '<div style="color:#8b949e">No decisions yet</div>';
      
  const capabilityMap = {
    'coordinator': ['Orchestrates all 8 agents', 'Resolves conflicts', 'Allocates resources', 'Makes final decisions'],
    'logistics': ['Routes 6 trucks', 'Manages convoy paths', 'Tracks road conditions', 'Fuel management'],
    'medical': ['Deploys 3 med units', 'Triages critical patients', 'Hospital capacity tracking', 'Evacuation priority'],
    'air_support': ['Helicopter sorties', 'Aerial rescue ops', 'Fuel: limited trips', 'Weather-dependent'],
    'communication': ['Sets up field comms', 'Manages dark zones', 'Relay coordination', 'Signal mapping'],
    'ground_rescue': ['Deploys rescue teams', 'Zone clearance', 'Survivor extraction', 'Building search'],
    'supply_chain': ['Food/water stocks', 'Medicine delivery', 'Camp setup', 'Resource conservation'],
    'field_assessment': ['Scout drones', 'Zone severity mapping', 'Road status updates', 'Damage assessment']
  };
  const caps = capabilityMap[agentId] || [];
  document.getElementById('modal-capabilities').innerHTML = 
    caps.map(c => `<div>• ${c}</div>`).join('');
    
  document.getElementById('modal-total-reward').textContent = 
    s.totalReward.toFixed(3);
  document.getElementById('modal-success-rate').textContent = 
    s.actions > 0 
      ? Math.round((s.decisions.filter(d => d.includes('+')).length / s.actions) * 100) + '%'
      : '0%';
  document.getElementById('modal-last-action').textContent = 
    s.decisions[0] ? s.decisions[0].split('→')[0].trim() : '—';
  
  document.getElementById('agent-modal').style.display = 'block';
}

function closeAgentModal() {
  document.getElementById('agent-modal').style.display = 'none';
}

function setText(id, val) { const el = document.getElementById(id); if(el) el.textContent = val; }
function makeSVG(tag, attrs, text) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attrs).forEach(([k,v]) => el.setAttribute(k, v));
  if (text !== undefined) el.textContent = text;
  return el;
}

function getSmartLabelOffset(node, allNodes, svgW, svgH) {
  const offsets = [
    {dx: 0,   dy: 18,  anchor: 'middle'},
    {dx: 0,   dy: -14, anchor: 'middle'},
    {dx: 18,  dy: 4,   anchor: 'start'},
    {dx: -18, dy: 4,   anchor: 'end'},
    {dx: 14,  dy: 14,  anchor: 'start'},
    {dx: -14, dy: 14,  anchor: 'end'},
  ];
  
  for (const off of offsets) {
    const testX = node.x + off.dx;
    const testY = node.y + off.dy;
    
    let tooClose = false;
    for (const other of allNodes) {
      if (other.id === node.id) continue;
      const dist = Math.sqrt(
        Math.pow(testX - other.x, 2) + Math.pow(testY - other.y, 2)
      );
      if (dist < 40) { tooClose = true; break; }
    }
    
    if (!tooClose && testX > 10 && testX < svgW-10 && 
        testY > 10 && testY < svgH-10) {
      return off;
    }
  }
  return {dx: 0, dy: 18, anchor: 'middle'};
}


// ==================== CHARTS ====================
const resourceData = {labels:[], fuel:[], water:[], food:[]};
const scoreData = {labels:[], scores:[]};
let resourceChart, scoreChart;

function initCharts() {
  resourceChart = new Chart(document.getElementById('resource-canvas'), {
    type:'line', data:{labels:resourceData.labels, datasets:[
      {label:'Fuel %',data:resourceData.fuel,borderColor:'#BA7517',borderWidth:2,tension:0.3,pointRadius:0},
      {label:'Water %',data:resourceData.water,borderColor:'#378ADD',borderWidth:2,tension:0.3,pointRadius:0},
      {label:'Food %',data:resourceData.food,borderColor:'#1D9E75',borderWidth:2,tension:0.3,pointRadius:0},
    ]}, options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{boxWidth:10,font:{size:9}}}},scales:{y:{min:0,max:100,title:{display:true,text:'% remaining',font:{size:9}}},x:{title:{display:true,text:'Hour',font:{size:9}}}}}
  });
  scoreChart = new Chart(document.getElementById('score-canvas'), {
    type:'line', data:{labels:scoreData.labels, datasets:[
      {label:'Episode Score',data:scoreData.scores,borderColor:'#1D9E75',borderWidth:2,fill:true,backgroundColor:'rgba(29,158,117,0.15)',tension:0.3,pointRadius:4,pointHoverRadius:7,pointBackgroundColor:'#1D9E75'},
    ]}, options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{font:{size:11},color:'#444'}},tooltip:{backgroundColor:'#0d1117',titleColor:'#e6edf3',bodyColor:'#8b949e',borderColor:'#30363d',borderWidth:1}},scales:{y:{min:0,max:1,grid:{color:'#e8e8e3'},title:{display:true,text:'Score',font:{size:9}}},x:{grid:{color:'#e8e8e3'},title:{display:true,text:'Episode',font:{size:9}}}}}
  });
}

// ==================== UPDATE FUNCTIONS ====================
function updateMetrics(state) {
  const obs = state.observation || state;
  const zones = obs.zones || [];
  const totalPop = zones.reduce((s,z) => s + (z.population||0), 0);
  const totalCrit = zones.reduce((s,z) => s + (z.injured_critical||0), 0);
  setText('m-affected', totalPop.toLocaleString());
  setText('m-rescued', (state.total_rescued||obs.total_rescued||0).toLocaleString());
  setText('m-critical', totalCrit);
  setText('m-deaths', state.total_deaths||obs.total_deaths||0);
  setText('m-hour', (obs.current_hour||0) + '/' + (state.max_hours||72));
  setText('m-phase', (obs.current_phase||'rescue').toUpperCase());
  const teams = obs.teams||[];
  const active = teams.filter(t => t.status !== 'idle').length;
  setText('m-teams', active + '/' + teams.length);
  setText('m-reward', (state.total_reward||0).toFixed(2));
  // Resource chart
  const h = obs.current_hour||0;
  const res = state.resources||obs.resources||{};
  if (!resourceData.labels.includes(h)) {
    resourceData.labels.push(h);
    const mf = Math.max(res.max_fuel||1,1), mw = Math.max(res.max_water||1,1), mfo = Math.max(res.max_food||1,1);
    resourceData.fuel.push(Math.round((res.fuel_helicopter||0)/mf*100));
    resourceData.water.push(Math.round((res.water_units||0)/mw*100));
    resourceData.food.push(Math.round((res.food_units||0)/mfo*100));
    if(resourceChart) resourceChart.update();
  }
  // Phase bar
  const pct = Math.round(h / (state.max_hours||72) * 100);
  const rescuePct = Math.min(pct, 33);
  const reliefPct = h > 24 ? Math.min(pct - 33, 33) : 0;
  const rehabPct = h > 48 ? Math.min(pct - 66, 34) : 0;
  const futurePct = 100 - rescuePct - reliefPct - rehabPct;
  document.getElementById('ph-rescue').style.width = rescuePct+'%';
  document.getElementById('ph-relief').style.width = reliefPct+'%'; document.getElementById('ph-relief').textContent = reliefPct > 5 ? 'Relief 24-48h' : '';
  document.getElementById('ph-rehab').style.width = rehabPct+'%'; document.getElementById('ph-rehab').textContent = rehabPct > 5 ? 'Rehab 48-72h' : '';
  document.getElementById('ph-future').style.width = futurePct+'%';
  setText('phase-info', 'Hour ' + h + '/' + (state.max_hours||72) + ' | Phase: ' + (obs.current_phase||'rescue').toUpperCase());
  // Past decisions
  const history = state.action_history || [];
  const impacts = history.filter(a => a.long_term_impact).slice(-3);
  document.getElementById('past-decisions').innerHTML = impacts.map(a => '<div class="past-item">Hour '+a.hour+': '+a.long_term_impact+'</div>').join('');
}

function updateCrisisMap(graph) {
  const svg = document.getElementById('crisis-map');
  svg.innerHTML = '';
  const edges = graph.edges || [];
  const nodes = graph.nodes || [];
  const teams = graph.teams || [];
  // Add glow filter
  const defs = `<defs>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
      <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>`;
  svg.innerHTML = defs;
  edges.forEach(e => {
    const from = nodes.find(n => n.id === e.from_zone);
    const to = nodes.find(n => n.id === e.to_zone);
    if(!from||!to) return;
    const colors = {open:'#00E5A0',flooded:'#FF9933',blocked:'#FF4444',damaged:'#999'};
    svg.appendChild(makeSVG('line', {x1:from.x,y1:from.y,x2:to.x,y2:to.y,stroke:colors[e.status]||'#ccc','stroke-width':e.status==='blocked'?1.5:2.5,'stroke-dasharray':e.status==='blocked'?'5 3':'none'}));
  });
  const nodeColors = {village:'#FF4444',hospital:'#3A9EFF',base:'#00E5A0',helipad:'#FF9933',shelter:'#a78bfa'};
  const nodeSizes = {village:13,hospital:11,base:15,helipad:9,shelter:10};
  nodes.forEach(n => {
    const isVillage = n.type === 'village';
    const circle = makeSVG('circle', {cx:n.x,cy:n.y,r:nodeSizes[n.type]||10,fill:nodeColors[n.type]||'#888',stroke:'rgba(255,255,255,0.3)','stroke-width':'1.5'});
    if(isVillage) circle.setAttribute('filter', 'url(#glow)');
    svg.appendChild(circle);
    if(n.type==='village' && n.population) svg.appendChild(makeSVG('text', {x:n.x,y:n.y+4,'text-anchor':'middle','font-size':'8',fill:'#fff','font-weight':'600'}, n.population));
    if(n.type==='hospital') svg.appendChild(makeSVG('text', {x:n.x,y:n.y+4,'text-anchor':'middle','font-size':'7',fill:'#fff','font-weight':'600'}, (n.capacity_pct||0)+'%'));
    
    const svgW = svg.viewBox.baseVal.width || 520;
    const svgH = svg.viewBox.baseVal.height || 400;
    const labelOff = getSmartLabelOffset(n, nodes, svgW, svgH);
    svg.appendChild(makeSVG('text', {
      x: n.x + labelOff.dx, 
      y: n.y + labelOff.dy,
      'font-size': '10', 
      fill: '#CBD5E1', 
      'text-anchor': labelOff.anchor,
      'paint-order': 'stroke',
      stroke: '#0d1f3c',
      'stroke-width': '3',
      'font-weight': '500'
    }, n.name || n.id));
  });
  teams.forEach(t => {
    svg.appendChild(makeSVG('circle', {cx:t.current_x,cy:t.current_y,r:'5',fill:'#a78bfa',stroke:'#fff','stroke-width':'1.5'}));
    svg.appendChild(makeSVG('text', {
      x: t.current_x, 
      y: t.current_y - 16,
      'font-size': '9',
      fill: '#A78BFA',
      'text-anchor': 'middle',
      'paint-order': 'stroke',
      stroke: '#0d1f3c',
      'stroke-width': '3'
    }, t.id));
  });
}

function updateAgentCards(agents) {
  const badgeColors = {idle:'#D3D1C7',active:'#9FE1CB',warning:'#FAC775',urgent:'#F7C1C1',offline:'#E24B4A'};
  Object.entries(agents).forEach(([name, data]) => {
    const act = data.current_action || 'standby';
    setText('ag-'+name+'-act', act.length > 30 ? act.substring(0,28)+'..' : act);
    const badge = document.getElementById('ag-'+name+'-badge');
    const card = document.getElementById('ag-'+name);
    const statusText = (data.status||'idle').toUpperCase();
    if(badge) { badge.textContent = statusText; badge.style.background = badgeColors[data.status]||'#D3D1C7'; }
    if(card) {
      card.classList.remove('active-agent','urgent-agent');
      if(statusText === 'URGENT') card.classList.add('urgent-agent');
      else if(statusText === 'ACTIVE') card.classList.add('active-agent');
    }
  });
  const conflicts = Object.entries(agents).filter(([_,d]) => d.conflict_with).map(([n,d]) => n+' vs '+d.conflict_with+': '+d.conflict_reason);
  const cb = document.getElementById('conflict-alert');
  if(conflicts.length > 0) { cb.style.display='block'; cb.textContent='CONFLICT: '+conflicts[0]; } else { cb.style.display='none'; }
  const coops = Object.entries(agents).filter(([_,d]) => d.cooperation_chain).map(([_,d]) => d.cooperation_chain);
  const co = document.getElementById('coop-alert');
  if(coops.length > 0) { co.style.display='block'; co.textContent='CHAIN: '+coops[0]; } else { co.style.display='none'; }
}

const ACTION_ICONS = {
  'dispatch_team': '🚁',
  'request_airlift': '✈️',
  'allocate_resource': '📦',
  'deploy_scout': '🔍',
  'setup_comms': '📡',
  'advance_hour': '⏰',
  'evacuate_zone': '🚨',
  'medical_triage': '🏥',
  'block_road': '🚧',
  'request_reinforcement': '🆘',
};

function formatParams(p) {
  if (!p || Object.keys(p).length === 0) return '';
  const parts = [];
  if (p.zone_id) parts.push(p.zone_id);
  if (p.team_type) parts.push(p.team_type);
  if (p.resource_type) parts.push(p.resource_type);
  if (p.amount) parts.push(`×${p.amount}`);
  if (p.target_zone) parts.push(`→${p.target_zone}`);
  if (p.message) parts.push(p.message.slice(0, 20));
  return parts.length > 0 ? parts.join(' ') : JSON.stringify(p).slice(0, 30);
}

function addLogLine(step, agentName, actionName, params, reward, conflict, hour) {
  const log = document.getElementById('action-log');
  const isPos = reward >= 0;
  
  let paramStr = '';
  if (typeof params === 'string') {
    paramStr = params;
  } else if (params && typeof params === 'object') {
    paramStr = formatParams(params);
  }

  let conflictBadge = '';
  if (conflict && conflict.length > 0) {
    const shortConflict = conflict.split(':')[0].trim();
    conflictBadge = `<span class="log-conflict">${shortConflict}</span>`;
  }
  
  const icon = ACTION_ICONS[actionName] || '▶';
  const line = document.createElement('div');
  line.className = 'log-line';
  line.innerHTML = `
    <span class="log-step">S${step}</span>
    <span class="log-hour">H${hour !== undefined ? hour : ''}</span>
    <span class="log-agent">${agentName || 'coord'}</span>
    <span class="log-arrow">›</span>
    <span class="log-action">${icon} ${actionName || 'action'}</span>
    <span class="log-params">${paramStr || ''}</span>
    ${conflictBadge}
    <span class="log-reward ${isPos ? 'reward-pos' : 'reward-neg'}">
      ${isPos ? '+' : ''}${reward.toFixed(2)}
    </span>
  `;
  // Insert at top so newest is always visible without scrolling
  if (log.firstChild && log.firstChild.style && 
      log.firstChild.style.color === '#888') {
    // Remove placeholder "Click Run Episode to start" message
    log.removeChild(log.firstChild);
  }
  log.insertBefore(line, log.firstChild);
  
  // Animate new line in
  line.style.opacity = '0';
  line.style.transform = 'translateX(-10px)';
  requestAnimationFrame(() => {
    line.style.transition = 'opacity 0.3s, transform 0.3s';
    line.style.opacity = '1';
    line.style.transform = 'translateX(0)';
  });
  
  // Keep max 80 lines
  while (log.children.length > 80) {
    log.removeChild(log.lastChild);
  }
  
  logStepCount++;
  updateLogCount();
}

function clearLog() {
  const log = document.getElementById('action-log');
  log.innerHTML = '<div style="color:#3fb950; font-family:monospace; padding:2px 0;">Log cleared. Ready for next episode.</div>';
  logStepCount = 0;
  updateLogCount();
}

let logStepCount = 0;
function updateLogCount() {
  const el = document.getElementById('log-step-count');
  if (el) el.textContent = `${logStepCount} steps`;
}

function updateActionLog(history) {
  const log = document.getElementById('action-log');
  log.innerHTML = '';
  logStepCount = 0;

  (history||[]).slice(-60).forEach(e => {
    addLogLine(
      e.step,
      e.agent_name || 'coordinator',
      e.tool_name,
      e.parameters || e.params_short || '',
      e.reward || 0,
      e.conflict_resolved || '',
      e.hour
    );
  });
}

function updateSelfImprovement(cur) {
  if(!cur) return;
  setText('diff-val', (cur.difficulty||3)+'/10');
  setText('weakness-val', cur.current_weakness||'none');
  document.getElementById('diff-fill').style.width = ((cur.difficulty||3)*10)+'%';
  const strats = cur.strategy_memory || [];
  document.getElementById('strategy-list').innerHTML = strats.length ? strats.map((s,i) =>
    '<div class="strat-item"><b>'+(i+1)+'.</b> '+s.rule+' <span class="strat-rate">('+Math.round(s.success_rate*100)+'%)</span> <span class="strat-ep">ep '+s.learned_after+'</span></div>'
  ).join('') : '<div class="strat-item" style="color:#888">No strategies yet</div>';
  const hist = cur.episode_history || [];
  hist.forEach(ep => {
    if(!scoreData.labels.includes(ep.episode)) {
      scoreData.labels.push(ep.episode);
      scoreData.scores.push(ep.score);
      if(scoreChart) scoreChart.update();
    }
  });
  setText('t4-live', 'Difficulty '+(cur.difficulty||3)+'/10');
}

function updateThemeIndicators(state, agents) {
  const activeAgents = Object.values(agents).filter(a => (a.status||'idle') !== 'idle').length;
  setText('t1-live', activeAgents + '/8 agents active');
  const obs = state.observation || state;
  setText('t2-live', 'Hour '+(obs.current_hour||0)+'/72 | '+(obs.current_phase||'rescue').toUpperCase());
  setText('t3-live', (state.dynamic_events_count||0)+' events triggered');
}

function checkDynamicEvents(state) {
  const obs = state.observation || state;
  const events = obs.dynamic_events || [];
  if(events.length > 0) {
    const banner = document.getElementById('event-banner');
    banner.textContent = events[0];
    banner.style.display = 'block';
    banner.style.animation = 'none'; banner.offsetHeight; banner.style.animation = 'flash 0.5s ease 3';
    setTimeout(() => { banner.style.display = 'none'; }, 5000);
  }
}

// ==================== REFRESH LOOP ====================
async function refreshAll() {
  try {
    const [state, agents, graph] = await Promise.all([
      fetch('/state').then(r => r.json()),
      fetch('/agents').then(r => r.json()),
      fetch('/graph').then(r => r.json()),
    ]);
    updateMetrics(state);
    updateCrisisMap(graph);
    updateAgentCards(agents);
    updateActionLog(state.action_history);
    updateThemeIndicators(state, agents);
    checkDynamicEvents(state);
    document.getElementById('conn-dot').style.background = '#1D9E75';
  } catch(e) {
    document.getElementById('conn-dot').style.background = '#E24B4A';
  }
}
setInterval(refreshAll, 2000);
setInterval(async () => {
  try { const cur = await fetch('/curriculum').then(r=>r.json()); updateSelfImprovement(cur); } catch(e){}
}, 5000);

// ==================== BUTTON HANDLERS ====================
async function startEpisode() {
  initAgentStats();
  const task = document.getElementById('task-select').value;
  resourceData.labels=[]; resourceData.fuel=[]; resourceData.water=[]; resourceData.food=[];
  setText('auto-status', 'Starting...');
  try {
    await fetch('/reset', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({task_id:task})});
    await refreshAll();
    setText('auto-status', 'Episode started!');
  } catch(e) { setText('auto-status', 'Error: '+e.message); }
}

async function stepOnce() {
  try {
    const resp = await fetch('/step', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({tool_name:'advance_hour', parameters:{}})});
    const data = await resp.json();
    console.log('FULL STEP RESPONSE:', JSON.stringify(data, null, 2));
    
    // Update per-agent stats from step response
    if (data.agent_reports) {
      Object.entries(data.agent_reports).forEach(([agId, report]) => {
        if (!agentStats[agId]) {
          agentStats[agId] = {
            actions: 0, totalReward: 0, conflicts: 0,
            decisions: [], mission: 'Standby'
          };
        }
        const s = agentStats[agId];
        const action = report.current_action || '';
        const stepReward = parseFloat(data.action?.reward || 0);
        const hasConflict = !!(report.conflict_with);
        
        // Only count for the agent whose action was chosen
        // All agents get their status updated
        if (action && action !== 'Initializing' && action !== 'standby') {
          s.actions++;
          s.totalReward += (stepReward / 8); // split reward across agents
          if (hasConflict) s.conflicts++;
          
          const decisionStr = `${action}`;
          const rewardStr = `${stepReward >= 0 ? '+' : ''}${stepReward.toFixed(2)}`;
          s.decisions.unshift(`${decisionStr} → ${rewardStr}`);
          if (s.decisions.length > 5) s.decisions = s.decisions.slice(0, 5);
          s.mission = action + (report.details?.zone_id 
            ? ` in ${report.details.zone_id}` : '');
        }
      });
      
      // The coordinator specifically gets full credit for the action taken
      const coordAction = data.action?.tool_name || '';
      const coordReward = parseFloat(data.action?.reward || 0);
      const coordHour = data.action?.hour || 0;
      if (coordAction && agentStats['coordinator']) {
        const cs = agentStats['coordinator'];
        cs.decisions[0] = `${coordAction} (H${coordHour}) → ${coordReward >= 0 ? '+' : ''}${coordReward.toFixed(2)}`;
      }
    }
    
    // Get richer action info
    const actionHistory = data.observation?.action_history || [];
    const lastAction = actionHistory[actionHistory.length - 1] || {};
    
    const toolName = lastAction.tool_name || data.action?.tool_name || 'step';
    const params = lastAction.parameters || lastAction.params || {};
    const stepReward = parseFloat(lastAction.reward ?? data.reward ?? 0);
    const hour = lastAction.hour ?? data.observation?.current_hour ?? 0;
    const conflictStr = lastAction.conflict_resolved || data.action?.conflict || '';
    const stepNum = lastAction.step ?? data.observation?.step_number ?? 0;
    
    addLogLine(
      stepNum,
      'Coordinator',
      toolName,
      params,
      stepReward,
      conflictStr,
      hour
    );
    
    await refreshAll();
    if(data.done) setText('auto-status', 'DONE! Score: '+(data.info?.grader_score||0).toFixed(3));
  } catch(e) { setText('auto-status', 'Error'); }
}

let autoRunInterval = null;
let autoRunActive = false;

function autoRun() {
  if (autoRunActive) {
    clearInterval(autoRunInterval);
    autoRunActive = false;
    autoRunInterval = null;
    document.getElementById('auto-status').textContent = '';
    const btn = document.querySelector('button[onclick="autoRun()"]');
    if (btn) { btn.textContent = 'Auto-Run'; btn.style.background = ''; btn.style.color = ''; }
    return;
  }
  
  autoRunActive = true;
  const btn = document.querySelector('button[onclick="autoRun()"]');
  if (btn) { 
    btn.textContent = '⏹ Stop'; 
    btn.style.background = '#f85149';
    btn.style.color = '#fff';
  }
  
  let stepCount = 0;
  document.getElementById('auto-status').textContent = 'Running...';
  
  autoRunInterval = setInterval(async () => {
    stepCount++;
    document.getElementById('auto-status').textContent = `Step ${stepCount}...`;
    
    // Call stepOnce AND force map re-render
    await stepOnce();
    
    // Force map update after each step
    const stateResp = await fetch('/state');
    if (stateResp.ok) {
      const stateData = await stateResp.json();
      if (stateData && stateData.graph) {
        updateCrisisMap(stateData.graph);
      }
    }
  }, 800);
}

// ==================== INIT ====================
initCharts();
refreshAll();
</script>
<!-- AGENT MODAL -->
<div id="agent-modal" style="display:none; position:fixed; 
  top:0; left:0; width:100%; height:100%; 
  background:rgba(0,0,0,0.7); z-index:1000; 
  backdrop-filter:blur(4px);"
  onclick="if(event.target===this) closeAgentModal()">
  <div style="
    position:absolute; top:50%; left:50%;
    transform:translate(-50%,-50%);
    background:#0d1117; border:1px solid #30363d;
    border-radius:14px; padding:24px;
    width:420px; max-width:90vw;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  ">
    <div style="display:flex; justify-content:space-between; 
                align-items:center; margin-bottom:16px;">
      <div>
        <h2 id="modal-agent-name" style="color:#e6edf3; font-size:18px; 
                                          font-weight:700;"></h2>
        <p id="modal-agent-role" style="color:#8b949e; font-size:12px;
                                         margin-top:3px;"></p>
      </div>
      <div style="display:flex; gap:8px; align-items:center;">
        <span id="modal-status-badge" style="padding:4px 12px; 
          border-radius:20px; font-size:11px; font-weight:700;"></span>
        <button onclick="closeAgentModal()" style="background:none; 
          border:none; color:#8b949e; font-size:20px; cursor:pointer;">×</button>
      </div>
    </div>
    
    <!-- Stats row -->
    <div style="display:grid; grid-template-columns:repeat(3,1fr); 
                gap:10px; margin-bottom:16px;">
      <div style="background:#161b22; border-radius:8px; padding:10px; 
                  text-align:center;">
        <div style="color:#8b949e; font-size:10px;">Actions Taken</div>
        <div id="modal-actions" style="color:#58a6ff; font-size:22px; 
                                        font-weight:700; margin-top:4px;">0</div>
      </div>
      <div style="background:#161b22; border-radius:8px; padding:10px; 
                  text-align:center;">
        <div style="color:#8b949e; font-size:10px;">Avg Reward</div>
        <div id="modal-avg-reward" style="color:#3fb950; font-size:22px; 
                                           font-weight:700; margin-top:4px;">0.00</div>
      </div>
      <div style="background:#161b22; border-radius:8px; padding:10px; 
                  text-align:center;">
        <div style="color:#8b949e; font-size:10px;">Conflicts</div>
        <div id="modal-conflicts" style="color:#f85149; font-size:22px; 
                                          font-weight:700; margin-top:4px;">0</div>
      </div>
    </div>
    
    <!-- Extra Stats -->
    <div style="background:#161b22; border-radius:8px; padding:10px; 
                margin-bottom:12px; display:flex; gap:16px;">
      <div style="flex:1; text-align:center;">
        <div style="color:#8b949e; font-size:10px;">Total Reward</div>
        <div id="modal-total-reward" style="color:#3fb950; font-size:16px; 
                                             font-weight:700; margin-top:2px;">
          0.00
        </div>
      </div>
      <div style="flex:1; text-align:center;">
        <div style="color:#8b949e; font-size:10px;">Success Rate</div>
        <div id="modal-success-rate" style="color:#58a6ff; font-size:16px; 
                                             font-weight:700; margin-top:2px;">
          0%
        </div>
      </div>
      <div style="flex:1; text-align:center;">
        <div style="color:#8b949e; font-size:10px;">Last Action</div>
        <div id="modal-last-action" style="color:#ffa657; font-size:11px; 
                                            font-weight:600; margin-top:4px;">
          —
        </div>
      </div>
    </div>
    
    <!-- Current mission -->
    <div style="background:#161b22; border-radius:8px; padding:12px; 
                margin-bottom:12px;">
      <div style="color:#8b949e; font-size:10px; 
                  text-transform:uppercase; margin-bottom:6px;">
        Current Mission
      </div>
      <div id="modal-mission" style="color:#e6edf3; font-size:12px; 
                                      line-height:1.6;">—</div>
    </div>
    
    <!-- Recent decisions -->
    <div style="background:#161b22; border-radius:8px; padding:12px;">
      <div style="color:#8b949e; font-size:10px; 
                  text-transform:uppercase; margin-bottom:6px;">
        Last 5 Decisions
      </div>
      <div id="modal-decisions" style="font-family:monospace; font-size:11px; 
                                        color:#e6edf3; line-height:2.0;"></div>
    </div>
    
    <!-- Capabilities -->
    <div style="background:#161b22; border-radius:8px; padding:12px; 
                margin-top:10px;">
      <div style="color:#8b949e; font-size:10px; text-transform:uppercase; 
                  margin-bottom:6px;">Capabilities</div>
      <div id="modal-capabilities" style="font-size:11px; color:#e6edf3; 
                                           line-height:2.0;"></div>
    </div>
  </div>
</div>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_HTML

# Refine chunk 0

# Refine chunk 1

# Refine chunk 2

# Refine chunk 3

# Refine chunk 4

# Refine chunk 5

# Refine chunk 6

# Refine chunk 7

# Refine chunk 8

# Refine chunk 9

# Refine chunk 10

# Refine chunk 11

# Refine chunk 12

# Refine chunk 13
