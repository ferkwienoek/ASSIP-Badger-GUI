# uvicorn fastapi2:app --reload --port 8000


import requests
import xml.etree.ElementTree as ET
import json
from collections import defaultdict
from sentence_transformers import SentenceTransformer, util
import networkx as nx
from geopy.distance import geodesic
import pandas as pd
import os
from openai import OpenAI
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class UserPrompt(BaseModel):
    user_prompt: str

min_lat = 38.82657
min_lon = -77.31182
max_lat = 38.83533
max_lon = -77.30015

def get_osm_file(min_lat, min_lon, max_lat, max_lon):
    url = f"https://overpass-api.de/api/map?bbox={min_lon},{min_lat},{max_lon},{max_lat}"
    return requests.get(url).content

osm_data = get_osm_file(min_lat, min_lon, max_lat, max_lon)
with open("gmu.xml", "wb") as f:
    f.write(osm_data)

tree = ET.parse('gmu.xml')
root = tree.getroot()

tag_dict = defaultdict(set)
for element in root.iter():
    if element.tag in {"node", "way", "relation"}:
        for tag in element.findall("tag"):
            k = tag.attrib.get("k")
            v = tag.attrib.get("v", "")
            if k is not None:
                tag_dict[k].add(v)

tag_dict_json = {k: sorted(list(v_set)) for k, v_set in tag_dict.items()}
with open("osm_tags_sorted.json", "w") as f:
    json.dump(tag_dict_json, f, indent=2)

with open("osm_tags_sorted.json", "r") as f:
    tag_dict = json.load(f)

tag_texts = [f"{k}={v}" for k, values in tag_dict.items() for v in values]
model = SentenceTransformer('all-MiniLM-L6-v2')
tag_embeddings = model.encode(tag_texts, convert_to_tensor=True)

node_lookup = {}
for node in root.findall("node"):
    node_id = node.attrib["id"]
    lat = float(node.attrib["lat"])
    lon = float(node.attrib["lon"])
    node_lookup[node_id] = (lat, lon)

def find_latlon_by_name(place_name):
    tree = ET.parse("gmu.xml")
    root = tree.getroot()
    for element in root.iter():
        if element.tag in {"node", "way"}:
            tags = {tag.attrib["k"]: tag.attrib["v"] for tag in element.findall("tag")}
            if tags.get("name", "").lower() == place_name.lower():
                if element.tag == "node":
                    lat = float(element.attrib["lat"])
                    lon = float(element.attrib["lon"])
                    return {"type": "node", "lat": lat, "lon": lon, "tags": tags}
                elif element.tag == "way":
                    nd_refs = [nd.attrib["ref"] for nd in element.findall("nd")]
                    coords = [node_lookup[ref] for ref in nd_refs if ref in node_lookup]
                    if coords:
                        avg_lat = sum(lat for lat, _ in coords) / len(coords)
                        avg_lon = sum(lon for _, lon in coords) / len(coords)
                        return {"type": "way", "lat": avg_lat, "lon": avg_lon, "tags": tags}
    return None

