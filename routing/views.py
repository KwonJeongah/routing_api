from django.shortcuts import render

# Create your views here.

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from haversine import haversine
import osmnx as ox
import networkx as nx
from sklearn.neighbors import KDTree
import folium
import pandas as pd
import json 
import time
import copy
import requests

from django.http import JsonResponse
from .models import Waypoint, Vehicle

def get_graph(center_point, dis):
    
    G = ox.graph_from_point(center_point, distance = dis, network_type='drive')

    fast=['motorway','trunk','primary','secondary','motorway_link','trunk_link','primary_link','secondary_link','escape','track']
    slow = ['tertiary', 'residential','tertiary_link','living_street']
    other = ['unclassified','road','service']

    def find_speed(row):
        if row['highway'] in fast:
            return 100/3.6
        elif row['highway'] in slow:
            return 50/3.6
        elif row['highway'] in other:
            return 70/3.6
        else:
            return 5/3.6
        
    nodes, edges = ox.graph_to_gdfs(G, nodes=True, edges=True)
   
    edges = edges.assign(speed=edges.apply(find_speed, axis=1))
    edges['wgt'] = edges['length']/edges['speed']

    UG = ox.gdfs_to_graph(nodes, edges)
    
    return UG

def get_nodes(way_points_df):
    subset = way_points_df[['lat','lon']]
    ex_nodes_geom = [tuple(x) for x in subset.to_numpy()]
    
    demand = way_points_df['weight'].tolist()
    
    return demand, ex_nodes_geom    
   
def near_nodes_geom(G, ex_nodes_geom):
    near_nodes_geom = []
    ex_n = len(ex_nodes_geom)
    
    for i in range(0, ex_n):
        t = (G.nodes[ox.get_nearest_node(G, ex_nodes_geom[i])]['y'], G.nodes[ox.get_nearest_node(G, ex_nodes_geom[i])]['x'])
        near_nodes_geom.append(t)
        
    return near_nodes_geom

def near_nodes_id(G, ex_nodes_geom):
    ids = []
    ex_n = len(ex_nodes_geom)
   
    for i in range(0, ex_n):
        ids.append(G.nodes[ox.get_nearest_node(G, ex_nodes_geom[i])]['osmid'])
  
    return ids


def get_dMatrix(G, near_nodes):
    d_matrix = []
    ex_n = len(near_nodes)
    
    for i in range(0, ex_n):
        is_arr = []
        for j in range(0, ex_n):
            if nx.has_path(G, near_nodes[i], near_nodes[j]):
                length = nx.shortest_path_length(G, near_nodes[i], near_nodes[j], weight = 'wgt')
                is_arr.append(length)
            else:
                is_arr.append(10000000)
        d_matrix.append(is_arr)
       
    return d_matrix    

def create_data_model(matrix, n_veh, demands, vehicle_capacities):
    """Stores the data for the problem."""
    data = {}
    data['distance_matrix'] = matrix
    data['num_vehicles'] = n_veh
    data['depot'] = 0 #Starting point 0으로 고정
    data['demands'] = demands
    data['vehicle_capacities'] = vehicle_capacities
    
    return data

def return_sol_list(data, manager, routing, solution):
    sol_list = []
    for vehicle_id in range(data['num_vehicles']):
        vehicle_sol = []
        index = routing.Start(vehicle_id)
        while not routing.IsEnd(index):
            vehicle_sol.append(manager.IndexToNode(index))
            previous_index = index
            index = solution.Value(routing.NextVar(index))
        vehicle_sol.append(0)
        sol_list.append(vehicle_sol)

    return sol_list

def osm_route(G, route, v_id):
    fig = ox.plot_graph_routes(G, route, route_color='b',
    fig_height=25, fig_width=25, use_geom=True, save=True,
    filename=str(v_id+1))

