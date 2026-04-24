from pydantic import BaseModel
from typing import List, Dict, Optional
from enum import Enum

# ===== ENUMS =====
class ZoneStatus(str, Enum):
    SAFE = "safe"
    FLOODED = "flooded"
    DAMAGED = "damaged"
    DESTROYED = "destroyed"


class RoadStatus(str, Enum):
    OPEN = "open"
    FLOODED = "flooded"
    BLOCKED = "blocked"
    DAMAGED = "damaged"


class TeamType(str, Enum):
    RESCUE = "rescue"
    MEDICAL = "medical"
    SUPPLY = "supply"
    SCOUT = "scout"


class TransportType(str, Enum):
    TRUCK = "truck"
    BOAT = "boat"
    HELICOPTER = "helicopter"
    FOOT = "foot"


class Phase(str, Enum):
    RESCUE = "rescue"
    RELIEF = "relief"
    REHABILITATION = "rehabilitation"


class AgentStatus(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    WARNING = "warning"
    URGENT = "urgent"
    OFFLINE = "offline"


class EventType(str, Enum):
    AFTERSHOCK = "aftershock"
    HOSPITAL_OVERFLOW = "hospital_overflow"
    COMMS_DOWN = "comms_down"
    NEW_SURVIVORS = "new_survivors"
    SUPPLY_DELAY = "supply_delay"
    ROAD_CLEARS = "road_clears"
    VOLUNTEER_ARRIVAL = "volunteer_arrival"
    NDRF_REINFORCEMENT = "ndrf_reinforcement"


# ===== DATA MODELS =====
class Zone(BaseModel):
    zone_id: str
    name: str
    zone_type: str = "village"
    population: int
    injured_critical: int = 0
    injured_moderate: int = 0
    rescued: int = 0
    dead: int = 0
    status: ZoneStatus = ZoneStatus.SAFE
    has_communication: bool = True
    last_contact_hours_ago: int = 0
    distress_level: float = 0.0


class Hospital(BaseModel):
    hospital_id: str
    name: str
    capacity: int
    current_patients: int = 0
    has_power: bool = True
    is_damaged: bool = False
    capacity_pct: float = 0.0


class Road(BaseModel):
    road_id: str
    from_zone: str
    to_zone: str
    status: RoadStatus = RoadStatus.OPEN
    travel_time_hours: float
    actual_travel_time: float = 0.0


class Team(BaseModel):
    team_id: str
    team_type: TeamType
    transport: TransportType = TransportType.TRUCK
    current_zone: str
    destination: Optional[str] = None
    status: str = "idle"
    eta_hours: float = 0.0
    assigned_task: Optional[str] = None


class Resource(BaseModel):
    food_units: int = 0
    water_units: int = 0
    medicine_units: int = 0
    tents: int = 0
    fuel_helicopter: float = 0.0
    boats_available: int = 0
    trucks_available: int = 0
    helicopters_available: int = 0
    budget_remaining: float = 100.0
    max_food: int = 1000
    max_water: int = 800
    max_medicine: int = 500
    max_fuel: float = 10.0


class AgentReport(BaseModel):
    agent_name: str
    status: AgentStatus = AgentStatus.IDLE
    current_action: str = ""
    recommendation: str = ""
    urgency: str = "normal"
    conflict_with: Optional[str] = None
    conflict_reason: Optional[str] = None
    cooperation_chain: Optional[str] = None
    details: Dict = {}


class DynamicEvent(BaseModel):
    event_type: EventType
    hour_triggered: int
    description: str
    zones_affected: List[str] = []
    roads_affected: List[str] = []


class Observation(BaseModel):
    zones: List[Zone] = []
    hospitals: List[Hospital] = []
    roads: List[Road] = []
    resources: Resource = Resource()
    teams: List[Team] = []
    agent_reports: Dict[str, AgentReport] = {}
    current_hour: int = 0
    current_phase: Phase = Phase.RESCUE
    dynamic_events: List[str] = []
    step_number: int = 0
    task_id: str = ""
    total_rescued: int = 0
    total_deaths: int = 0


class Action(BaseModel):
    tool_name: str
    parameters: Dict = {}


class StepResult(BaseModel):
    observation: Observation
    reward: float = 0.0
    done: bool = False
    info: Dict = {}


class FullState(BaseModel):
    observation: Observation
    total_reward: float = 0.0
    action_history: List[Dict] = []
    strategy_memory: List[Dict] = []
    curriculum_difficulty: float = 3.0
    episode_number: int = 0
    current_weakness: str = "none"
