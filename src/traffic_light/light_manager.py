import traci
import logging
from typing import List, Dict, Any, Optional, Set
from emergency_vehicle.vehicle_detector import EmergencyVehicleManager
import math
class TrafficLightManager:
    def __init__(self, emergency_vehicle_manager: EmergencyVehicleManager):
        """
        Initialize Traffic Light Manager
        
        :param emergency_vehicle_manager: Manager for emergency vehicles
        """
        self.logger = logging.getLogger(__name__)
        self.emergency_vehicle_manager = emergency_vehicle_manager
        self.original_states: Dict[str, Dict[str, Any]] = {}
        self.active_emergency_junctions: Set[str] = set()
        self.MIN_PHASE_DURATION = 5  # Minimum phase duration in seconds
    
    def manage_traffic_lights(self):
        """
        Change traffic lights when emergency vehicle is within distance threshold
        and restore once it has passed.
        """
        try:
            emergency_vehicles = self.emergency_vehicle_manager.detect_emergency_vehicles()
            current_emergency_junctions = set()

            for vehicle_id in emergency_vehicles:
                ev_position = traci.vehicle.getPosition(vehicle_id)

                # Get nearest junction
                nearest_junction = min(
                    self.emergency_vehicle_manager.all_junctions, 
                    key=lambda j: math.dist(ev_position, self.route_predictor.get_junction_coords(j))
                )
                
                distance = math.dist(ev_position, self.route_predictor.get_junction_coords(nearest_junction))
                
                if distance < 50:  # Only activate if within 50m
                    current_emergency_junctions.add(nearest_junction)
                    self._set_junction_priority(nearest_junction, vehicle_id)

            # Restore any junctions that no longer have emergency vehicles nearby
            junctions_to_restore = self.active_emergency_junctions - current_emergency_junctions
            for junction_id in junctions_to_restore:
                self._restore_junction(junction_id)

            self.active_emergency_junctions = current_emergency_junctions

        except Exception as e:
            self.logger.error(f"Error managing traffic lights: {e}")

    def _get_controlled_lanes(self, junction_id: str) -> List[str]:
        """Get all lanes controlled by this traffic light"""
        try:
            return traci.trafficlight.getControlledLanes(junction_id)
        except Exception as e:
            self.logger.error(f"Error getting controlled lanes for junction {junction_id}: {e}")
            return []
    
    def _set_junction_priority(self, junction_id: str, priority_lanes: List[str], vehicle_id: str):
        """
        Set specific lanes to green for emergency vehicle
        
        :param junction_id: Traffic light cluster ID
        :param priority_lanes: Lanes to set green
        :param vehicle_id: ID of the emergency vehicle
        """
        try:
            # Capture original state if not already done
            if junction_id not in self.original_states:
                self._capture_original_state(junction_id)
            
            # Get all lanes controlled by this traffic light
            controlled_lanes = self._get_controlled_lanes(junction_id)
            
            # Get vehicle's current lane and next lane
            current_lane = traci.vehicle.getLaneID(vehicle_id)
            route_edges = traci.vehicle.getRoute(vehicle_id)
            current_edge_index = route_edges.index(traci.vehicle.getRoadID(vehicle_id))
            
            # Determine which lanes need to be green
            lanes_to_green = set()
            lanes_to_green.add(current_lane)
            
            # Add upcoming lanes from priority_lanes
            for lane_id in controlled_lanes:
                if any(priority_lane in lane_id for priority_lane in priority_lanes):
                    lanes_to_green.add(lane_id)
            
            # Create new traffic light state
            new_state = ""
            for lane in controlled_lanes:
                if lane in lanes_to_green:
                    new_state += "G"  # Green for priority lanes
                else:
                    new_state += "r"  # Red for other lanes
            
            # Set the new state with minimum duration
            # Get current traffic light program
            program_id = traci.trafficlight.getProgram(junction_id)
            phases = traci.trafficlight.getCompleteRedYellowGreenDefinition(junction_id)[0].phases

            # Find a phase where the emergency vehicle lane is green
            for i, phase in enumerate(phases):
                if "G" in phase.state:  # Adjust condition if needed
                    traci.trafficlight.setPhase(junction_id, i)
                    self.logger.debug(f"Changed {junction_id} to phase {i} for EV")
                    break
            traci.trafficlight.setPhaseDuration(junction_id, self.MIN_PHASE_DURATION)
            
            self.logger.debug(f"Set priority for junction {junction_id}, lanes {lanes_to_green}")
            
        except Exception as e:
            self.logger.error(f"Error setting junction priority for {junction_id}: {e}")
    
    def _capture_original_state(self, junction_id: str):
        """Store original traffic light state for restoration"""
        try:
            self.original_states[junction_id] = {
                'state': traci.trafficlight.getRedYellowGreenState(junction_id),
                'program': traci.trafficlight.getProgram(junction_id),
                'phase_duration': traci.trafficlight.getPhaseDuration(junction_id),
                'complete_definition': traci.trafficlight.getCompleteRedYellowGreenDefinition(junction_id)[0]
            }
        except Exception as e:
            self.logger.error(f"Error capturing original state for {junction_id}: {e}")
    
    def _restore_junction(self, junction_id: str):
        """Restore junction to original traffic state"""
        try:
            if junction_id in self.original_states:
                state = self.original_states[junction_id]
                traci.trafficlight.setProgram(junction_id, state['program'])
                traci.trafficlight.setPhase(junction_id, 0)  # Restore first phase
                del self.original_states[junction_id]
                self.logger.info(f"Restored junction {junction_id} to normal operation")

        except Exception as e:
            self.logger.error(f"Error restoring junction {junction_id}: {e}")
    
    def restore_traffic_lights(self):
        """Restore all traffic lights to their original states"""
        for junction_id in list(self.original_states.keys()):
            self._restore_junction(junction_id)