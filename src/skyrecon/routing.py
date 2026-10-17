"""Grid route planning with obstacle inflation."""

from __future__ import annotations

from heapq import heappop, heappush
from math import hypot

Cell = tuple[int, int]


class AirspaceGrid:
    def __init__(self, width: int, height: int) -> None:
        if width < 2 or height < 2:
            raise ValueError("airspace dimensions must be at least 2 x 2")
        self.width, self.height = width, height
        self._blocked: set[Cell] = set()

    def block_disc(self, center: Cell, radius: int = 0) -> None:
        cx, cy = center
        for x in range(cx - radius, cx + radius + 1):
            for y in range(cy - radius, cy + radius + 1):
                if self.contains((x, y)) and hypot(x - cx, y - cy) <= radius + 0.25:
                    self._blocked.add((x, y))

    def contains(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.width and 0 <= cell[1] < self.height

    def route(self, start: Cell, destination: Cell) -> list[Cell]:
        if not self.contains(start) or not self.contains(destination):
            raise ValueError("route endpoints are outside the configured airspace")
        if start in self._blocked or destination in self._blocked:
            return []

        frontier: list[tuple[float, Cell]] = [(0.0, start)]
        parent: dict[Cell, Cell | None] = {start: None}
        cost: dict[Cell, float] = {start: 0.0}
        while frontier:
            _, current = heappop(frontier)
            if current == destination:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                candidate = (current[0] + dx, current[1] + dy)
                if not self.contains(candidate) or candidate in self._blocked:
                    continue
                new_cost = cost[current] + 1.0
                if new_cost < cost.get(candidate, float("inf")):
                    cost[candidate] = new_cost
                    priority = new_cost + abs(destination[0] - candidate[0]) + abs(destination[1] - candidate[1])
                    heappush(frontier, (priority, candidate))
                    parent[candidate] = current

        if destination not in parent:
            return []
        path: list[Cell] = []
        cursor: Cell | None = destination
        while cursor is not None:
            path.append(cursor)
            cursor = parent[cursor]
        return list(reversed(path))
