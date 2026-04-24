from typing import Dict, List, Optional
from server.models import AgentReport, AgentStatus


class BaseAgent:
    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.status = AgentStatus.IDLE
        self.current_action = "Initializing"
        self.recommendation = ""

    def assess(self, state: dict) -> AgentReport:
        raise NotImplementedError

    def react(self, action: dict, state: dict) -> dict:
        raise NotImplementedError

    def _make_report(
        self,
        action: str,
        rec: str,
        urgency: str = "normal",
        conflict_with: str = None,
        conflict_reason: str = None,
        cooperation_chain: str = None,
        details: dict = None,
    ) -> AgentReport:
        self.current_action = action
        self.recommendation = rec
        return AgentReport(
            agent_name=self.name,
            status=self.status,
            current_action=action,
            recommendation=rec,
            urgency=urgency,
            conflict_with=conflict_with,
            conflict_reason=conflict_reason,
            cooperation_chain=cooperation_chain,
            details=details or {},
        )


class LogisticsAgent(BaseAgent):
    """Manages ground transport (trucks, boats). Knows road graph status."""

    def __init__(self):
        super().__init__("logistics", "Logistics")
        self.known_blocked_roads: List[str] = []

    def assess(self, state: dict) -> AgentReport:
        roads = state.get("roads", [])
        blocked = [r.get("road_id", r.get("id", "")) for r in roads if r.get("status") == "blocked"]
        flooded = [r.get("road_id", r.get("id", "")) for r in roads if r.get("status") == "flooded"]
        self.known_blocked_roads = blocked
        trucks = state.get("resources", {}).get("trucks_available", 0)
        boats = state.get("resources", {}).get("boats_available", 0)

        if blocked:
            self.status = AgentStatus.WARNING
            action = f"{len(blocked)} roads blocked: {', '.join(blocked[:3])}"
            rec = "Avoid blocked roads. Use alternate routes or boats for flooded roads."
            conflict = None
            conflict_reason = None
            if flooded:
                conflict = "air_support"
                conflict_reason = (
                    f"{len(flooded)} flooded roads — need boats OR helicopter. "
                    "Logistics wants boats, Air wants to save fuel."
                )
            return self._make_report(
                action,
                rec,
                urgency="high",
                conflict_with=conflict,
                conflict_reason=conflict_reason,
                details={
                    "blocked_roads": blocked,
                    "flooded_roads": flooded,
                    "trucks_available": trucks,
                    "boats_available": boats,
                },
            )

        self.status = AgentStatus.ACTIVE
        return self._make_report(
            f"Routes operational. {trucks} trucks, {boats} boats ready.",
            "Ground transport available for deployment.",
            details={
                "blocked_roads": [],
                "flooded_roads": flooded,
                "trucks_available": trucks,
                "boats_available": boats,
            },
        )

    def react(self, action: dict, state: dict) -> dict:
        tool = action.get("tool_name", "")
        if tool == "dispatch_team":
            zone = action.get("parameters", {}).get("zone_id", "?")
            transport = action.get("parameters", {}).get("transport", "truck")
            self.current_action = f"Dispatching {transport} to {zone}"
        elif tool == "re_route":
            self.current_action = "Re-routing active teams due to road changes"
        return {"logistics_updated": True}


