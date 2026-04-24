import networkx as nx
from server.models import RoadStatus, TransportType


class CrisisGraph:
    """Graph-based crisis zone map using NetworkX.
    Nodes = locations (villages, hospitals, bases, helipads, shelters)
    Edges = roads with status (open, flooded, blocked, damaged)
    Teams move along edges. Road status changes dynamically during episodes.
    """

    def __init__(self):
        self.G = nx.Graph()
        self.node_positions = {}

    def build_from_task(self, task_config: dict) -> None:
        """Build graph from task configuration.
        task_config has 'nodes' list and 'edges' list.
        Each node: {id, name, type, x, y, population, status, ...}
        Each edge: {id, from, to, status, travel_time}
        """
        try:
            self.G.clear()
            self.node_positions.clear()
            if not isinstance(task_config, dict):
                return

            for node in task_config.get("nodes", []):
                try:
                    node_id = node["id"]
                    self.G.add_node(node_id, **node)
                    self.node_positions[node_id] = (node.get("x", 0), node.get("y", 0))
                except Exception:
                    continue

            for edge in task_config.get("edges", []):
                try:
                    src = edge["from"]
                    dst = edge["to"]
                    edge_id = edge.get("id", f"{src}-{dst}")
                    status = edge.get("status", RoadStatus.OPEN.value)
                    if status not in {s.value for s in RoadStatus}:
                        status = RoadStatus.OPEN.value
                    self.G.add_edge(
                        src,
                        dst,
                        id=edge_id,
                        road_id=edge_id,
                        status=status,
                        travel_time=edge.get("travel_time", 1.0),
                    )
                except Exception:
                    continue
        except Exception:
            # Keep a valid, empty graph on unexpected failures.
            self.G = nx.Graph()
            self.node_positions = {}

    def get_shortest_path(self, source: str, destination: str, transport: TransportType):
        """Find shortest path considering road status and transport type.
        TRUCK: only OPEN roads
        BOAT: OPEN and FLOODED roads
        HELICOPTER: direct [source, destination] always (no road needed)
        FOOT: any road except where status is 'blocked' with no alternate
        Returns list of node IDs or None if unreachable.
        """
        try:
            if source not in self.G or destination not in self.G:
                return None

            if transport == TransportType.HELICOPTER:
                return [source, destination]

            allowed_edges = []
            for u, v, data in self.G.edges(data=True):
                status = data.get("status", RoadStatus.OPEN.value)
                if transport == TransportType.TRUCK:
                    if status == RoadStatus.OPEN.value:
                        allowed_edges.append((u, v, data))
                elif transport == TransportType.BOAT:
                    if status in (RoadStatus.OPEN.value, RoadStatus.FLOODED.value):
                        allowed_edges.append((u, v, data))
                elif transport == TransportType.FOOT:
                    if status != RoadStatus.BLOCKED.value:
                        allowed_edges.append((u, v, data))
                else:
                    if status == RoadStatus.OPEN.value:
                        allowed_edges.append((u, v, data))

            subgraph = nx.Graph()
            subgraph.add_nodes_from(self.G.nodes())
            for u, v, data in allowed_edges:
                subgraph.add_edge(u, v, **data)

            return nx.shortest_path(subgraph, source, destination, weight="travel_time")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
        except Exception:
            return None

    def get_travel_time(self, source: str, destination: str, transport: TransportType) -> float:
        """Calculate travel time in hours.
        HELICOPTER: 0.5 hours anywhere
        TRUCK: sum of edge travel_times on shortest path
        BOAT: sum of edge travel_times * 1.5
        FOOT: sum of edge travel_times * 3.0
        Returns -1.0 if no path exists.
        """
        try:
            if transport == TransportType.HELICOPTER:
                return 0.5

            path = self.get_shortest_path(source, destination, transport)
            if path is None or len(path) < 2:
                return -1.0

            multiplier = {
                TransportType.TRUCK.value: 1.0,
                TransportType.BOAT.value: 1.5,
                TransportType.FOOT.value: 3.0,
            }.get(transport.value, 1.0)

            total_time = 0.0
            for i in range(len(path) - 1):
                edge_data = self.G.get_edge_data(path[i], path[i + 1], default={})
                total_time += float(edge_data.get("travel_time", 1.0)) * multiplier
            return round(total_time, 1)
        except Exception:
            return -1.0

    def block_road(self, road_id: str) -> bool:
        """Set a road's status to BLOCKED. Returns True if found."""
        try:
            for u, v, data in self.G.edges(data=True):
                if data.get("road_id") == road_id or data.get("id") == road_id:
                    self.G[u][v]["status"] = RoadStatus.BLOCKED.value
                    return True
            return False
        except Exception:
            return False

    def flood_road(self, road_id: str) -> bool:
        """Set a road's status to FLOODED."""
        try:
            for u, v, data in self.G.edges(data=True):
                if data.get("road_id") == road_id or data.get("id") == road_id:
                    self.G[u][v]["status"] = RoadStatus.FLOODED.value
                    return True
            return False
        except Exception:
            return False

    def clear_road(self, road_id: str) -> bool:
        """Set a road's status to OPEN."""
        try:
            for u, v, data in self.G.edges(data=True):
                if data.get("road_id") == road_id or data.get("id") == road_id:
                    self.G[u][v]["status"] = RoadStatus.OPEN.value
                    return True
            return False
        except Exception:
            return False

    def get_road_status(self, road_id: str):
        """Get current status of a road."""
        try:
            for _, _, data in self.G.edges(data=True):
                if data.get("road_id") == road_id or data.get("id") == road_id:
                    return data.get("status", RoadStatus.OPEN.value)
            return None
        except Exception:
            return None

    def damage_hospital(self, node_id: str) -> bool:
        """Mark a hospital node as damaged."""
        try:
            if node_id in self.G:
                self.G.nodes[node_id]["is_damaged"] = True
                self.G.nodes[node_id]["has_power"] = False
                return True
            return False
        except Exception:
            return False

    def get_reachable_zones(self, from_zone: str, transport: TransportType) -> list:
        """Return all zone_ids reachable from given zone with given transport."""
        try:
            if from_zone not in self.G:
                return []

            if transport == TransportType.HELICOPTER:
                return [n for n in self.G.nodes() if n != from_zone]

            reachable = []
            for node in self.G.nodes():
                if node == from_zone:
                    continue
                path = self.get_shortest_path(from_zone, node, transport)
                if path is not None:
                    reachable.append(node)
            return reachable
        except Exception:
            return []

    def update_node_data(self, node_id: str, **kwargs) -> bool:
        """Update attributes of a node."""
        try:
            if node_id in self.G:
                for key, value in kwargs.items():
                    self.G.nodes[node_id][key] = value
                return True
            return False
        except Exception:
            return False

    def get_node_data(self, node_id: str):
        """Get all data for a node."""
        try:
            if node_id in self.G:
                return dict(self.G.nodes[node_id])
            return None
        except Exception:
            return None

    def to_dashboard_data(self, teams: list = None) -> dict:
        """Export graph data for frontend SVG visualization.
        Returns dict with 'nodes', 'edges', and 'teams' for the dashboard.
        """
        try:
            nodes = []
            for node_id, data in self.G.nodes(data=True):
                try:
                    pos = self.node_positions.get(node_id, (0, 0))
                    capacity = max(data.get("capacity", 1), 1)
                    current_patients = data.get("current_patients", 0)
                    nodes.append(
                        {
                            "id": node_id,
                            "name": data.get("name", node_id),
                            "type": data.get("type", "unknown"),
                            "x": pos[0],
                            "y": pos[1],
                            "population": data.get("population", 0),
                            "status": data.get("status", "safe"),
                            "injured_critical": data.get("injured_critical", 0),
                            "capacity": data.get("capacity", 0),
                            "current_patients": current_patients,
                            "capacity_pct": round((current_patients / capacity) * 100, 1)
                            if data.get("type") == "hospital"
                            else 0,
                            "is_damaged": data.get("is_damaged", False),
                        }
                    )
                except Exception:
                    continue

            edges = []
            for u, v, data in self.G.edges(data=True):
                try:
                    edges.append(
                        {
                            "id": data.get("road_id", data.get("id", f"{u}-{v}")),
                            "from_zone": u,
                            "to_zone": v,
                            "status": data.get("status", RoadStatus.OPEN.value),
                            "travel_time": data.get("travel_time", 1.0),
                        }
                    )
                except Exception:
                    continue

            team_data = []
            if teams:
                for t in teams:
                    try:
                        if isinstance(t, dict):
                            team_dict = t
                        elif hasattr(t, "dict"):
                            team_dict = t.dict()
                        elif hasattr(t, "model_dump"):
                            team_dict = t.model_dump()
                        else:
                            team_dict = {}

                        current_zone = team_dict.get("current_zone", "BASE")
                        destination = team_dict.get("destination")
                        pos = self.node_positions.get(current_zone, (250, 250))

                        if (
                            destination
                            and destination in self.node_positions
                            and team_dict.get("status") == "moving"
                        ):
                            dest_pos = self.node_positions.get(destination, pos)
                            eta = float(team_dict.get("eta_hours", 1) or 1)
                            progress = max(0, min(1, 1 - (eta / max(eta + 0.1, 0.1))))
                            interp_x = pos[0] + (dest_pos[0] - pos[0]) * progress
                            interp_y = pos[1] + (dest_pos[1] - pos[1]) * progress
                            pos = (round(interp_x, 1), round(interp_y, 1))

                        team_data.append(
                            {
                                "id": team_dict.get("team_id", "unknown"),
                                "type": team_dict.get("team_type", "rescue"),
                                "current_x": pos[0],
                                "current_y": pos[1],
                                "destination": destination,
                                "status": team_dict.get("status", "idle"),
                            }
                        )
                    except Exception:
                        continue

            return {"nodes": nodes, "edges": edges, "teams": team_data}
        except Exception:
            return {"nodes": [], "edges": [], "teams": []}
