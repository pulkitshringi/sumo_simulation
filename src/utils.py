# src/utils.py
import csv
import time
import os
import json
from typing import List, Dict, Any

class Config:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        src_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(src_dir)
        config_path = os.path.join(project_root, 'config', 'config.json')
        
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print(f"Config file not found at: {config_path}")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Project root directory: {project_root}")
            raise
    
    @property
    def sumo_config_path(self):
        src_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(src_dir)
        return os.path.join(project_root, self.config['sumo']['config_path'])

class Logger:
    def __init__(self, filename_prefix: str):
        self.config = Config()
        src_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(src_dir)
        log_dir = os.path.join(project_root, self.config.config['logging']['directory'])
        
        os.makedirs(log_dir, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.filename = os.path.join(log_dir, f"{filename_prefix}_{timestamp}.csv")
        self.setup_csv()

    def setup_csv(self):
        with open(self.filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'Timestamp', 
                'Emergency Vehicle ID', 
                'Traffic Light Cluster', 
                'Distance', 
                'Action Taken'
            ])

    def log_event(self, data: Dict[str, Any]):
        with open(self.filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                data.get('timestamp'),
                data.get('vehicle_id', 'N/A'),
                data.get('cluster'),
                data.get('distance', 'N/A'),
                data.get('action')
            ])