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
.grid-2{display:grid;grid-template-columns:3fr 2fr;gap:10px}
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
  padding: 10px 8px;
  text-align: center;
  border: 2px solid transparent;
  transition: all 0.3s;
  position: relative;
}
.agent-card.active-agent{
  border-color: #1D9E75;
  box-shadow: 0 0 12px rgba(29,158,117,0.3);
}
.agent-card.urgent-agent{
  border-color: #E24B4A;
  box-shadow: 0 0 12px rgba(226,75,74,0.3);
  animation: urgentPulse 1s infinite;
}
@keyframes urgentPulse{
  0%,100%{box-shadow: 0 0 8px rgba(226,75,74,0.3);}
  50%{box-shadow: 0 0 20px rgba(226,75,74,0.6);}
}
.agent-name{ font-size: 12px; font-weight: 700; }
.agent-action{ font-size: 10px; margin-top: 4px; color: #555; min-height: 28px; line-height: 1.4; }
.agent-badge{
  font-size: 9px; padding: 3px 8px; border-radius: 4px;
  display: inline-block; margin-top: 4px; font-weight: 600;
}
.conflict-banner{display:none;background:#FFF3CD;color:#856404;padding:6px 10px;border-radius:4px;text-align:center;font-size:10px;font-weight:500;margin-top:6px;animation:flash 0.5s 3}
.coop-banner{display:none;background:#D4EDDA;color:#155724;padding:6px 10px;border-radius:4px;text-align:center;font-size:10px;margin-top:4px}
.action-log{
  font-family: 'Courier New', monospace;
  font-size: 11px;
  max-height: 160px;
  overflow-y: auto;
  background: #0d1117;
  color: #e6edf3;
  padding: 12px;
  border-radius: 8px;
  line-height: 2.0;
  border: 1px solid #30363d;
}
.log-line{ border-bottom: 1px solid #21262d; padding: 2px 0; }
.reward-pos{ color: #3fb950; font-weight: 700; }
.reward-neg{ color: #f85149; font-weight: 700; }
.log-step{ color: #79c0ff; }
.log-agent{ color: #d2a8ff; }
.log-action{ color: #ffa657; }
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
  <div class="panel">
    <span class="section-label" style="background:#FAECE7;color:#712B13">Theme 3: World Model — Crisis Map</span>
    <div class="map-container">
      <svg id="crisis-map" viewBox="0 0 520 400" width="100%" style="min-height:220px"></svg>
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
  <div class="panel">
    <span class="section-label" style="background:#EEEDFE;color:#3C3489">Theme 1: Multi-Agent — 8 Agent Swarm</span>
    <div class="grid-4" style="margin-top:6px" id="agents-grid-1">
      <div class="agent-card" id="ag-coordinator" style="background:#EEEDFE"><div class="agent-name" style="color:#3C3489">Coordinator</div><div class="agent-action" id="ag-coordinator-act">Initializing</div><div class="agent-badge" id="ag-coordinator-badge" style="background:#CECBF6;color:#26215C">IDLE</div></div>
      <div class="agent-card" id="ag-logistics" style="background:#FAECE7"><div class="agent-name" style="color:#712B13">Logistics</div><div class="agent-action" id="ag-logistics-act">Ready</div><div class="agent-badge" id="ag-logistics-badge" style="background:#F5C4B3;color:#4A1B0C">IDLE</div></div>
      <div class="agent-card" id="ag-medical" style="background:#E6F1FB"><div class="agent-name" style="color:#0C447C">Medical</div><div class="agent-action" id="ag-medical-act">Ready</div><div class="agent-badge" id="ag-medical-badge" style="background:#B5D4F4;color:#042C53">IDLE</div></div>
      <div class="agent-card" id="ag-air_support" style="background:#FAEEDA"><div class="agent-name" style="color:#633806">Air Support</div><div class="agent-action" id="ag-air_support-act">Ready</div><div class="agent-badge" id="ag-air_support-badge" style="background:#FAC775;color:#412402">IDLE</div></div>
    </div>
    <div class="grid-4" style="margin-top:4px" id="agents-grid-2">
      <div class="agent-card" id="ag-communication" style="background:#E1F5EE"><div class="agent-name" style="color:#085041">Comms</div><div class="agent-action" id="ag-communication-act">Ready</div><div class="agent-badge" id="ag-communication-badge" style="background:#9FE1CB;color:#04342C">IDLE</div></div>
      <div class="agent-card" id="ag-ground_rescue" style="background:#FBEAF0"><div class="agent-name" style="color:#72243E">Ground</div><div class="agent-action" id="ag-ground_rescue-act">Ready</div><div class="agent-badge" id="ag-ground_rescue-badge" style="background:#F4C0D1;color:#4B1528">IDLE</div></div>
      <div class="agent-card" id="ag-supply_chain" style="background:#FCEBEB"><div class="agent-name" style="color:#791F1F">Supply</div><div class="agent-action" id="ag-supply_chain-act">Ready</div><div class="agent-badge" id="ag-supply_chain-badge" style="background:#F7C1C1;color:#501313">IDLE</div></div>
      <div class="agent-card" id="ag-field_assessment" style="background:#F1EFE8"><div class="agent-name" style="color:#444441">Scout</div><div class="agent-action" id="ag-field_assessment-act">Ready</div><div class="agent-badge" id="ag-field_assessment-badge" style="background:#D3D1C7;color:#2C2C2A">IDLE</div></div>
    </div>
    <div class="conflict-banner" id="conflict-alert"></div>
    <div class="coop-banner" id="coop-alert"></div>
  </div>
</div>

<!-- SECTION D: ACTION LOG -->
<div class="panel">
  <span class="section-label" style="background:#E1F5EE;color:#085041">Live Action Stream</span>
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
function setText(id, val) { const el = document.getElementById(id); if(el) el.textContent = val; }
function makeSVG(tag, attrs, text) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attrs).forEach(([k,v]) => el.setAttribute(k, v));
  if (text !== undefined) el.textContent = text;
  return el;
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
    svg.appendChild(makeSVG('text', {x:n.x,y:n.y+20,'text-anchor':'middle','font-size':'8',fill:'#7EC8C8'}, n.name||n.id));
  });
  teams.forEach(t => {
    svg.appendChild(makeSVG('circle', {cx:t.current_x,cy:t.current_y,r:'5',fill:'#a78bfa',stroke:'#fff','stroke-width':'1.5'}));
    svg.appendChild(makeSVG('text', {x:t.current_x,y:t.current_y-8,'text-anchor':'middle','font-size':'7',fill:'#a78bfa','font-weight':'500'}, t.id));
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

function updateActionLog(history) {
  const log = document.getElementById('action-log');
  const last = (history||[]).slice(-12);
  log.innerHTML = last.map(e => {
    let line = '<span class="log-step">Step '+e.step+':</span> <span class="log-action">'+e.tool_name+'</span> '+((e.params_short||'').substring(0,40))+' ';
    if(e.event) line += '<span class="event-inline">EVENT: '+e.event+'</span> ';
    if(e.conflict_resolved) line += '<span class="conflict-inline">'+e.conflict_resolved+'</span> ';
    const r = e.reward||0;
    line += '<span class="'+(r>=0?'reward-pos':'reward-neg')+'">'+(r>=0?'+':'')+r.toFixed(2)+'</span>';
    return '<div class="log-line">'+line+'</div>';
  }).join('');
  log.scrollTop = log.scrollHeight;
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
    await refreshAll();
    if(data.done) setText('auto-status', 'DONE! Score: '+(data.info?.grader_score||0).toFixed(3));
  } catch(e) { setText('auto-status', 'Error'); }
}

let autoRunning = false;
async function autoRun() {
  if(autoRunning) { autoRunning=false; setText('auto-status','Stopped'); return; }
  autoRunning = true;
  setText('auto-status', 'Auto-running...');
  const actions = ['dispatch_team','allocate_resource','deploy_scout','setup_comms','request_airlift','advance_hour'];
  const zones = ['Z1','Z2','Z3','Z4','Z5'];
  while(autoRunning) {
    const tool = actions[Math.floor(Math.random()*actions.length)];
    const params = {};
    if(tool==='dispatch_team') { params.zone_id=zones[Math.floor(Math.random()*zones.length)]; params.team_type='rescue'; params.transport='boat'; }
    else if(tool==='allocate_resource') { params.zone_id=zones[Math.floor(Math.random()*zones.length)]; params.resource_type='water'; params.quantity=20; }
    else if(tool==='deploy_scout'||tool==='setup_comms') { params.zone_id=zones[Math.floor(Math.random()*zones.length)]; }
    else if(tool==='request_airlift') { params.zone_id=zones[Math.floor(Math.random()*zones.length)]; }
    try {
      const resp = await fetch('/step', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({tool_name:tool, parameters:params})});
      const data = await resp.json();
      await refreshAll();
      if(data.done) { autoRunning=false; setText('auto-status','DONE! Score: '+(data.info?.grader_score||0).toFixed(3)); break; }
    } catch(e) { autoRunning=false; setText('auto-status','Error'); break; }
    await new Promise(r => setTimeout(r, 400));
  }
}

// ==================== INIT ====================
initCharts();
refreshAll();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_HTML
