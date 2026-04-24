from typing import Dict, List, Any
import random
import copy


TASK_CONFIGS: Dict[str, dict] = {

    # ==================== TASK 1: EASY ====================
    "village_flood_rescue": {
        "display_name": "Village Flood Rescue (Bihar)",
        "difficulty": "easy",
        "description": "Single village flooded in Darbhanga district, Bihar. 50 stranded people. 2 rescue boats, 1 medical team. 12-hour operation.",
        "max_steps": 20,
        "max_hours": 12,
        "population_total": 50,
        "nodes": [
            {"id": "BASE", "name": "NDRF Base Camp", "type": "base", "x": 250, "y": 320,
             "population": 0, "status": "safe", "injured_critical": 0, "injured_moderate": 0,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z1", "name": "Darbhanga Village", "type": "village", "x": 150, "y": 100,
             "population": 50, "status": "flooded", "injured_critical": 8, "injured_moderate": 15,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "H1", "name": "District Hospital", "type": "hospital", "x": 380, "y": 180,
             "capacity": 100, "current_patients": 20, "has_power": True, "is_damaged": False},
            {"id": "HELI1", "name": "Helipad Alpha", "type": "helipad", "x": 300, "y": 280,
             "population": 0, "status": "safe"},
            {"id": "S1", "name": "Relief Camp 1", "type": "shelter", "x": 420, "y": 320,
             "capacity": 200, "current_occupants": 0},
        ],
        "edges": [
            {"id": "R1", "from": "BASE", "to": "Z1", "status": "flooded", "travel_time": 3.0},
            {"id": "R2", "from": "BASE", "to": "H1", "status": "open", "travel_time": 1.5},
            {"id": "R3", "from": "Z1", "to": "H1", "status": "flooded", "travel_time": 2.5},
            {"id": "R4", "from": "BASE", "to": "HELI1", "status": "open", "travel_time": 0.5},
            {"id": "R5", "from": "H1", "to": "S1", "status": "open", "travel_time": 1.0},
            {"id": "R6", "from": "HELI1", "to": "Z1", "status": "open", "travel_time": 0.5},
        ],
        "initial_resources": {
            "food_units": 200, "water_units": 150, "medicine_units": 100, "tents": 20,
            "fuel_helicopter": 4.0, "boats_available": 2, "trucks_available": 1,
            "helicopters_available": 1, "budget_remaining": 100.0,
            "max_food": 200, "max_water": 150, "max_medicine": 100, "max_fuel": 4.0,
        },
        "initial_teams": [
            {"team_id": "NDRF-Alpha", "team_type": "rescue", "transport": "boat", "current_zone": "BASE"},
            {"team_id": "NDRF-Bravo", "team_type": "rescue", "transport": "boat", "current_zone": "BASE"},
            {"team_id": "Med-Unit-1", "team_type": "medical", "transport": "truck", "current_zone": "H1"},
        ],
        "event_schedule": [],
        "random_event_chance": 0.0,
        "grading_config": {
            "rescue_weight": 0.6, "time_weight": 0.2, "resource_efficiency_weight": 0.2,
        },
    },

    # ==================== TASK 2: MEDIUM ====================
    "multi_district_cyclone": {
        "display_name": "Multi-District Cyclone Response (Odisha)",
        "difficulty": "medium",
        "description": "Cyclone Fani strikes 5 districts in Odisha. 500 affected across 5 villages. 3 boats, 2 helicopters, 4 medical teams. Road R5 floods at Hour 6. 36-hour operation.",
        "max_steps": 40,
        "max_hours": 36,
        "population_total": 500,
        "nodes": [
            {"id": "BASE", "name": "Bhubaneswar Command", "type": "base", "x": 260, "y": 340,
             "population": 0, "status": "safe", "injured_critical": 0, "injured_moderate": 0,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z1", "name": "Puri Coastal", "type": "village", "x": 100, "y": 80,
             "population": 150, "status": "flooded", "injured_critical": 20, "injured_moderate": 35,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z2", "name": "Bhadrak Town", "type": "village", "x": 180, "y": 160,
             "population": 120, "status": "damaged", "injured_critical": 10, "injured_moderate": 25,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z3", "name": "Kendrapara", "type": "village", "x": 350, "y": 100,
             "population": 80, "status": "flooded", "injured_critical": 8, "injured_moderate": 15,
             "has_communication": False, "last_contact_hours_ago": 3},
            {"id": "Z4", "name": "Jagatsinghpur", "type": "village", "x": 420, "y": 200,
             "population": 100, "status": "damaged", "injured_critical": 12, "injured_moderate": 20,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z5", "name": "Balasore Village", "type": "village", "x": 80, "y": 260,
             "population": 50, "status": "flooded", "injured_critical": 5, "injured_moderate": 10,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "H1", "name": "SCB Medical College", "type": "hospital", "x": 300, "y": 260,
             "capacity": 200, "current_patients": 80, "has_power": True, "is_damaged": False},
            {"id": "H2", "name": "District Hospital Puri", "type": "hospital", "x": 150, "y": 300,
             "capacity": 80, "current_patients": 60, "has_power": True, "is_damaged": False},
            {"id": "HELI1", "name": "IAF Helipad", "type": "helipad", "x": 320, "y": 340,
             "population": 0, "status": "safe"},
            {"id": "S1", "name": "Cyclone Shelter 1", "type": "shelter", "x": 450, "y": 320,
             "capacity": 300, "current_occupants": 50},
        ],
        "edges": [
            {"id": "R1", "from": "BASE", "to": "Z1", "status": "flooded", "travel_time": 4.0},
            {"id": "R2", "from": "BASE", "to": "Z2", "status": "open", "travel_time": 2.0},
            {"id": "R3", "from": "Z1", "to": "Z2", "status": "flooded", "travel_time": 2.5},
            {"id": "R4", "from": "Z2", "to": "Z3", "status": "open", "travel_time": 3.0},
            {"id": "R5", "from": "Z3", "to": "Z4", "status": "open", "travel_time": 2.0},
            {"id": "R6", "from": "BASE", "to": "Z5", "status": "flooded", "travel_time": 3.5},
            {"id": "R7", "from": "Z5", "to": "H2", "status": "open", "travel_time": 1.5},
            {"id": "R8", "from": "BASE", "to": "H1", "status": "open", "travel_time": 1.0},
            {"id": "R9", "from": "Z4", "to": "H1", "status": "open", "travel_time": 2.5},
            {"id": "R10", "from": "Z1", "to": "H2", "status": "flooded", "travel_time": 2.0},
            {"id": "R11", "from": "BASE", "to": "HELI1", "status": "open", "travel_time": 0.5},
            {"id": "R12", "from": "H1", "to": "S1", "status": "open", "travel_time": 1.5},
            {"id": "R13", "from": "Z2", "to": "Z5", "status": "open", "travel_time": 3.0},
        ],
        "initial_resources": {
            "food_units": 600, "water_units": 500, "medicine_units": 300, "tents": 80,
            "fuel_helicopter": 8.0, "boats_available": 3, "trucks_available": 3,
            "helicopters_available": 2, "budget_remaining": 100.0,
            "max_food": 600, "max_water": 500, "max_medicine": 300, "max_fuel": 8.0,
        },
        "initial_teams": [
            {"team_id": "NDRF-Alpha", "team_type": "rescue", "transport": "boat", "current_zone": "BASE"},
            {"team_id": "NDRF-Bravo", "team_type": "rescue", "transport": "boat", "current_zone": "BASE"},
            {"team_id": "NDRF-Charlie", "team_type": "rescue", "transport": "truck", "current_zone": "BASE"},
            {"team_id": "Med-Unit-1", "team_type": "medical", "transport": "truck", "current_zone": "H1"},
            {"team_id": "Med-Unit-2", "team_type": "medical", "transport": "truck", "current_zone": "H2"},
            {"team_id": "Scout-Drone-1", "team_type": "scout", "transport": "helicopter", "current_zone": "BASE"},
        ],
        "event_schedule": [
            {"hour": 6, "type": "road_floods", "road_id": "R5", "description": "Storm surge floods Road R5 (Kendrapara-Jagatsinghpur). Trucks cannot pass."},
            {"hour": 18, "type": "hospital_overflow", "hospital_id": "H2", "description": "District Hospital Puri at 100% capacity. Divert patients to SCB Medical."},
        ],
        "random_event_chance": 0.05,
        "grading_config": {
            "rescue_weight": 0.4, "time_weight": 0.15, "resource_efficiency_weight": 0.15,
            "equity_weight": 0.15, "rerouting_weight": 0.15,
        },
    },

    # ==================== TASK 3: HARD ====================
    "earthquake_aftershock": {
        "display_name": "Earthquake + Aftershock Cascade (Gujarat)",
        "difficulty": "hard",
        "description": "7.2 magnitude earthquake in Gujarat. 12 zones, 2000+ people. Aftershock at Hour 18 blocks 3 roads and damages 1 hospital. Communication lost in 2 zones. 48-hour operation.",
        "max_steps": 55,
        "max_hours": 48,
        "population_total": 2000,
        "nodes": [
            {"id": "BASE", "name": "Gandhinagar Command", "type": "base", "x": 250, "y": 350,
             "population": 0, "status": "safe", "injured_critical": 0, "injured_moderate": 0,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z1", "name": "Bhuj Old City", "type": "village", "x": 80, "y": 60,
             "population": 400, "status": "destroyed", "injured_critical": 60, "injured_moderate": 100,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z2", "name": "Anjar Town", "type": "village", "x": 180, "y": 100,
             "population": 300, "status": "damaged", "injured_critical": 35, "injured_moderate": 70,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z3", "name": "Bachau Village", "type": "village", "x": 350, "y": 80,
             "population": 200, "status": "damaged", "injured_critical": 20, "injured_moderate": 40,
             "has_communication": False, "last_contact_hours_ago": 5},
            {"id": "Z4", "name": "Rapar Settlement", "type": "village", "x": 450, "y": 120,
             "population": 150, "status": "damaged", "injured_critical": 15, "injured_moderate": 30,
             "has_communication": False, "last_contact_hours_ago": 5},
            {"id": "Z5", "name": "Mandvi Coast", "type": "village", "x": 60, "y": 200,
             "population": 180, "status": "damaged", "injured_critical": 18, "injured_moderate": 35,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z6", "name": "Mundra Port Area", "type": "village", "x": 160, "y": 240,
             "population": 250, "status": "damaged", "injured_critical": 25, "injured_moderate": 50,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z7", "name": "Gandhidham", "type": "village", "x": 300, "y": 180,
             "population": 220, "status": "damaged", "injured_critical": 22, "injured_moderate": 45,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z8", "name": "Nakhatrana Block", "type": "village", "x": 420, "y": 240,
             "population": 100, "status": "safe", "injured_critical": 5, "injured_moderate": 15,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z9", "name": "Lakhpat Border", "type": "village", "x": 30, "y": 300,
             "population": 80, "status": "damaged", "injured_critical": 8, "injured_moderate": 15,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z10", "name": "Abdasa Rural", "type": "village", "x": 480, "y": 300,
             "population": 120, "status": "safe", "injured_critical": 3, "injured_moderate": 10,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "H1", "name": "GK General Hospital", "type": "hospital", "x": 200, "y": 300,
             "capacity": 300, "current_patients": 100, "has_power": True, "is_damaged": False},
            {"id": "H2", "name": "Bhuj Civil Hospital", "type": "hospital", "x": 120, "y": 150,
             "capacity": 150, "current_patients": 50, "has_power": True, "is_damaged": False},
            {"id": "H3", "name": "Gandhidham PHC", "type": "hospital", "x": 350, "y": 250,
             "capacity": 80, "current_patients": 10, "has_power": True, "is_damaged": False},
            {"id": "HELI1", "name": "IAF Bhuj Helipad", "type": "helipad", "x": 100, "y": 100,
             "population": 0, "status": "safe"},
            {"id": "HELI2", "name": "Kandla Port Helipad", "type": "helipad", "x": 280, "y": 280,
             "population": 0, "status": "safe"},
            {"id": "S1", "name": "Relief Camp Bhuj", "type": "shelter", "x": 140, "y": 350,
             "capacity": 500, "current_occupants": 100},
            {"id": "S2", "name": "Relief Camp Gandhidham", "type": "shelter", "x": 380, "y": 340,
             "capacity": 400, "current_occupants": 50},
        ],
        "edges": [
            {"id": "R1", "from": "BASE", "to": "Z1", "status": "damaged", "travel_time": 4.0},
            {"id": "R2", "from": "Z1", "to": "Z2", "status": "open", "travel_time": 2.0},
            {"id": "R3", "from": "Z2", "to": "Z3", "status": "open", "travel_time": 3.0},
            {"id": "R4", "from": "Z3", "to": "Z4", "status": "open", "travel_time": 2.5},
            {"id": "R5", "from": "Z1", "to": "Z5", "status": "damaged", "travel_time": 3.0},
            {"id": "R6", "from": "Z5", "to": "Z6", "status": "open", "travel_time": 2.0},
            {"id": "R7", "from": "Z6", "to": "Z7", "status": "open", "travel_time": 2.5},
            {"id": "R8", "from": "Z7", "to": "Z8", "status": "open", "travel_time": 2.0},
            {"id": "R9", "from": "Z5", "to": "Z9", "status": "damaged", "travel_time": 4.0},
            {"id": "R10", "from": "Z8", "to": "Z10", "status": "open", "travel_time": 3.0},
            {"id": "R11", "from": "BASE", "to": "H1", "status": "open", "travel_time": 1.0},
            {"id": "R12", "from": "Z1", "to": "H2", "status": "open", "travel_time": 1.5},
            {"id": "R13", "from": "Z7", "to": "H3", "status": "open", "travel_time": 1.0},
            {"id": "R14", "from": "BASE", "to": "HELI1", "status": "open", "travel_time": 0.5},
            {"id": "R15", "from": "BASE", "to": "HELI2", "status": "open", "travel_time": 0.5},
            {"id": "R16", "from": "H1", "to": "S1", "status": "open", "travel_time": 1.0},
            {"id": "R17", "from": "H3", "to": "S2", "status": "open", "travel_time": 1.0},
            {"id": "R18", "from": "Z2", "to": "Z6", "status": "open", "travel_time": 3.5},
            {"id": "R19", "from": "BASE", "to": "Z7", "status": "open", "travel_time": 2.0},
            {"id": "R20", "from": "Z4", "to": "Z8", "status": "open", "travel_time": 2.5},
        ],
        "initial_resources": {
            "food_units": 1500, "water_units": 1200, "medicine_units": 800, "tents": 200,
            "fuel_helicopter": 15.0, "boats_available": 2, "trucks_available": 6,
            "helicopters_available": 3, "budget_remaining": 100.0,
            "max_food": 1500, "max_water": 1200, "max_medicine": 800, "max_fuel": 15.0,
        },
        "initial_teams": [
            {"team_id": "NDRF-Alpha", "team_type": "rescue", "transport": "truck", "current_zone": "BASE"},
            {"team_id": "NDRF-Bravo", "team_type": "rescue", "transport": "truck", "current_zone": "BASE"},
            {"team_id": "NDRF-Charlie", "team_type": "rescue", "transport": "foot", "current_zone": "BASE"},
            {"team_id": "NDRF-Delta", "team_type": "rescue", "transport": "truck", "current_zone": "BASE"},
            {"team_id": "Med-Unit-1", "team_type": "medical", "transport": "truck", "current_zone": "H1"},
            {"team_id": "Med-Unit-2", "team_type": "medical", "transport": "truck", "current_zone": "H2"},
            {"team_id": "Med-Unit-3", "team_type": "medical", "transport": "truck", "current_zone": "H3"},
            {"team_id": "Scout-1", "team_type": "scout", "transport": "helicopter", "current_zone": "BASE"},
            {"team_id": "Supply-1", "team_type": "supply", "transport": "truck", "current_zone": "BASE"},
        ],
        "event_schedule": [
            {"hour": 12, "type": "comms_down", "zones": ["Z3", "Z4"],
             "description": "Cell towers in Bachau and Rapar collapse. Zones go DARK."},
            {"hour": 18, "type": "aftershock", "roads_blocked": ["R3", "R5", "R9"],
             "hospital_damaged": "H2",
             "description": "6.1 aftershock! Roads R3, R5, R9 blocked. Bhuj Civil Hospital damaged. 50 new casualties in Z1."},
            {"hour": 30, "type": "road_clears", "road_id": "R5",
             "description": "Debris cleared from Road R5. Route to Mandvi Coast reopened."},
            {"hour": 36, "type": "ndrf_reinforcement",
             "description": "NDRF 2nd Battalion arrives. 2 additional rescue teams + 1 helicopter."},
        ],
        "random_event_chance": 0.06,
        "grading_config": {
            "rescue_weight": 0.30, "time_weight": 0.10, "resource_efficiency_weight": 0.10,
            "equity_weight": 0.15, "rerouting_weight": 0.10,
            "comms_recovery_weight": 0.10, "aftershock_response_weight": 0.15,
        },
    },

    # ==================== TASK 4: EXPERT ====================
    "full_72hr_operation": {
        "display_name": "Full 72-Hour Super Cyclone Operation (Tamil Nadu)",
        "difficulty": "expert",
        "description": "Super cyclone + flooding in Tamil Nadu. 12 zones, 5000+ people, 72-hour window. 3 phases: Rescue(0-24h), Relief(24-48h), Rehabilitation(48-72h). Multiple dynamic events.",
        "max_steps": 80,
        "max_hours": 72,
        "population_total": 5200,
        "nodes": [
            {"id": "BASE", "name": "Chennai Command Center", "type": "base", "x": 260, "y": 360,
             "population": 0, "status": "safe", "injured_critical": 0, "injured_moderate": 0,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z1", "name": "Marina Beach Area", "type": "village", "x": 80, "y": 60,
             "population": 800, "status": "flooded", "injured_critical": 80, "injured_moderate": 150,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z2", "name": "Mylapore Ward", "type": "village", "x": 180, "y": 100,
             "population": 600, "status": "flooded", "injured_critical": 50, "injured_moderate": 100,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z3", "name": "Adyar River Belt", "type": "village", "x": 320, "y": 80,
             "population": 500, "status": "flooded", "injured_critical": 45, "injured_moderate": 90,
             "has_communication": False, "last_contact_hours_ago": 6},
            {"id": "Z4", "name": "Velachery Low-Lying", "type": "village", "x": 420, "y": 130,
             "population": 700, "status": "flooded", "injured_critical": 70, "injured_moderate": 120,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z5", "name": "Tambaram Suburbs", "type": "village", "x": 100, "y": 200,
             "population": 400, "status": "damaged", "injured_critical": 30, "injured_moderate": 60,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z6", "name": "Sholinganallur IT Corridor", "type": "village", "x": 460, "y": 220,
             "population": 350, "status": "damaged", "injured_critical": 20, "injured_moderate": 50,
             "has_communication": False, "last_contact_hours_ago": 4},
            {"id": "Z7", "name": "Perungudi Marsh", "type": "village", "x": 350, "y": 200,
             "population": 300, "status": "flooded", "injured_critical": 25, "injured_moderate": 55,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z8", "name": "Porur Lake Overflow", "type": "village", "x": 50, "y": 300,
             "population": 280, "status": "flooded", "injured_critical": 20, "injured_moderate": 45,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z9", "name": "Pallavaram Hill", "type": "village", "x": 200, "y": 260,
             "population": 200, "status": "safe", "injured_critical": 5, "injured_moderate": 20,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z10", "name": "Chromepet Industrial", "type": "village", "x": 300, "y": 290,
             "population": 250, "status": "damaged", "injured_critical": 15, "injured_moderate": 35,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "Z11", "name": "Mahabalipuram Coast", "type": "village", "x": 480, "y": 320,
             "population": 450, "status": "flooded", "injured_critical": 40, "injured_moderate": 80,
             "has_communication": False, "last_contact_hours_ago": 8},
            {"id": "Z12", "name": "Kanchipuram Outskirts", "type": "village", "x": 150, "y": 340,
             "population": 370, "status": "damaged", "injured_critical": 25, "injured_moderate": 55,
             "has_communication": True, "last_contact_hours_ago": 0},
            {"id": "H1", "name": "Rajiv Gandhi GH", "type": "hospital", "x": 220, "y": 180,
             "capacity": 500, "current_patients": 200, "has_power": True, "is_damaged": False},
            {"id": "H2", "name": "Apollo Greams Road", "type": "hospital", "x": 130, "y": 140,
             "capacity": 200, "current_patients": 80, "has_power": True, "is_damaged": False},
            {"id": "H3", "name": "Chromepet GH", "type": "hospital", "x": 350, "y": 310,
             "capacity": 150, "current_patients": 30, "has_power": True, "is_damaged": False},
            {"id": "HELI1", "name": "Tambaram AFB Helipad", "type": "helipad", "x": 100, "y": 250,
             "population": 0, "status": "safe"},
            {"id": "HELI2", "name": "Marina Helipad", "type": "helipad", "x": 60, "y": 100,
             "population": 0, "status": "safe"},
            {"id": "S1", "name": "YMCA Relief Camp", "type": "shelter", "x": 180, "y": 320,
             "capacity": 800, "current_occupants": 200},
            {"id": "S2", "name": "Trade Centre Shelter", "type": "shelter", "x": 400, "y": 350,
             "capacity": 600, "current_occupants": 100},
        ],
        "edges": [
            {"id": "R1", "from": "BASE", "to": "Z1", "status": "flooded", "travel_time": 3.0},
            {"id": "R2", "from": "Z1", "to": "Z2", "status": "flooded", "travel_time": 2.0},
            {"id": "R3", "from": "Z2", "to": "Z3", "status": "flooded", "travel_time": 3.0},
            {"id": "R4", "from": "Z3", "to": "Z4", "status": "open", "travel_time": 2.5},
            {"id": "R5", "from": "Z4", "to": "Z6", "status": "open", "travel_time": 2.0},
            {"id": "R6", "from": "Z4", "to": "Z7", "status": "flooded", "travel_time": 1.5},
            {"id": "R7", "from": "BASE", "to": "Z5", "status": "open", "travel_time": 2.0},
            {"id": "R8", "from": "Z5", "to": "Z8", "status": "flooded", "travel_time": 3.5},
            {"id": "R9", "from": "Z5", "to": "Z9", "status": "open", "travel_time": 1.5},
            {"id": "R10", "from": "Z9", "to": "Z10", "status": "open", "travel_time": 2.0},
            {"id": "R11", "from": "Z10", "to": "Z7", "status": "open", "travel_time": 1.5},
            {"id": "R12", "from": "Z6", "to": "Z11", "status": "flooded", "travel_time": 4.0},
            {"id": "R13", "from": "BASE", "to": "Z12", "status": "open", "travel_time": 2.5},
            {"id": "R14", "from": "Z2", "to": "H2", "status": "open", "travel_time": 1.0},
            {"id": "R15", "from": "BASE", "to": "H1", "status": "open", "travel_time": 1.0},
            {"id": "R16", "from": "Z10", "to": "H3", "status": "open", "travel_time": 1.0},
            {"id": "R17", "from": "BASE", "to": "HELI1", "status": "open", "travel_time": 0.5},
            {"id": "R18", "from": "Z1", "to": "HELI2", "status": "open", "travel_time": 0.5},
            {"id": "R19", "from": "H1", "to": "S1", "status": "open", "travel_time": 1.0},
            {"id": "R20", "from": "H3", "to": "S2", "status": "open", "travel_time": 1.0},
            {"id": "R21", "from": "Z12", "to": "H1", "status": "open", "travel_time": 2.0},
            {"id": "R22", "from": "Z7", "to": "H3", "status": "open", "travel_time": 1.5},
            {"id": "R23", "from": "Z8", "to": "Z12", "status": "damaged", "travel_time": 3.0},
            {"id": "R24", "from": "Z9", "to": "Z12", "status": "open", "travel_time": 2.0},
        ],
        "initial_resources": {
            "food_units": 3000, "water_units": 2500, "medicine_units": 1500, "tents": 400,
            "fuel_helicopter": 25.0, "boats_available": 5, "trucks_available": 8,
            "helicopters_available": 4, "budget_remaining": 100.0,
            "max_food": 3000, "max_water": 2500, "max_medicine": 1500, "max_fuel": 25.0,
        },
        "initial_teams": [
            {"team_id": "NDRF-Alpha", "team_type": "rescue", "transport": "boat", "current_zone": "BASE"},
            {"team_id": "NDRF-Bravo", "team_type": "rescue", "transport": "boat", "current_zone": "BASE"},
            {"team_id": "NDRF-Charlie", "team_type": "rescue", "transport": "truck", "current_zone": "BASE"},
            {"team_id": "NDRF-Delta", "team_type": "rescue", "transport": "truck", "current_zone": "BASE"},
            {"team_id": "NDRF-Echo", "team_type": "rescue", "transport": "foot", "current_zone": "BASE"},
            {"team_id": "Med-Unit-1", "team_type": "medical", "transport": "truck", "current_zone": "H1"},
            {"team_id": "Med-Unit-2", "team_type": "medical", "transport": "truck", "current_zone": "H2"},
            {"team_id": "Med-Unit-3", "team_type": "medical", "transport": "truck", "current_zone": "H3"},
            {"team_id": "Med-Unit-4", "team_type": "medical", "transport": "helicopter", "current_zone": "BASE"},
            {"team_id": "Scout-1", "team_type": "scout", "transport": "helicopter", "current_zone": "BASE"},
            {"team_id": "Scout-2", "team_type": "scout", "transport": "helicopter", "current_zone": "BASE"},
            {"team_id": "Supply-1", "team_type": "supply", "transport": "truck", "current_zone": "BASE"},
            {"team_id": "Supply-2", "team_type": "supply", "transport": "boat", "current_zone": "BASE"},
        ],
        "event_schedule": [
            {"hour": 6, "type": "new_survivors", "zone_id": "Z7", "extra_population": 40,
             "description": "Drone spots 40 people on rooftop in Perungudi Marsh — not on original manifest!"},
            {"hour": 12, "type": "comms_down", "zones": ["Z3"],
             "description": "Cell tower in Adyar collapses. Zone Z3 goes DARK."},
            {"hour": 18, "type": "aftershock", "roads_blocked": ["R3", "R8"],
             "hospital_damaged": "H2",
             "description": "Aftershock! Roads R3, R8 blocked. Apollo Hospital damaged. 60 new casualties."},
            {"hour": 24, "type": "phase_transition", "new_phase": "relief",
             "description": "PHASE TRANSITION: Rescue → Relief. Priority shifts to medical and food distribution."},
            {"hour": 30, "type": "supply_delay",
             "description": "Resupply helicopter delayed 8 hours due to weather. Ration existing supplies."},
            {"hour": 36, "type": "road_clears", "road_id": "R3",
             "description": "Debris cleared from Road R3. Route to Adyar reopened."},
            {"hour": 40, "type": "volunteer_arrival", "extra_teams": 2,
             "description": "20 civilian volunteers arrive at Chennai Command. 2 new supply teams available."},
            {"hour": 48, "type": "phase_transition", "new_phase": "rehabilitation",
             "description": "PHASE TRANSITION: Relief → Rehabilitation. Priority shifts to shelter and infrastructure."},
            {"hour": 54, "type": "ndrf_reinforcement",
             "description": "NDRF 5th Battalion arrives. 3 additional teams + 1 helicopter."},
            {"hour": 60, "type": "road_clears", "road_id": "R8",
             "description": "Road R8 cleared. Route to Porur Lake reopened."},
        ],
        "random_event_chance": 0.08,
        "grading_config": {
            "rescue_weight": 0.20, "time_weight": 0.08, "resource_efficiency_weight": 0.08,
            "equity_weight": 0.12, "rerouting_weight": 0.08,
            "comms_recovery_weight": 0.08, "aftershock_response_weight": 0.10,
            "phase_transition_weight": 0.10, "self_improvement_weight": 0.08,
            "long_horizon_planning_weight": 0.08,
        },
    },
}