class MedicalAgent(BaseAgent):
    """Tracks hospital capacity, injured counts, triage priority."""

    def __init__(self):
        super().__init__("medical", "Medical")
        self.critical_zones: List[str] = []

    def assess(self, state: dict) -> AgentReport:
        zones = state.get("zones", [])
        hospitals = state.get("hospitals", [])
        critical_zones = [z for z in zones if z.get("injured_critical", 0) > 0]
        self.critical_zones = [z.get("zone_id", z.get("id", "")) for z in critical_zones]
        total_critical = sum(z.get("injured_critical", 0) for z in critical_zones)
        overloaded = [
            h
            for h in hospitals
            if h.get("capacity_pct", 0) >= 85
            or (h.get("current_patients", 0) / max(h.get("capacity", 1), 1) * 100) >= 85
        ]

        if total_critical > 0:
            self.status = AgentStatus.URGENT
            worst = max(critical_zones, key=lambda z: z.get("injured_critical", 0))
            worst_id = worst.get("zone_id", worst.get("id", "?"))
            worst_name = worst.get("name", worst_id)
            worst_count = worst.get("injured_critical", 0)
            action = f"{total_critical} critical patients in {len(critical_zones)} zones"
            rec = f"URGENT: Send medical team to {worst_name} — {worst_count} critical patients"
            return self._make_report(
                action,
                rec,
                urgency="critical",
                conflict_with="supply_chain",
                conflict_reason=(
                    "Medical demands immediate resource deployment. "
                    "Supply wants to conserve for later phases."
                ),
                details={
                    "total_critical": total_critical,
                    "critical_zones": self.critical_zones,
                    "worst_zone": worst_id,
                    "overloaded_hospitals": [h.get("hospital_id", "") for h in overloaded],
                },
            )

        self.status = AgentStatus.ACTIVE
        return self._make_report(
            "No critical patients currently",
            "Medical situation stable",
            details={
                "total_critical": 0,
                "overloaded_hospitals": [h.get("hospital_id", "") for h in overloaded],
            },
        )

    def react(self, action: dict, state: dict) -> dict:
        tool = action.get("tool_name", "")
        if tool in ("dispatch_team", "allocate_resource"):
            zone = action.get("parameters", {}).get("zone_id", "?")
            self.current_action = f"Medical response to {zone}"
        return {"medical_updated": True}


class AirSupportAgent(BaseAgent):
    """Manages helicopters and drones. LIMITED FUEL = limited trips."""

    def __init__(self):
        super().__init__("air_support", "Air Support")

    def assess(self, state: dict) -> AgentReport:
        res = state.get("resources", {})
        fuel = res.get("fuel_helicopter", 0)
        helis = res.get("helicopters_available", 0)
        hour = state.get("current_hour", 0)
        hours_left = 72 - hour

        if fuel <= 2:
            self.status = AgentStatus.WARNING
            action = f"FUEL CRITICAL: Only {fuel} helicopter trips remaining"
            rec = f"CONSERVE fuel — {hours_left}h remaining in operation. Use ground transport."
            return self._make_report(
                action,
                rec,
                urgency="high",
                conflict_with="medical",
                conflict_reason=f"Only {fuel} trips left but Medical demanding airlift for critical patients.",
                details={"fuel_remaining": fuel, "helicopters": helis, "hours_remaining": hours_left},
            )

        self.status = AgentStatus.ACTIVE
        action = f"Air support ready: {fuel} trips fuel, {helis} helicopters"
        rec = "Helicopter available." if fuel > 5 else f"Use selectively — {fuel} trips left."
        return self._make_report(
            action,
            rec,
            details={"fuel_remaining": fuel, "helicopters": helis, "hours_remaining": hours_left},
        )

    def react(self, action: dict, state: dict) -> dict:
        tool = action.get("tool_name", "")
        if tool == "request_airlift":
            self.current_action = f"Helicopter to {action.get('parameters', {}).get('zone_id', '?')}"
        elif tool == "deploy_scout":
            self.current_action = "Drone deployed for scouting"
        return {"air_updated": True}


class CommunicationAgent(BaseAgent):
    """Monitors signal status per zone. Manages satellite phones, radio."""

    def __init__(self):
        super().__init__("communication", "Communication")
        self.dark_zones: List[str] = []

    def assess(self, state: dict) -> AgentReport:
        zones = state.get("zones", [])
        self.dark_zones = [z for z in zones if not z.get("has_communication", True)]

        if self.dark_zones:
            self.status = AgentStatus.WARNING
            worst = max(self.dark_zones, key=lambda z: z.get("last_contact_hours_ago", 0))
            worst_id = worst.get("zone_id", worst.get("id", "?"))
            hours_dark = worst.get("last_contact_hours_ago", 0)
            dark_ids = [z.get("zone_id", z.get("id", "")) for z in self.dark_zones]
            action = f"{len(self.dark_zones)} zones NO SIGNAL — {worst_id} dark for {hours_dark}h"
            rec = f"Deploy satellite phone to {worst_id} (dark {hours_dark}h, unknown survivors)"
            return self._make_report(
                action,
                rec,
                urgency="high",
                conflict_with="field_assessment",
                conflict_reason="Both need drone: Comms for signal check, Field for survivor search.",
                details={"dark_zones": dark_ids, "worst_zone": worst_id, "hours_dark": hours_dark},
            )

        self.status = AgentStatus.ACTIVE
        return self._make_report(
            "All zones have signal",
            "Communications stable",
            details={"dark_zones": []},
        )

    def react(self, action: dict, state: dict) -> dict:
        if action.get("tool_name") == "setup_comms":
            zone = action.get("parameters", {}).get("zone_id", "?")
            self.current_action = f"Setting up comms in {zone}"
        return {"comms_updated": True}