@app.post("/get_waypoints/")
def get_waypoints(data: UserPrompt):
    user_prompt = data.user_prompt
    prompt_embedding = model.encode(user_prompt, convert_to_tensor=True)
    cosine_scores = util.cos_sim(prompt_embedding, tag_embeddings)[0]
    top_k = 10
    top_indices = cosine_scores.argsort(descending=True)[:top_k]
    top_matches = [(tag_texts[i], float(cosine_scores[i])) for i in top_indices]
    matched_kv = [{"k": tag.split("=")[0], "v": tag.split("=")[1], "score": score} for tag, score in top_matches]
    matched_df = pd.DataFrame(matched_kv)

    client = OpenAI(api_key="")
    fine_tuned_model = ""

    guideline = ("Only respond with the name of the percieved destination on the GMU campus that the user wants to go "
                 "to.")
    response = client.chat.completions.create(
        model=fine_tuned_model,
        messages=[
            {"role": "system", "content": guideline},
            {"role": "user", "content": user_prompt}
        ]
    )
    outputllm = response.choices[0].message.content

    result = find_latlon_by_name(outputllm)

    tree = ET.parse("gmu.xml")
    root = tree.getroot()
    node_coords = {}
    for node in root.findall("node"):
        node_id = node.attrib["id"]
        lat = float(node.attrib["lat"])
        lon = float(node.attrib["lon"])
        node_coords[node_id] = (lat, lon)

    N_top_kv_pairs = 10
    top_matches = matched_df.head(N_top_kv_pairs).to_dict("records")

    matched_elements = []
    for element in root.iter():
        if element.tag in {"node", "way"}:
            tags = {tag.attrib["k"]: tag.attrib["v"] for tag in element.findall("tag")}
            match_count = sum(1 for match in top_matches if tags.get(match["k"]) == match["v"])
            if match_count == 0:
                continue
            match_entry = {"type": element.tag, "tags": tags, "match_count": match_count}
            if element.tag == "node":
                match_entry["lat"] = element.attrib.get("lat")
                match_entry["lon"] = element.attrib.get("lon")
            elif element.tag == "way":
                match_entry["id"] = element.attrib.get("id")
                nd_refs = [nd.attrib["ref"] for nd in element.findall("nd")]
                coords = [node_coords[ref] for ref in nd_refs if ref in node_coords]
                if coords:
                    avg_lat = sum(lat for lat, _ in coords) / len(coords)
                    avg_lon = sum(lon for _, lon in coords) / len(coords)
                    match_entry["lat"] = avg_lat
                    match_entry["lon"] = avg_lon
                else:
                    match_entry["lat"] = None
                    match_entry["lon"] = None
            matched_elements.append(match_entry)

    matched_elements.sort(key=lambda x: x["match_count"], reverse=True)
    location_df = pd.DataFrame(matched_elements)

    node_lookup = {}
    for node in root.findall("node"):
        node_id = node.attrib["id"]
        lat = float(node.attrib["lat"])
        lon = float(node.attrib["lon"])
        node_lookup[node_id] = (lat, lon)

    G = nx.Graph()
    for way in root.findall("way"):
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
        if (tags.get("highway") in {"footway", "path", "corridor", "pedestrian"}
                and tags.get("highway") != "steps"
                and tags.get("ramp:wheelchair") != "no"
                and tags.get("wheelchair") != "no"):
            nds = [nd.attrib["ref"] for nd in way.findall("nd")]
            for i in range(len(nds) - 1):
                n1, n2 = nds[i], nds[i + 1]
                if n1 in node_lookup and n2 in node_lookup:
                    coord1, coord2 = node_lookup[n1], node_lookup[n2]
                    dist = geodesic(coord1, coord2).meters
                    G.add_edge(n1, n2, weight=dist)

    start_point = (38.8295903, -77.3058259)
    nearest_start_node = min(node_lookup, key=lambda nid: geodesic(start_point, node_lookup[nid]).meters)
    dest_lat = float(location_df.iloc[0]["lat"])
    dest_lon = float(location_df.iloc[0]["lon"])
    destination_coords = [(dest_lat, dest_lon)]
    graph_nodes = set(G.nodes)
    destination_nodes = [
        min(graph_nodes, key=lambda nid: geodesic(dest, node_lookup[nid]).meters)
        for dest in destination_coords
    ]

    shortest_path = None
    min_distance = float("inf")
    for dest in destination_nodes:
        try:
            path = nx.shortest_path(G, source=nearest_start_node, target=dest, weight='weight')
            dist = nx.shortest_path_length(G, source=nearest_start_node, target=dest, weight='weight')
            if dist < min_distance:
                min_distance = dist
                shortest_path = path
        except nx.NetworkXNoPath:
            continue

    path_coords = [node_lookup[nid] for nid in shortest_path] if shortest_path else []
    path_df = pd.DataFrame(path_coords, columns=["lat", "lon"])
    output_path = "shortest_path_coords.csv"
    path_df.to_csv(output_path, index=False)
    csv_path = 'shortest_path_coords.csv'
    df = pd.read_csv(csv_path)
    df.columns = [col.strip().lower() for col in df.columns]
    if 'lat' in df.columns and 'lon' in df.columns:
        df.rename(columns={'lat': 'latitude', 'lon': 'longitude'}, inplace=True)

    waypoint_lines = ["QGC WPL 110"]
    for idx, row in df.iterrows():
        line = f"{idx}\t0\t3\t16\t0\t0\t0\t0\t{row['latitude']}\t{row['longitude']}\t0.000000\t1"
        waypoint_lines.append(line)
    with open("converted_waypoints.txt", "w") as f:
        f.write("\n".join(waypoint_lines))

    return {
        "destination": outputllm,
        "waypoints": path_df
    }
