"""Pure functions over supplied graphs and place data; no live location or map service."""

import heapq
import math
from collections import deque

from .registry import register


def _path(previous, end):
    result = []
    while end is not None:
        result.append(end)
        end = previous[end]
    return result[::-1]


@register("life", {"graph": {"A": ["B"], "B": ["C"]}, "start": "A", "goal": "C"}, ["A", "B", "C"])
def shortest_unweighted_path(graph, start, goal):
    """Find a shortest directed unweighted path by BFS. Neighbors are node-ID lists; unreachable returns null."""
    previous, queue = {start: None}, deque([start])
    while queue:
        node = queue.popleft()
        if node == goal:
            return _path(previous, goal)
        for neighbor in graph.get(node, []):
            if neighbor not in previous:
                previous[neighbor] = node
                queue.append(neighbor)
    return None


@register("life", {"graph": {"A": {"B": 2, "C": 5}, "B": {"C": 1}}, "start": "A", "goal": "C"}, {"path": ["A", "B", "C"], "cost": 3})
def shortest_weighted_path(graph, start, goal):
    """Dijkstra on directed node->{neighbor:nonnegative finite weight} graphs with string IDs; unreachable returns null."""
    if any(not math.isfinite(w) or w < 0 for neighbors in graph.values() for w in neighbors.values()):
        raise ValueError("All weights must be finite and nonnegative")
    distance, previous, queue = {start: 0}, {start: None}, [(0, start)]
    while queue:
        cost, node = heapq.heappop(queue)
        if cost != distance[node]:
            continue
        if node == goal:
            return {"path": _path(previous, goal), "cost": cost}
        for neighbor, weight in graph.get(node, {}).items():
            value = cost + weight
            if value < distance.get(neighbor, math.inf):
                distance[neighbor], previous[neighbor] = value, node
                heapq.heappush(queue, (value, neighbor))
    return None


@register("life", {"graph": {"A": ["B"], "B": ["A", "C"]}, "start": "A"}, ["A", "B", "C"])
def reachable_nodes(graph, start):
    """Return nodes reachable by directed edges, including start, in breadth-first discovery order."""
    seen, queue, result = {start}, deque([start]), []
    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return result


@register("life", {"graph": {"A": ["C"], "B": ["C"]}}, ["A", "B", "C"])
def topological_order(graph):
    """Topologically sort a directed dependency graph with string IDs; lexical tie-breaking, reject cycles."""
    nodes = set(graph) | {n for neighbors in graph.values() for n in neighbors}
    indegree = dict.fromkeys(nodes, 0)
    for neighbors in graph.values():
        for n in neighbors:
            indegree[n] += 1
    queue = [n for n in nodes if not indegree[n]]
    heapq.heapify(queue)
    result = []
    while queue:
        node = heapq.heappop(queue)
        result.append(node)
        for n in graph.get(node, []):
            indegree[n] -= 1
            if not indegree[n]:
                heapq.heappush(queue, n)
    if len(result) != len(nodes):
        raise ValueError("Graph contains a cycle")
    return result


@register("life", {"grid": [[0, 0], [1, 0]], "start": [0, 0], "goal": [1, 1]}, [[0, 0], [0, 1], [1, 1]])
def grid_shortest_path(grid, start, goal):
    """Find four-neighbor shortest path on a rectangular grid; 0=free, 1=blocked; positions [row,column]."""
    if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
        raise ValueError("Require a nonempty rectangular grid")
    if any(v not in (0, 1) for row in grid for v in row):
        raise ValueError("Grid values must be 0 or 1")
    rows, cols = len(grid), len(grid[0])
    def valid(p):
        return len(p) == 2 and 0 <= p[0] < rows and 0 <= p[1] < cols and grid[p[0]][p[1]] == 0
    if not valid(start) or not valid(goal):
        raise ValueError("Start and goal must be free cells")
    start, goal = tuple(start), tuple(goal)
    queue, previous = deque([start]), {start: None}
    while queue:
        point = queue.popleft()
        if point == goal:
            return [list(p) for p in _path(previous, point)]
        for dr, dc in ((-1, 0), (0, 1), (1, 0), (0, -1)):
            nxt = point[0] + dr, point[1] + dc
            if valid(nxt) and nxt not in previous:
                previous[nxt] = point
                queue.append(nxt)
    return None


