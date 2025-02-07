# src/traffic_light/light_manager.py
import traci
import logging
from typing import List, Dict, Any
from emergency_vehicle.vehicle_detector import EmergencyVehicleManager

class TrafficLightManager:
    def __init__(self, emergency_vehicle_manager: EmergencyVehicleManager):
        """
        Initialize Traffic Light Manager
        
        :param emergency_vehicle_manager: Manager for emergency vehicles
        """
        self.logger = logging.getLogger(__name__)
        self.emergency_vehicle_manager = emergency_vehicle_manager
        self.original_states: Dict[str, Dict[str, Any]] = {}
    
    def manage_traffic_lights(self):
        """
        Manage traffic lights for emergency vehicles
        """
        try:
            emergency_vehicles = self.emergency_vehicle_manager.detect_emergency_vehicles()
            
            for vehicle_id in emergency_vehicles:
                next_junction = self.emergency_vehicle_manager.get_vehicle_next_junction(vehicle_id)
                
                if next_junction:
                    junction_id, priority_lanes = next_junction
                    self._set_junction_priority(junction_id, priority_lanes)
        
        except Exception as e:
            self.logger.error(f"Error managing traffic lights: {e}")
    
    def _set_junction_priority(self, junction_id: str, priority_lanes: List[str]):
        """
        Set specific lanes to green for emergency vehicle
        
        :param junction_id: Traffic light cluster ID
        :param priority_lanes: Lanes to set green
        """
        try:
            # Capture original state if not already done
            if junction_id not in self.original_states:
                self._capture_original_state(junction_id)
            
            # Get current traffic light logic
            logic = traci.trafficlight.getCompleteRedYellowGreenDefinition(junction_id)[0]
            
            # Modify phases to prioritize emergency vehicle lanes
            for phase in logic.phases:
                # Convert all signal states to red first
                modified_state = ''.join(['r' if char in 'Gg' else char for char in phase.state])
                
                # Set priority lanes to green
                for lane in priority_lanes:
                    modified_state = modified_state.replace('r', 'G', 1)
                
                phase.state = modified_state
            
            # Apply modified traffic light logic
            traci.trafficlight.setCompleteRedYellowGreenDefinition(junction_id, logic)
        
        except Exception as e:
            self.logger.error(f"Error setting junction priority for {junction_id}: {e}")
    
    def _capture_original_state(self, junction_id: str):
        """
        Store original traffic light state for restoration
        
        :param junction_id: Traffic light cluster ID to capture
        """
        try:
            original_logic = traci.trafficlight.getCompleteRedYellowGreenDefinition(junction_id)[0]
            original_program = traci.trafficlight.getProgram(junction_id)
            
            self.original_states[junction_id] = {
                'logic': original_logic,
                'program': original_program
            }
        
        except Exception as e:
            self.logger.error(f"Error capturing original state for {junction_id}: {e}")
    
    def restore_traffic_lights(self):
        """
        Restore all captured traffic light states to their original configuration
        """
        for junction_id, state in self.original_states.items():
            try:
                traci.trafficlight.setCompleteRedYellowGreenDefinition(
                    junction_id, 
                    state['logic']
                )
                traci.trafficlight.setProgram(
                    junction_id, 
                    state['program']
                )
            except Exception as e:
                self.logger.error(f"Error restoring traffic light state for {junction_id}: {e}")