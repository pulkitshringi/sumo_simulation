# src/emergency_vehicle/route_predictor.py
import gzip
import networkx as nx
import math
import xml.etree.ElementTree as ET
import logging
from typing import List, Tuple, Dict, Optional

class RoutePredictor:
    def __init__(self, sumo_net_file: str):
        """
        Initialize route predictor with SUMO network file
        
        :param sumo_net_file: Path to SUMO .net.xml or .net.xml.gz file
        """
        self.logger = logging.getLogger(__name__)
        self.sumo_net_file = sumo_net_file
        self.graph = self._parse_network_file()
    
    def _parse_network_file(self) -> nx.DiGraph:
        """
        Parse SUMO network XML file to create a graph
        
        :return: Directed graph representation of the network
        """
        graph = nx.DiGraph()
        
        try:
            # Determine file opening method based on extension
            if self.sumo_net_file.endswith('.gz'):
                open_func = gzip.open
                decode = True
            else:
                open_func = open
                decode = False
            
            # Parse the network XML file
            with open_func(self.sumo_net_file, 'rb') as f:
                # Read and decode if necessary
                xml_content = f.read()
                if decode:
                    xml_content = xml_content.decode('utf-8')
                
                # Parse XML content
                root = ET.fromstring(xml_content)
                
                # Extract junctions
                for junction in root.findall('.//junction'):
                    junc_id = junction.get('id', '')
                    # Skip internal junctions
                    if junc_id.startswith(':'):
                        continue
                    
                    try:
                        x = float(junction.get('x', 0))
                        y = float(junction.get('y', 0))
                        graph.add_node(junc_id, pos=(x, y))
                    except (TypeError, ValueError) as coord_error:
                        self.logger.warning(f"Skipping junction {junc_id} due to coordinate error: {coord_error}")
                
                # Extract edges
                for edge in root.findall('.//edge'):
                    from_junction = edge.get('from', '')
                    to_junction = edge.get('to', '')
                    
                    if (from_junction and to_junction and 
                        from_junction in graph.nodes and 
                        to_junction in graph.nodes):
                        # Calculate distance between junctions
                        from_pos = graph.nodes[from_junction]['pos']
                        to_pos = graph.nodes[to_junction]['pos']
                        distance = math.dist(from_pos, to_pos)
                        
                        graph.add_edge(from_junction, to_junction, weight=distance)
        
        except ET.ParseError as parse_error:
            self.logger.error(f"XML Parsing error: {parse_error}")
            return nx.DiGraph()
        except Exception as e:
            self.logger.error(f"Unexpected error parsing network file: {e}")
            return nx.DiGraph()
        
        return graph
    
    def find_emergency_route(
        self, 
        start_point: Tuple[float, float], 
        end_point: Tuple[float, float]
    ) -> List[Tuple[str, List[str]]]:
        """
        Find emergency route through network with junction details
        
        :param start_point: Starting coordinates
        :param end_point: Destination coordinates
        :return: List of (junction_id, priority_lanes)
        """
        # Find nearest junctions to start and end points
        try:
            start_junction = min(
                self.graph.nodes, 
                key=lambda j: math.dist(start_point, self.graph.nodes[j]['pos'])
            )
            end_junction = min(
                self.graph.nodes, 
                key=lambda j: math.dist(end_point, self.graph.nodes[j]['pos'])
            )
            
            # Find shortest path
            try:
                route = nx.shortest_path(self.graph, start_junction, end_junction, weight='weight')
            except nx.NetworkXNoPath:
                self.logger.warning(f"No path found between {start_junction} and {end_junction}")
                return []
            
            # Extract junction route
            junction_routes = []
            for i in range(len(route) - 1):
                current_junction = route[i]
                next_junction = route[i + 1]
                
                # Find edges connecting these junctions
                connecting_edges = [
                    edge for edge in self.graph.edges 
                    if edge[0] == current_junction and edge[1] == next_junction
                ]
                
                # Use edge IDs as priority lanes
                priority_lanes = [f"{edge[0]}_{edge[1]}" for edge in connecting_edges]
                
                junction_routes.append((current_junction, priority_lanes))
            
            return junction_routes
        
        except Exception as e:
            self.logger.error(f"Error finding emergency route: {e}")
            return []
    
    def get_junction_coords(self, junction_id: str) -> Optional[Tuple[float, float]]:
        """
        Get coordinates of a specific junction
        
        :param junction_id: ID of the junction
        :return: Coordinates of the junction or None
        """
        try:
            return self.graph.nodes[junction_id]['pos']
        except KeyError:
            self.logger.warning(f"Junction {junction_id} not found in graph")
            return None
    
    def get_all_junctions(self) -> List[str]:
        """Get list of all junction IDs"""
        return list(self.graph.nodes)