@register("life", {"position": [0, 0], "heading": "N", "instructions": [{"turn": "right"}, {"forward": 3}]}, {"position": [3, 0], "heading": "E"})
def follow_relative_directions(position, heading, instructions):
    """Follow left/right/back turns and nonnegative forward distances; Cartesian x=east,y=north, headings N/E/S/W."""
    headings, vectors = "NESW", [(0, 1), (1, 0), (0, -1), (-1, 0)]
    if heading not in headings or len(heading) != 1 or len(position) != 2:
        raise ValueError("Invalid heading or position")
    index, x, y = headings.index(heading), position[0], position[1]
    for action in instructions:
        if set(action) == {"turn"}:
            index = (index + {"left": -1, "right": 1, "back": 2}[action["turn"]]) % 4
        elif set(action) == {"forward"} and action["forward"] >= 0:
            dx, dy = vectors[index]
            x, y = x + dx * action["forward"], y + dy * action["forward"]
        else:
            raise ValueError("Each instruction must be one valid turn or forward distance")
    return {"position": [x, y], "heading": headings[index]}


@register("life", {"a": [1, 2], "b": [4, 6]}, 7)
def manhattan_distance(a, b):
    """Compute Manhattan (L1) distance between equal-dimensional coordinate lists."""
    if len(a) != len(b):
        raise ValueError("Dimension mismatch")
    return sum(abs(x - y) for x, y in zip(a, b))


@register("life", {"a": [1, 2], "b": [4, 6]}, 5.0)
def euclidean_distance(a, b):
    """Compute straight-line Euclidean distance between equal-dimensional coordinate lists."""
    return math.dist(a, b)


@register("life", {"a": [0, 0], "b": [0, 0]}, 0.0)
def haversine_km(a, b):
    """Approximate spherical distance in km for [latitude,longitude] degrees, radius=6371.0088 km; not route distance."""
    for point in (a, b):
        if len(point) != 2 or not -90 <= point[0] <= 90 or not -180 <= point[1] <= 180:
            raise ValueError("Invalid latitude/longitude")
    lat1, lon1, lat2, lon2 = map(math.radians, [*a, *b])
    value = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(min(1.0, max(0.0, value))))


@register("life", {"places": [{"id": "p1", "kind": "cafe"}, {"id": "p2", "kind": "park"}], "constraints": {"kind": "cafe"}}, ["p1"])
def filter_places(places, constraints):
    """Return place IDs whose explicit attributes equal every supplied constraint; missing fields do not match."""
    return [p["id"] for p in places if all(k in p and p[k] == v for k, v in constraints.items())]


@register("life", {"places": [{"id": "p1", "name": "Central Park", "aliases": ["The Park"]}], "name": " the park "}, ["p1"])
def resolve_place_name(places, name):
    """Resolve exact case-insensitive names/aliases after trimming whitespace. Return all matching IDs; never guess ambiguity."""
    target = name.strip().casefold()
    return [p["id"] for p in places if target in {n.strip().casefold() for n in [p["id"], p.get("name", ""), *p.get("aliases", [])]}]


@register("life", {"point": [2, 3], "rectangle": [0, 0, 4, 5]}, True)
def point_in_rectangle(point, rectangle):
    """Test membership in a closed axis-aligned rectangle [xmin,ymin,xmax,ymax], including the boundary."""
    x1, y1, x2, y2 = rectangle
    if x1 > x2 or y1 > y2 or len(point) != 2:
        raise ValueError("Invalid rectangle or point")
    return x1 <= point[0] <= x2 and y1 <= point[1] <= y2


@register("life", {"places": [{"id": "b", "position": [2, 0]}, {"id": "a", "position": [1, 0]}], "origin": [0, 0], "k": 1}, [{"id": "a", "distance": 1.0}])
def nearest_places(places, origin, k):
    """Rank supplied places by Euclidean distance from origin; break ties by string ID; return up to k places."""
    if k < 0:
        raise ValueError("k must be nonnegative")
    ordered = sorted((math.dist(p["position"], origin), p["id"]) for p in places)
    return [{"id": identifier, "distance": distance} for distance, identifier in ordered[:k]]


@register("life", {"candidate_lists": [["a", "b"], ["b", "c"]]}, ["b"])
def intersect_candidates(candidate_lists):
    """Intersect nonempty lists of candidate string IDs; return sorted unique IDs."""
    if not candidate_lists:
        raise ValueError("At least one candidate list is required")
    return sorted(set.intersection(*(set(items) for items in candidate_lists)))


@register("life", {"intervals": [[1, 5], [3, 8]]}, [3, 5])
def intersect_time_windows(intervals):
    """Intersect closed time intervals in the caller's common numeric time unit; touching endpoints count, disjoint returns null."""
    if not intervals or any(len(p) != 2 or p[0] > p[1] for p in intervals):
        raise ValueError("Require valid intervals")
    start, end = max(p[0] for p in intervals), min(p[1] for p in intervals)
    return [start, end] if start <= end else None