class GroundRescueAgent(BaseAgent):
    """Foot rescue teams. Slow but can access areas vehicles cannot."""

    def __init__(self):
        super().__init__("ground_rescue", "Ground Rescue")
        self.survivors_found: int = 0
        self.teams_deployed: int = 0

    def assess(self, state: dict) -> AgentReport:
        teams = state.get("teams", [])
        foot_active = [t for t in teams if t.get("transport") == "foot" and t.get("status") != "idle"]
        foot_idle = [t for t in teams if t.get("transport") == "foot" and t.get("status") == "idle"]
        self.teams_deployed = len(foot_active)

        zones = state.get("zones", [])
        unreached = [
            z
            for z in zones
            if z.get("rescued", 0) == 0 and z.get("population", 0) > 0 and z.get("status") != "safe"
        ]

        coop = None
        if self.survivors_found > 0:
            coop = (
                f"Ground found {self.survivors_found} survivors "
                "→ Medical dispatching → Logistics routing transport"
            )

        if unreached and foot_idle:
            self.status = AgentStatus.ACTIVE
            target = unreached[0]
            target_id = target.get("zone_id", target.get("id", "?"))
            target_name = target.get("name", target_id)
            action = f"{self.teams_deployed} teams active, {len(foot_idle)} idle"
            rec = f"Send foot team to {target_name} ({target.get('population', 0)} people stranded)"
            return self._make_report(
                action,
                rec,
                cooperation_chain=coop,
                details={
                    "deployed": self.teams_deployed,
                    "idle": len(foot_idle),
                    "unreached_zones": len(unreached),
                },
            )

        self.status = AgentStatus.ACTIVE
        return self._make_report(
            f"{self.teams_deployed} ground teams operating",
            "Ground operations ongoing",
            cooperation_chain=coop,
            details={"deployed": self.teams_deployed},
        )

    def react(self, action: dict, state: dict) -> dict:
        if action.get("tool_name") == "dispatch_team":
            if action.get("parameters", {}).get("transport") == "foot":
                self.teams_deployed += 1
                self.current_action = f"Foot team to {action['parameters'].get('zone_id', '?')}"
        return {"ground_updated": True}


class SupplyChainAgent(BaseAgent):
    """Tracks food, water, medicine, tents. Manages depletion + conservation."""

    def __init__(self):
        super().__init__("supply_chain", "Supply Chain")

    def assess(self, state: dict) -> AgentReport:
        res = state.get("resources", {})
        max_f = max(res.get("max_food", 1000), 1)
        max_w = max(res.get("max_water", 800), 1)
        max_m = max(res.get("max_medicine", 500), 1)
        food_pct = round(res.get("food_units", 0) / max_f * 100)
        water_pct = round(res.get("water_units", 0) / max_w * 100)
        med_pct = round(res.get("medicine_units", 0) / max_m * 100)
        phase = state.get("current_phase", "rescue")

        warnings = []
        if food_pct < 30:
            warnings.append(f"Food {food_pct}%")
        if water_pct < 30:
            warnings.append(f"Water {water_pct}%")
        if med_pct < 30:
            warnings.append(f"Medicine {med_pct}%")

        if warnings:
            self.status = AgentStatus.WARNING
            action = "LOW STOCK: " + ", ".join(warnings)
            rec = f"Conserve supplies — we are in {phase} phase, need reserves for later."
            return self._make_report(
                action,
                rec,
                urgency="high",
                conflict_with="medical",
                conflict_reason=(
                    "Supply wants conservation for later phases. "
                    "Medical demands immediate distribution for critical patients."
                ),
                details={
                    "food_pct": food_pct,
                    "water_pct": water_pct,
                    "medicine_pct": med_pct,
                    "phase": phase,
                    "tents": res.get("tents", 0),
                },
            )

        self.status = AgentStatus.ACTIVE
        return self._make_report(
            f"Supplies adequate — Food:{food_pct}%, Water:{water_pct}%, Med:{med_pct}%",
            "Distribution can proceed normally.",
            details={
                "food_pct": food_pct,
                "water_pct": water_pct,
                "medicine_pct": med_pct,
                "phase": phase,
                "tents": res.get("tents", 0),
            },
        )

    def react(self, action: dict, state: dict) -> dict:
        if action.get("tool_name") == "allocate_resource":
            rtype = action.get("parameters", {}).get("resource_type", "supplies")
            self.current_action = f"Distributing {rtype}"
        return {"supply_updated": True}


