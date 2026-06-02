"""
Graph Engine — Unified Knowledge Graph from SchemaEngine + EventStore.

Builds a graph of nodes (task, project, commitment, life_area, event, person, source)
and edges for Phase 4 Life Graph and future graph-based insights.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from src.models.schema import SchemaEntity

logger = logging.getLogger(__name__)

# Node type constants (frontend colors: task=blue, project=purple, commitment=red, life_area=green, event=gray, person=yellow, source=teal)
NODE_TYPE_TASK = "task"
NODE_TYPE_PROJECT = "project"
NODE_TYPE_COMMITMENT = "commitment"
NODE_TYPE_LIFE_AREA = "life_area"
NODE_TYPE_EVENT = "event"
NODE_TYPE_PERSON = "person"
NODE_TYPE_SOURCE = "source"
NODE_TYPE_DUE_DATE = "due_date"  # virtual node for commitment -> due_date

# Edge type constants
EDGE_EVENT_TO_TASK = "event_to_task"
EDGE_TASK_TO_PROJECT = "task_to_project"
EDGE_TASK_TO_LIFE_AREA = "task_to_life_area"
EDGE_PROJECT_TO_LIFE_AREA = "project_to_life_area"
EDGE_COMMITMENT_TO_TASK = "commitment_to_task"
EDGE_COMMITMENT_TO_DUE_DATE = "commitment_to_due_date"
EDGE_EVENT_TO_PERSON = "event_to_person"
EDGE_TASK_DEPENDS = "task_depends"  # placeholder


@dataclass
class GraphNode:
    id: str
    type: str
    label: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.type, "label": self.label, "meta": self.meta}


@dataclass
class GraphEdge:
    source: str
    target: str
    type: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "target": self.target, "type": self.type, "meta": self.meta}


@dataclass
class Graph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    def node_by_id(self, nid: str) -> GraphNode | None:
        for n in self.nodes:
            if n.id == nid:
                return n
        return None

    def edges_from(self, nid: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.source == nid]

    def edges_to(self, nid: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.target == nid]

    def degree(self, nid: str) -> int:
        return len(self.edges_from(nid)) + len(self.edges_to(nid))


class GraphBuilder:
    """
    Builds a unified graph from SchemaEngine nodes and EventStore events.
    Input: tenant_id, space_id, optional filters.
    Output: Graph (nodes + edges).
    """

    def __init__(self, schema_engine: Any, event_store: Any) -> None:
        self._schema = schema_engine
        self._store = event_store
        self._graph: Graph | None = None
        self._node_index: dict[str, GraphNode] = {}
        self._edge_set: set[tuple[str, str, str]] = set()

    def _add_node(self, n: GraphNode) -> None:
        if n.id not in self._node_index:
            self._node_index[n.id] = n
            self._graph.nodes.append(n)

    def _add_edge(self, source: str, target: str, edge_type: str, meta: dict | None = None) -> None:
        key = (source, target, edge_type)
        if key in self._edge_set:
            return
        self._edge_set.add(key)
        self._graph.edges.append(GraphEdge(source=source, target=target, type=edge_type, meta=meta or {}))

    async def build(
        self,
        tenant_id: str,
        space_id: str | None = None,
        *,
        life_area: str | None = None,
        project_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        entity_types: list[str] | None = None,
        source_filter: str | None = None,
        limit_nodes: int = 2000,
    ) -> Graph:
        """
        Build graph from schema nodes and events. Optional filters reduce scope.
        """
        self._graph = Graph()
        self._node_index = {}
        self._edge_set = set()

        try:
            nodes = await self._schema.list_nodes(
                tenant_id=tenant_id,
                space_id=space_id,
                limit=limit_nodes,
                use_cache=False,
            )
            events: list[Any] = []
            try:
                since = None
                if date_from:
                    try:
                        since = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
                    except Exception:
                        pass
                if since is None:
                    since = datetime.now(timezone.utc) - timedelta(days=90)
                event_list = await self._store.list(
                    tenant_id=tenant_id,
                    space_id=space_id,
                    limit=min(2000, limit_nodes),
                    since=since,
                )
                events = event_list
            except Exception as e:
                logger.warning("GraphBuilder: event_store.list failed: %s", e)

            # Apply entity_types filter to schema nodes
            if entity_types:
                allowed = {e.strip().lower() for e in entity_types}
                nodes = [n for n in nodes if (n.get("entity") or "").lower() in allowed]

            tasks = [n for n in nodes if n.get("entity") == SchemaEntity.TASK.value]
            projects = [n for n in nodes if n.get("entity") == SchemaEntity.PROJECT.value]
            commitments = [n for n in nodes if n.get("entity") == SchemaEntity.COMMITMENT.value]
            life_areas = [n for n in nodes if n.get("entity") == SchemaEntity.LIFE_AREA.value]

            if project_id:
                proj_set = {project_id}
                tasks = [t for t in tasks if t.get("parent_id") == project_id]
                projects = [p for p in projects if p.get("id") == project_id]
            else:
                proj_set = {p["id"] for p in projects}

            if life_area:
                life_area_lower = life_area.strip().lower()
                life_areas = [la for la in life_areas if (la.get("title") or "").strip().lower() == life_area_lower]
                if not life_areas:
                    life_areas = [n for n in nodes if n.get("entity") == SchemaEntity.LIFE_AREA.value]

            # --- Source nodes (unique sources from events) ---
            sources_seen: set[str] = set()
            for ev in events:
                src = getattr(ev, "source", None) or (ev.source if isinstance(ev, dict) else None) or "unknown"
                if source_filter and src != source_filter:
                    continue
                if src and src not in sources_seen:
                    sources_seen.add(src)
                    nid = f"source:{src}"
                    self._add_node(GraphNode(id=nid, type=NODE_TYPE_SOURCE, label=src, meta={"source": src}))

            # --- Life area nodes ---
            for la in life_areas:
                nid = la.get("id")
                if not nid:
                    continue
                self._add_node(GraphNode(
                    id=nid,
                    type=NODE_TYPE_LIFE_AREA,
                    label=la.get("title") or "Life area",
                    meta={"tenant_id": la.get("tenant_id"), "space_id": la.get("space_id")},
                ))

            # --- Project nodes ---
            for p in projects:
                nid = p.get("id")
                if not nid:
                    continue
                self._add_node(GraphNode(
                    id=nid,
                    type=NODE_TYPE_PROJECT,
                    label=p.get("title") or "Project",
                    meta={
                        "tenant_id": p.get("tenant_id"),
                        "parent_id": p.get("parent_id"),
                        "status": p.get("status"),
                        "description": (p.get("description") or "")[:200],
                    },
                ))
                parent_id = p.get("parent_id")
                if parent_id and parent_id in self._node_index:
                    self._add_edge(nid, parent_id, EDGE_PROJECT_TO_LIFE_AREA)

            # --- Task nodes ---
            for t in tasks:
                nid = t.get("id")
                if not nid:
                    continue
                self._add_node(GraphNode(
                    id=nid,
                    type=NODE_TYPE_TASK,
                    label=t.get("title") or "Task",
                    meta={
                        "tenant_id": t.get("tenant_id"),
                        "status": t.get("status"),
                        "due_date": t.get("due_date"),
                        "parent_id": t.get("parent_id"),
                    },
                ))
                parent_id = t.get("parent_id")
                if parent_id and parent_id in proj_set:
                    self._add_edge(nid, parent_id, EDGE_TASK_TO_PROJECT)
                # task -> life_area: via metadata.life_area or parent project's life area
                life_area_id = (t.get("metadata") or {}).get("life_area_id")
                if life_area_id and life_area_id in self._node_index:
                    self._add_edge(nid, life_area_id, EDGE_TASK_TO_LIFE_AREA)
                elif parent_id:
                    proj_node = next((p for p in projects if p.get("id") == parent_id), None)
                    if proj_node and proj_node.get("parent_id") and proj_node["parent_id"] in self._node_index:
                        self._add_edge(nid, proj_node["parent_id"], EDGE_TASK_TO_LIFE_AREA)

            # --- Commitment nodes + virtual due_date nodes ---
            for c in commitments:
                nid = c.get("id")
                if not nid:
                    continue
                self._add_node(GraphNode(
                    id=nid,
                    type=NODE_TYPE_COMMITMENT,
                    label=c.get("title") or "Commitment",
                    meta={
                        "tenant_id": c.get("tenant_id"),
                        "status": c.get("status"),
                        "due_date": c.get("due_date"),
                    },
                ))
                due = c.get("due_date")
                if due:
                    if isinstance(due, str):
                        due_label = due[:10] if len(due) >= 10 else due
                    else:
                        due_label = str(due)[:10]
                    due_id = f"due_date:{nid}"
                    self._add_node(GraphNode(id=due_id, type=NODE_TYPE_DUE_DATE, label=due_label, meta={"commitment_id": nid}))
                    self._add_edge(nid, due_id, EDGE_COMMITMENT_TO_DUE_DATE)
                # commitment -> task: if metadata has task_id or we link by title; placeholder: skip unless we have explicit link
                task_id = (c.get("metadata") or {}).get("task_id")
                if task_id and task_id in self._node_index:
                    self._add_edge(nid, task_id, EDGE_COMMITMENT_TO_TASK)

            # --- Event nodes + event -> task, event -> person, event -> source ---
            event_ids: set[str] = set()
            for ev in events:
                if source_filter:
                    src = getattr(ev, "source", None) or (ev.source if isinstance(ev, dict) else None)
                    if src != source_filter:
                        continue
                eid = str(getattr(ev, "id", None) or (ev.get("id") if isinstance(ev, dict) else None) or "")
                if not eid or eid in event_ids:
                    continue
                event_ids.add(eid)
                content = getattr(ev, "content", None) or (ev.get("content") if isinstance(ev, dict) else "") or ""
                label = (content[:50] + "…") if len(content) > 50 else content or "Event"
                ts = getattr(ev, "timestamp", None) or (ev.get("timestamp") if isinstance(ev, dict) else None)
                if hasattr(ts, "isoformat"):
                    ts = ts.isoformat()
                self._add_node(GraphNode(
                    id=eid,
                    type=NODE_TYPE_EVENT,
                    label=label,
                    meta={
                        "source": getattr(ev, "source", None) or (ev.get("source") if isinstance(ev, dict) else None),
                        "timestamp": ts,
                    },
                ))
                src = getattr(ev, "source", None) or (ev.get("source") if isinstance(ev, dict) else None)
                if src:
                    self._add_edge(eid, f"source:{src}", "event_to_source")
                # event -> person (actor / metadata sender, participants)
                meta = getattr(ev, "metadata", None) or (ev.get("metadata") if isinstance(ev, dict) else {}) or {}
                actor = getattr(ev, "actor", None) or meta.get("sender") or meta.get("actor")
                if actor:
                    pid = f"person:{actor}"
                    if pid not in self._node_index:
                        self._add_node(GraphNode(id=pid, type=NODE_TYPE_PERSON, label=actor, meta={"identifier": actor}))
                    self._add_edge(eid, pid, EDGE_EVENT_TO_PERSON)
                for p in (meta.get("participants") or [])[:5]:
                    if isinstance(p, str):
                        pid = f"person:{p}"
                        if pid not in self._node_index:
                            self._add_node(GraphNode(id=pid, type=NODE_TYPE_PERSON, label=p, meta={"identifier": p}))
                        self._add_edge(eid, pid, EDGE_EVENT_TO_PERSON)

            # --- event -> task (via task metadata source_event_id) ---
            for t in tasks:
                nid = t.get("id")
                meta = t.get("metadata") or {}
                ev_id = meta.get("source_event_id")
                if ev_id and str(ev_id) in self._node_index:
                    self._add_edge(str(ev_id), nid, EDGE_EVENT_TO_TASK)

        except Exception as e:
            logger.exception("GraphBuilder.build failed: %s", e)
            self._graph = Graph()

        return self._graph

    # --- Hooks for Phase 5 graph-based insights ---

    def get_isolated_nodes(self) -> list[GraphNode]:
        """Nodes with degree 0."""
        if not self._graph:
            return []
        return [n for n in self._graph.nodes if self._graph.degree(n.id) == 0]

    def get_high_degree_nodes(self, min_degree: int = 3) -> list[tuple[GraphNode, int]]:
        """Nodes with at least min_degree connections. Returns (node, degree)."""
        if not self._graph:
            return []
        out = []
        for n in self._graph.nodes:
            d = self._graph.degree(n.id)
            if d >= min_degree:
                out.append((n, d))
        out.sort(key=lambda x: -x[1])
        return out

    def get_clusters(self) -> list[list[str]]:
        """Connected components (node id lists). Simple BFS."""
        if not self._graph:
            return []
        adj: dict[str, set[str]] = defaultdict(set)
        for e in self._graph.edges:
            adj[e.source].add(e.target)
            adj[e.target].add(e.source)
        visited: set[str] = set()
        clusters: list[list[str]] = []
        for n in self._graph.nodes:
            nid = n.id
            if nid in visited:
                continue
            comp: list[str] = []
            stack = [nid]
            while stack:
                u = stack.pop()
                if u in visited:
                    continue
                visited.add(u)
                comp.append(u)
                for v in adj[u]:
                    if v not in visited:
                        stack.append(v)
            if comp:
                clusters.append(comp)
        return clusters

    def get_paths(self, entity_id: str, max_depth: int = 5) -> list[list[str]]:
        """Paths from entity_id to others (BFS, max_depth). Returns list of path (list of node ids)."""
        if not self._graph:
            return []
        adj: dict[str, list[str]] = defaultdict(list)
        for e in self._graph.edges:
            adj[e.source].append(e.target)
            adj[e.target].append(e.source)
        paths: list[list[str]] = []
        queue: list[tuple[str, list[str]]] = [(entity_id, [entity_id])]
        seen: set[str] = {entity_id}
        while queue and len(paths) < 500:
            u, path = queue.pop(0)
            if len(path) > 1:
                paths.append(path)
            if len(path) >= max_depth:
                continue
            for v in adj[u]:
                if v in seen:
                    continue
                seen.add(v)
                queue.append((v, path + [v]))
        return paths

    def get_life_area_distribution(self) -> dict[str, int]:
        """Count of nodes (tasks + projects) per life_area node id (by label)."""
        if not self._graph:
            return {}
        dist: dict[str, int] = defaultdict(int)
        life_area_labels = {n.id: n.label for n in self._graph.nodes if n.type == NODE_TYPE_LIFE_AREA}
        for e in self._graph.edges:
            if e.type == EDGE_TASK_TO_LIFE_AREA or e.type == EDGE_PROJECT_TO_LIFE_AREA:
                lid = e.target
                label = life_area_labels.get(lid, lid)
                dist[label] += 1
        return dict(dist)