# ==================== RANDOM EVENT GENERATOR ====================
RANDOM_EVENTS = [
    {"type": "road_floods", "description": "Sudden flooding on road {road_id}. Trucks cannot pass."},
    {"type": "hospital_overflow", "description": "Hospital {hospital_id} at 100% capacity. Divert patients."},
    {"type": "comms_down", "description": "Cell tower failure. Zone {zone_id} goes dark."},
    {"type": "new_survivors", "description": "Drone discovers {count} survivors in {zone_id}."},
    {"type": "supply_delay", "description": "Supply delivery delayed by {hours} hours."},
    {"type": "road_clears", "description": "Floodwater recedes. Road {road_id} passable again."},
    {"type": "volunteer_arrival", "description": "{count} volunteers arrive at base camp."},
]


def generate_random_event(state: dict) -> dict:
    """Generate a random dynamic event based on current state."""
    event_template = random.choice(RANDOM_EVENTS)
    event = {"type": event_template["type"], "description": event_template["description"]}

    zones = state.get("zones", [])
    roads = state.get("edges", []) or state.get("roads", [])
    hospitals = state.get("hospitals", [])

    if event["type"] == "road_floods":
        open_roads = [r for r in roads if r.get("status") == "open"]
        if open_roads:
            road = random.choice(open_roads)
            road_id = road.get("road_id", road.get("id", "R?"))
            event["road_id"] = road_id
            event["description"] = event["description"].format(road_id=road_id)
        else:
            return None
    elif event["type"] == "hospital_overflow":
        hosp = [h for h in hospitals if h.get("current_patients", 0) > 0]
        if hosp:
            h = random.choice(hosp)
            event["hospital_id"] = h.get("hospital_id", h.get("id", "H?"))
            event["description"] = event["description"].format(hospital_id=event["hospital_id"])
        else:
            return None
    elif event["type"] == "comms_down":
        comm_zones = [z for z in zones if z.get("has_communication", True) and z.get("population", 0) > 0]
        if comm_zones:
            z = random.choice(comm_zones)
            event["zone_id"] = z.get("zone_id", z.get("id", "Z?"))
            event["description"] = event["description"].format(zone_id=event["zone_id"])
        else:
            return None
    elif event["type"] == "new_survivors":
        count = random.randint(10, 50)
        z = random.choice([z for z in zones if z.get("population", 0) > 0]) if zones else None
        if z:
            event["zone_id"] = z.get("zone_id", z.get("id", "Z?"))
            event["count"] = count
            event["description"] = event["description"].format(count=count, zone_id=event["zone_id"])
        else:
            return None
    elif event["type"] == "supply_delay":
        hours = random.randint(4, 12)
        event["hours"] = hours
        event["description"] = event["description"].format(hours=hours)
    elif event["type"] == "road_clears":
        blocked = [r for r in roads if r.get("status") in ("blocked", "flooded")]
        if blocked:
            road = random.choice(blocked)
            road_id = road.get("road_id", road.get("id", "R?"))
            event["road_id"] = road_id
            event["description"] = event["description"].format(road_id=road_id)
        else:
            return None
    elif event["type"] == "volunteer_arrival":
        count = random.randint(5, 20)
        event["count"] = count
        event["description"] = event["description"].format(count=count)

    return event


# ==================== HELPER FUNCTIONS ====================
def get_task_config(task_id: str) -> dict:
    """Return a DEEP COPY of task config so original is never modified."""
    if task_id not in TASK_CONFIGS:
        available = list(TASK_CONFIGS.keys())
        raise ValueError(f"Unknown task: {task_id}. Available: {available}")
    return copy.deepcopy(TASK_CONFIGS[task_id])


def get_available_tasks() -> List[dict]:
    """Return list of {id, difficulty, description, display_name} for all tasks."""
    return [
        {
            "id": k,
            "difficulty": v["difficulty"],
            "description": v["description"],
            "display_name": v["display_name"],
            "population": v["population_total"],
            "max_hours": v["max_hours"],
        }
        for k, v in TASK_CONFIGS.items()
    ]
