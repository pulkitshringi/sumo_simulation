# src/emergency_vehicle/vehicle_detector.py
import traci
import logging
from typing import List, Optional, Tuple
from emergency_vehicle.route_predictor import RoutePredictor

class EmergencyVehicleManager:
    def __init__(self, route_predictor: RoutePredictor):
        """
        Initialize Emergency Vehicle Manager
        
        :param route_predictor: RoutePredictor instance for network navigation
        """
        self.logger = logging.getLogger(__name__)
        self.route_predictor = route_predictor
        self.all_junctions = route_predictor.get_all_junctions()
    
    def detect_emergency_vehicles(self) -> List[str]:
        """
        Detect emergency vehicles in the simulation
        
        :return: List of emergency vehicle IDs
        """
        try:
            # Detect vehicles with emergency prefix or specific vehicle type
            all_vehicles = traci.vehicle.getIDList()
            emergency_vehicles = [
                vehicle for vehicle in all_vehicles 
                if vehicle.startswith('emergency_') or 
                   traci.vehicle.getVehicleClass(vehicle) == 'emergency'
            ]
            return emergency_vehicles
        
        except Exception as e:
            self.logger.error(f"Error detecting emergency vehicles: {e}")
            return []
    
    def get_vehicle_next_junction(self, vehicle_id: str) -> Optional[Tuple[str, List[str]]]:
        """
        Get the next junction for an emergency vehicle
        
        :param vehicle_id: ID of the emergency vehicle
        :return: Tuple of (junction_id, priority_lanes) or None
        """
        try:
            # Get current vehicle information
            current_edge = traci.vehicle.getRoadID(vehicle_id)
            
            # Handle edge cases
            if not current_edge:
                self.logger.warning(f"No current edge found for vehicle {vehicle_id}")
                return None
            
            # Get full route with error handling
            try:
                route = traci.vehicle.getRoute(vehicle_id)
            except traci.exceptions.TraCIException:
                self.logger.warning(f"Could not retrieve route for vehicle {vehicle_id}")
                return None
            
            # Convert route to list to handle potential tuple
            route = list(route)
            
            # Find current edge in route
            try:
                current_index = route.index(current_edge)
            except ValueError:
                # If current edge is not in route, use the first edge
                current_index = 0
            
            # Get next edge, handling route end
            if current_index + 1 < len(route):
                next_edge = route[current_index + 1]
                
                # Find connected junctions
                connected_junctions = [
                    j for j in self.all_junctions 
                    if any(edge.startswith(f"{j}_") for edge in route)
                ]
                
                # Fallback junction selection
                if not connected_junctions and self.all_junctions:
                    connected_junctions = [self.all_junctions[0]]
                
                if connected_junctions:
                    # Choose a junction (first available)
                    junction_id = connected_junctions[0]
                    
                    # Create priority lanes 
                    priority_lanes = [f"{current_edge}_{next_edge}"]
                    
                    return (junction_id, priority_lanes)
            
            return None
        
        except Exception as e:
            self.logger.error(f"Comprehensive error finding next junction for vehicle {vehicle_id}: {e}")
            return None