def get_sht_path(G, ids, sol_list):
    sol = copy.deepcopy(sol_list)
    
    sol_len = len(sol)
    
    for i in range(0, sol_len):
        veh_len = len(sol[i])
        for j in range(0, veh_len):
            sol[i][j] = ids[sol[i][j]-1]
              
    #sol의 노드 간 shortest path 구하기
    route = []

    veh_num = len(sol)

    for i in range(0, veh_num):
        path = []
        nodes_len = len(sol[i])
        for j in range(0, nodes_len-1):
            p = nx.shortest_path(G, sol[i][j], sol[i][j+1], weight = 'wgt')
            path.append(p)
       # path = sum(path,[])
        route.append(path)    
        osm_route(G, route[i], i)
        
    #노드번호로 구성된 path를 좌표값으로 변경     
    for i in range(0, veh_num):
        route_len = len(route[i])
        for j in range(0, route_len):
            p2p_len = len(route[i][j])
            for k in range(0, p2p_len):
                geom = []
                geom.append(G.nodes[route[i][j][k]]['y'])
                geom.append(G.nodes[route[i][j][k]]['x'])
                #geom = tuple(G.nodes[route[i][j]]['y'],G.nodes[route[i][j]]['x'])
                route[i][j][k] = tuple(geom)     
            
    return route


def find_cen_len(ex_nodes_geom):
    nodes_n = len(ex_nodes_geom)
    center_point = ex_nodes_geom[0]
    
    #haversine km단위
    distance = []

    for i in range(0, nodes_n):
        d = haversine(center_point, ex_nodes_geom[i])
        distance.append(d)
        
    max_d = max(distance)
 
    length = int((max_d+3)*1000)
    
    return center_point, length

def route(requests_api):
    sol = None
    route = None


    #start = time.time()
    veh_url = 'http://127.0.0.1:8000/api/v1/vehicles/'
    wayp_url = 'http://127.0.0.1:8000/api/v1/waypoints/'
    
    show_route = 1 #1이면 route 출력, 아니면 출력하지 않음
        
    # get nodes
    way_point_json = requests.get(wayp_url).json()   
   
    #way_point_json = Waypoint.get().json()
    way_points_df = pd.DataFrame(way_point_json)
    
    demand, ex_nodes_geom = get_nodes(way_points_df)
    center_point, length = find_cen_len(ex_nodes_geom)


    #get map
    G = get_graph(center_point, length)
    
    # get near nodes id
    ids = []
    ids = near_nodes_id(G, ex_nodes_geom)
    
    # get distance matrix
    d_matrix = get_dMatrix(G, ids)
    
    # veh_info 서버로부터 가져오기
    veh_info_json = requests.get(veh_url).json()
    #veh_info_json = Vehicle.get().json()
    #json -> dataframe
    veh_info_df = pd.DataFrame(veh_info_json)
    
    #veh_info
    
    n_veh = len(veh_info_df)
    veh_capacity = list(veh_info_df['capacity'])
    
    
    """Solve the CVRP problem"""
    # Instantiate the data problem.
    data = create_data_model(d_matrix, n_veh, demand, veh_capacity)
    
    # Create the routing index manager
    manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                                          data['num_vehicles'], data['depot'])
    # Create Routing Model
    routing = pywrapcp.RoutingModel(manager)
    
    # Create and register a transit callback
    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    
    # Define cost of each arc
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    # Add Capacity constraint
    def demand_callback(from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]
    
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    
    # Add Distance constraint
    #dimension_name = 'Distance'
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0, #no slack
        data['vehicle_capacities'], #vehicle maximum capacities
        True, #start cumul to zero
        'Capacity')

    # Setting first solution heuristic
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    
    # Solve the problem
    assignment = routing.SolveWithParameters(search_parameters)
    
    if assignment:
        #print_solution(data, manager, routing, assignment)
        sol = return_sol_list(data, manager, routing, assignment)
        
        for i in range(0, n_veh):
            waypoint_len = len(sol[i])
            for j in range(0, waypoint_len):
                sol[i][j] = way_points_df.loc[sol[i][j]]['w_id']       
        veh_info_df['route'] = sol

        if show_route:
            route = get_sht_path(G, ids, sol)            
            veh_info_df['route_coord'] = route
    
    result = veh_info_df.to_json()
    return JsonResponse(result, safe=False)