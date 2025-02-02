import traci
from dataclasses import dataclass
from typing import Optional

@dataclass
class TrafficLightState:
    logic: any
    program: str
    complete_logic: any

class TrafficLightManager:
    def __init__(self, cluster_id: str):
        self.cluster_id = cluster_id
        self.original_state: Optional[TrafficLightState] = None

    def capture_original_state(self):
        """Store original traffic light state"""
        logic = traci.trafficlight.getCompleteRedYellowGreenDefinition(self.cluster_id)[0]
        self.original_state = TrafficLightState(
            logic=logic,
            program=traci.trafficlight.getProgram(self.cluster_id),
            complete_logic=logic
        )

    def set_emergency_state(self):
        """Set all lights to green for emergency vehicle"""
        logic = traci.trafficlight.getCompleteRedYellowGreenDefinition(self.cluster_id)[0]
        for phase in logic.phases:
            phase.state = ''.join(['G' if char in 'ruyG' else char for char in phase.state])
        traci.trafficlight.setCompleteRedYellowGreenDefinition(self.cluster_id, logic)

    def restore_normal_state(self):
        """Restore original traffic light state"""
        if self.original_state:
            traci.trafficlight.setCompleteRedYellowGreenDefinition(
                self.cluster_id, 
                self.original_state.complete_logic
            )
            traci.trafficlight.setProgram(
                self.cluster_id, 
                self.original_state.program
            )