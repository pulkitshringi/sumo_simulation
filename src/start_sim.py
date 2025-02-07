from main import MultiJunctionEmergencyControl

if __name__ == "__main__":
    controller = MultiJunctionEmergencyControl("config/sumo/osm.sumocfg")
    controller.run()