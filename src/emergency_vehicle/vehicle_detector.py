import traci
import math
from typing import Tuple, List

class EmergencyVehicleDetector:
    def __init__(self, target_cluster: str):
        self.target_cluster = target_cluster

    def detect_emergency_vehicles(self) -> List[str]:
        """Returns list of emergency vehicle IDs in simulation"""
        return [vid for vid in traci.vehicle.getIDList() if vid.startswith('emergency')]
    
    def calculate_distance(self, vehicle_id: str) -> float:
        """Calculate distance between vehicle and target cluster"""
        vehicle_pos = traci.vehicle.getPosition(vehicle_id)
        cluster_pos = traci.junction.getPosition(self.target_cluster)
        
        return math.sqrt(
            (vehicle_pos[0] - cluster_pos[0])**2 + 
            (vehicle_pos[1] - cluster_pos[1])**2
        )

    def set_emergency_vehicle_properties(self, vehicle_id: str):
        """Set special properties for emergency vehicles"""
        traci.vehicle.setLaneChangeMode(vehicle_id, 0)
        traci.vehicle.setSpeedMode(vehicle_id, 0)