class FieldAssessmentAgent(BaseAgent):
    """Scout drones. Discovers new survivors. Updates crisis map."""

    def __init__(self):
        super().__init__("field_assessment", "Field Assessment")
        self.zones_scouted: List[str] = []
        self.discoveries: int = 0

    def assess(self, state: dict) -> AgentReport:
        zones = state.get("zones", [])
        unscouted = [
            z
            for z in zones
            if z.get("zone_id", z.get("id", "")) not in self.zones_scouted
            and not z.get("has_communication", True)
        ]

        if unscouted:
            self.status = AgentStatus.ACTIVE
            target = unscouted[0]
            target_id = target.get("zone_id", target.get("id", "?"))
            action = f"{len(unscouted)} zones not yet scouted"
            rec = f"Deploy scout drone to {target.get('name', target_id)} — potential survivors unknown"
            return self._make_report(
                action,
                rec,
                details={
                    "unscouted": [z.get("zone_id", z.get("id", "")) for z in unscouted],
                    "scouted": len(self.zones_scouted),
                    "discoveries": self.discoveries,
                },
            )

        self.status = AgentStatus.ACTIVE
        return self._make_report(
            "All zones assessed — map current",
            "No further scouting needed right now.",
            details={"scouted": len(self.zones_scouted), "discoveries": self.discoveries},
        )

    def react(self, action: dict, state: dict) -> dict:
        if action.get("tool_name") == "deploy_scout":
            zone = action.get("parameters", {}).get("zone_id", "?")
            if zone not in self.zones_scouted:
                self.zones_scouted.append(zone)
            self.current_action = f"Scouting {zone}"
        return {"field_updated": True}


class CoordinatorAgent(BaseAgent):
    """The MAIN agent. Receives all reports. Makes decisions. LLM-powered."""

    def __init__(self):
        super().__init__("coordinator", "Coordinator")
        self.decisions_made: int = 0
        self.conflicts_resolved: int = 0

    def assess(self, state: dict) -> AgentReport:
        self.status = AgentStatus.ACTIVE
        hour = state.get("current_hour", 0)
        phase = state.get("current_phase", "rescue")
        total_rescued = state.get("total_rescued", 0)
        total_pop = sum(z.get("population", 0) for z in state.get("zones", []))
        rescue_pct = round(total_rescued / max(total_pop, 1) * 100)

        return self._make_report(
            f"Hour {hour}/72 | Phase: {phase} | Rescued: {rescue_pct}% | Decisions: {self.decisions_made}",
            "Awaiting next action from LLM agent.",
            details={
                "hour": hour,
                "phase": phase,
                "decisions": self.decisions_made,
                "conflicts_resolved": self.conflicts_resolved,
                "rescue_pct": rescue_pct,
            },
        )

    def react(self, action: dict, state: dict) -> dict:
        self.decisions_made += 1
        tool = action.get("tool_name", "unknown")
        self.current_action = f"Executed: {tool}"
        reports = state.get("agent_reports", {})
        for _, report in reports.items():
            if isinstance(report, dict) and report.get("conflict_with"):
                self.conflicts_resolved += 1
                break
        return {"coordinator_updated": True}


def create_all_agents() -> Dict[str, BaseAgent]:
    """Factory function to create all 8 agents."""
    return {
        "coordinator": CoordinatorAgent(),
        "logistics": LogisticsAgent(),
        "medical": MedicalAgent(),
        "air_support": AirSupportAgent(),
        "communication": CommunicationAgent(),
        "ground_rescue": GroundRescueAgent(),
        "supply_chain": SupplyChainAgent(),
        "field_assessment": FieldAssessmentAgent(),
    }
