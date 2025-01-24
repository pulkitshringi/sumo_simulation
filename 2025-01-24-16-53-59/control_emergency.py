import traci

def run_emergency_vehicle():
    """
    Run an emergency vehicle that triggers green lights when nearby
    """
    traci.start(["sumo-gui", "-c", "osm.sumocfg"])
    
    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            
            # Get all emergency vehicles
            emergency_vehicles = [vid for vid in traci.vehicle.getIDList() if vid.startswith('emergency')]
            
            for emergency_vid in emergency_vehicles:
                # Get emergency vehicle position
                emergency_pos = traci.vehicle.getPosition(emergency_vid)
                
                # Get all traffic lights
                tls_ids = traci.trafficlight.getIDList()
                
                for tls in tls_ids:
                    # Get traffic light position
                    tls_pos = traci.junction.getPosition(tls)
                    
                    # Calculate distance between emergency vehicle and traffic light
                    distance = ((emergency_pos[0] - tls_pos[0])**2 + (emergency_pos[1] - tls_pos[1])**2)**0.5
                    
                    # If emergency vehicle is within 200 meters, force green
                    if distance < 400:
                        try:
                            # Get current program logic
                            logic = traci.trafficlight.getCompleteRedYellowGreenDefinition(tls)[0]
                            
                            # Modify the state to all green
                            state_length = len(logic.getPhases()[0].state)
                            green_state = 'G' * state_length
                            
                            # Create a new program with all green phases
                            logic.phases[0].state = green_state
                            traci.trafficlight.setCompleteRedYellowGreenDefinition(tls, logic)
                        except Exception as e:
                            print(f"Error modifying traffic light {tls}: {e}")
                    
                # Ensure emergency vehicle has right of way
                traci.vehicle.setLaneChangeMode(emergency_vid, 0)
                traci.vehicle.setSpeedMode(emergency_vid, 0)
    
    finally:
        # Close the connection
        traci.close()

if __name__ == "__main__":
    run_emergency_vehicle()
