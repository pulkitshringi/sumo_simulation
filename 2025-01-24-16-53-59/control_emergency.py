import traci
import csv
import time
import math

def run_emergency_vehicle():
    """
    Manage emergency vehicle traffic control for cluster_30037241_304918729
    """
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    csv_filename = f"emergency_vehicle_log_{timestamp}.csv"
    
    target_cluster = "cluster_30037241_304918729"
    
    # Store complete original traffic light state
    original_tl_state = None
    
    with open(csv_filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow([
            'Timestamp', 
            'Emergency Vehicle ID', 
            'Traffic Light Cluster', 
            'Distance', 
            'Action Taken'
        ])
        
        traci.start(["sumo-gui", "-c", "osm.sumocfg"])
        
        try:
            # Capture full original state before modification
            original_tl_logic = traci.trafficlight.getCompleteRedYellowGreenDefinition(target_cluster)[0]
            original_tl_state = {
                'logic': original_tl_logic,
                'program': traci.trafficlight.getProgram(target_cluster),
                'complete_logic': original_tl_logic
            }
            
            emergency_detected = False
            last_emergency_time = 0
            
            while traci.simulation.getMinExpectedNumber() > 0:
                current_time = traci.simulation.getTime()
                traci.simulationStep()
                
                # Find emergency vehicles
                emergency_vehicles = [
                    vid for vid in traci.vehicle.getIDList() 
                    if vid.startswith('emergency')
                ]
                
                if emergency_vehicles:
                    emergency_detected = True
                    last_emergency_time = current_time
                    
                    for emergency_vid in emergency_vehicles:
                        # Get emergency vehicle position
                        emergency_pos = traci.vehicle.getPosition(emergency_vid)
                        
                        # Get cluster position
                        cluster_pos = traci.junction.getPosition(target_cluster)
                        
                        # Calculate distance 
                        distance = math.sqrt(
                            (emergency_pos[0] - cluster_pos[0])**2 + 
                            (emergency_pos[1] - cluster_pos[1])**2
                        )
                        
                        # Priority and logging
                        if distance < 50:
                            traci.vehicle.setLaneChangeMode(emergency_vid, 0)
                            traci.vehicle.setSpeedMode(emergency_vid, 0)
                            
                            # Modify traffic light to green
                            logic = traci.trafficlight.getCompleteRedYellowGreenDefinition(target_cluster)[0]
                            for phase in logic.phases:
                                phase.state = ''.join(['G' if char in 'ruyG' else char for char in phase.state])
                            
                            traci.trafficlight.setCompleteRedYellowGreenDefinition(target_cluster, logic)
                            
                            csv_writer.writerow([
                                current_time, 
                                emergency_vid, 
                                target_cluster, 
                                f"{distance:.2f}", 
                                "Green Priority"
                            ])
                            csvfile.flush()
                
                # Check if emergency vehicles are gone and some time has passed
                if emergency_detected and not emergency_vehicles and (current_time - last_emergency_time > 5):
                    try:
                        # Fully restore original traffic light state
                        traci.trafficlight.setCompleteRedYellowGreenDefinition(
                            target_cluster, 
                            original_tl_state['complete_logic']
                        )
                        traci.trafficlight.setProgram(
                            target_cluster, 
                            original_tl_state['program']
                        )
                        
                        csv_writer.writerow([
                            current_time, 
                            "N/A", 
                            target_cluster, 
                            "N/A", 
                            "Normal Traffic Restored"
                        ])
                        csvfile.flush()
                        
                        emergency_detected = False
                    except Exception as e:
                        print(f"Restoration error: {e}")
        
        finally:
            traci.close()

if __name__ == "__main__":
    run_emergency_vehicle()
    print(f"Emergency log saved to emergency_vehicle_log_{time.strftime('%Y%m%d-%H%M%S')}.csv")
