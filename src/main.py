# src/main.py
import os
import shutil
import sys
import logging
import subprocess
import traci
import xml.etree.ElementTree as ET
from emergency_vehicle.route_predictor import RoutePredictor
from emergency_vehicle.vehicle_detector import EmergencyVehicleManager
from traffic_light.light_manager import TrafficLightManager

class MultiJunctionEmergencyControl:
    def __init__(self, sumo_config_path: str):
        """
        Initialize the multi-junction emergency control simulation
        """
        # Configure detailed logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Resolve absolute paths
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sumo_config_path = os.path.abspath(os.path.join(self.project_root, sumo_config_path))
        
        self.logger.info(f"Project Root: {self.project_root}")
        self.logger.info(f"SUMO Config Path: {self.sumo_config_path}")
        
        # Validate configuration file
        self._validate_config_file()
        
        # Find and validate network file
        self.net_file = self._find_network_file()
        
        # Initialize simulation components
        self._initialize_components()
    
    def _validate_config_file(self):
        """Validate SUMO configuration file exists and is readable"""
        if not os.path.exists(self.sumo_config_path):
            self.logger.error(f"SUMO configuration file not found: {self.sumo_config_path}")
            raise FileNotFoundError(f"Configuration file not found: {self.sumo_config_path}")
        
        if not os.access(self.sumo_config_path, os.R_OK):
            self.logger.error(f"Cannot read SUMO configuration file: {self.sumo_config_path}")
            raise PermissionError(f"Cannot read configuration file: {self.sumo_config_path}")
    
    def _find_network_file(self) -> str:
        """
        Find the .net.xml file from the SUMO configuration
        """
        try:
            # Parse the configuration file
            tree = ET.parse(self.sumo_config_path)
            root = tree.getroot()
            
            # Look for network file references
            net_file_elem = root.find(".//net-file")
            if net_file_elem is not None:
                net_file_path = net_file_elem.get('value')
                full_path = os.path.abspath(os.path.join(os.path.dirname(self.sumo_config_path), net_file_path))
                
                self.logger.info(f"Network file found: {full_path}")
                if os.path.exists(full_path):
                    return full_path
            
            # Fallback: search for .net.xml in the same directory
            config_dir = os.path.dirname(self.sumo_config_path)
            for file in os.listdir(config_dir):
                if file.endswith('.net.xml'):
                    full_path = os.path.join(config_dir, file)
                    self.logger.info(f"Found network file via fallback: {full_path}")
                    return full_path
            
            raise FileNotFoundError("No network file found")
        
        except Exception as e:
            self.logger.error(f"Error finding network file: {e}")
            raise
    
    def _initialize_components(self):
        """Initialize simulation components"""
        try:
            self.route_predictor = RoutePredictor(self.net_file)
            self.emergency_vehicle_manager = EmergencyVehicleManager(self.route_predictor)
            self.traffic_light_manager = TrafficLightManager(self.emergency_vehicle_manager)
            self.logger.info("Simulation components initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize simulation components: {e}")
            raise
    
    def _get_sumo_binary(self) -> str:
        """
        Determine the appropriate SUMO binary with comprehensive checks
        """
        # List of possible SUMO binary names
        sumo_binaries = [
            "sumo-gui",  # Priority: GUI version
            "sumo",      # Fallback: Command-line version
            "sumo-gui.exe",  # Windows support
            "sumo.exe"   # Windows support
        ]
        
        # Check if SUMO_HOME is set
        sumo_home = os.environ.get('SUMO_HOME')
        if sumo_home:
            # Add paths from SUMO_HOME
            sumo_binaries = [
                os.path.join(sumo_home, 'bin', binary) for binary in sumo_binaries
            ] + sumo_binaries
        
        # Try finding the binary in PATH
        for binary in sumo_binaries:
            binary_path = shutil.which(binary)
            if binary_path:
                try:
                    # Verify the binary works
                    result = subprocess.run(
                        [binary_path, "--version"], 
                        capture_output=True, 
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        self.logger.info(f"Found SUMO binary: {binary_path}")
                        return binary_path
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    continue
        
        # If no binary found
        self.logger.error("No valid SUMO binary found. Please install SUMO.")
        raise RuntimeError("""
        SUMO is not installed or not in PATH. 
        Please install SUMO and ensure it's in your system PATH.
        
        Installation instructions:
        - Ubuntu/Debian: sudo apt-get install sumo
        - macOS with Homebrew: brew install sumo
        - Windows: Download from https://sumo.dlr.de/docs/Downloads.html
        
        After installation, you may need to set SUMO_HOME environment variable.
        """)

    def run(self):
        """
        Run the SUMO simulation with comprehensive error handling
        """
        try:
            # Determine SUMO binary
            sumo_binary = self._get_sumo_binary()
            
            # Prepare SUMO launch command
            sumo_cmd = [
                sumo_binary, 
                "-c", self.sumo_config_path,
                "--verbose"  
            ]

            
            self.logger.info(f"Launching SUMO with command: {' '.join(sumo_cmd)}")
            
            # Start TraCI
            traci.start(sumo_cmd)
            self.logger.info("Simulation started successfully")
            
            # Main simulation loop
            while traci.simulation.getMinExpectedNumber() > 0:
                traci.simulationStep()
                
                # Manage traffic lights for emergency vehicles
                self.traffic_light_manager.manage_traffic_lights()
                
                # Optional: add more detailed logging or specific checks
                current_time = traci.simulation.getTime()
                if current_time % 10 == 0:  # Log every 10 simulation seconds
                    self.logger.debug(f"Simulation time: {current_time}")
        
        except Exception as e:
            self.logger.error(f"Simulation error: {e}", exc_info=True)
        
        finally:
            # Cleanup
            try:
                self.traffic_light_manager.restore_traffic_lights()
                traci.close()
                self.logger.info("Simulation completed and cleaned up")
            except Exception as cleanup_error:
                self.logger.error(f"Error during cleanup: {cleanup_error}")
