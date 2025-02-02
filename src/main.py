import traci
import time
import os
from typing import List
from emergency_vehicle.vehicle_detector import EmergencyVehicleDetector
from traffic_light.light_manager import TrafficLightManager
from utils import Logger, Config

class EmergencyTrafficControl:
    def __init__(self):
        self.config = Config()
        self.target_cluster = self.config.config['traffic_light']['target_cluster']
        self.detector = EmergencyVehicleDetector(self.target_cluster)
        self.light_manager = TrafficLightManager(self.target_cluster)
        self.logger = Logger(self.config.config['logging']['prefix'])
        self.emergency_detected = False
        self.last_emergency_time = 0
        self.distance_threshold = self.config.config['traffic_light']['emergency_distance_threshold']
        self.restoration_delay = self.config.config['traffic_light']['restoration_delay']

    def run(self):
        sumo_cmd = ["sumo-gui" if self.config.config['sumo']['gui_enabled'] else "sumo",
                    "-c", self.config.sumo_config_path]
        
        print(f"Starting SUMO with config: {self.config.sumo_config_path}")
        traci.start(sumo_cmd)
        
        try:
            self.light_manager.capture_original_state()
            
            while traci.simulation.getMinExpectedNumber() > 0:
                current_time = traci.simulation.getTime()
                traci.simulationStep()
                
                emergency_vehicles = self.detector.detect_emergency_vehicles()
                
                if emergency_vehicles:
                    self.handle_emergency_vehicles(emergency_vehicles, current_time)
                else:
                    self.check_restore_normal_traffic(current_time)
        
        except Exception as e:
            print(f"Simulation error: {e}")
        finally:
            traci.close()

    def handle_emergency_vehicles(self, emergency_vehicles: List[str], current_time: float):
        self.emergency_detected = True
        self.last_emergency_time = current_time
        
        for vehicle_id in emergency_vehicles:
            distance = self.detector.calculate_distance(vehicle_id)
            
            if distance < self.distance_threshold:
                self.detector.set_emergency_vehicle_properties(vehicle_id)
                self.light_manager.set_emergency_state()
                
                self.logger.log_event({
                    'timestamp': current_time,
                    'vehicle_id': vehicle_id,
                    'cluster': self.target_cluster,
                    'distance': f"{distance:.2f}",
                    'action': "Green Priority"
                })

    def check_restore_normal_traffic(self, current_time: float):
        if self.emergency_detected and (current_time - self.last_emergency_time > self.restoration_delay):
            try:
                self.light_manager.restore_normal_state()
                
                self.logger.log_event({
                    'timestamp': current_time,
                    'cluster': self.target_cluster,
                    'action': "Normal Traffic Restored"
                })
                
                self.emergency_detected = False
            except Exception as e:
                print(f"Restoration error: {e}")