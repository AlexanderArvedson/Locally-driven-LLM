"""Graph-aware file ranker.

GraphRanker uses a GraphQuery instance to rank file candidates by:
  1. Keyword-matched seed nodes
  2. One-hop dependency expansion
  3. Per-file max-score aggregation
  4. Target file always first; remainder sorted by score descending
"""

from __future__ import annotations

from typing import Optional

from src.retrieval.graph.graph_query import GraphQuery


class GraphRanker:
    """Ranks file candidates using the knowledge graph as a retrieval index.

    The graph is treated purely as an index substrate — no graph content is
    included in the returned file list or passed upstream as context.
    """

    def rank_candidates(
        self,
        task: str,
        graph_query: GraphQuery,
        repo_path: str,
        target_file: Optional[str] = None,
        max_files: int = 15,
    ) -> list[str]:
        """Return an ordered list of file paths relevant to `task`.

        Pipeline:
            1. Extract normalised task keywords.
            2. Score graph nodes by keyword overlap (seed nodes).
            3. Expand seeds by one dependency hop.
            4. Map all expanded nodes to their source files with max scores.
            5. Insert target_file first; sort remainder by score descending.
        """
        task_words = GraphQuery.task_words(task)
        if not task_words:
            return [target_file] if target_file else []

        # Step 1+2: keyword scoring → seed nodes
        seed_scored = graph_query.query_by_keywords(task_words, top_k=20)
        seed_node_ids = [nid for nid, _ in seed_scored]

        # Step 3: dependency expansion (1 hop)
        expanded_ids = graph_query.expand_by_dependency(seed_node_ids, hops=1)

        # Rebuild scored list including expanded nodes (with score 0.1 for expanded-only)
        seed_score_map = dict(seed_scored)
        expanded_scored = [
            (nid, seed_score_map.get(nid, 0.1))
            for nid in expanded_ids
        ]

        # Step 4: map to files with max score
        file_scores = graph_query.files_for_scored_nodes(expanded_scored, repo_path)

        # Step 5: assemble result — target file first, rest by score desc
        result: list[str] = []
        if target_file:
            file_scores.pop(target_file, None)
            result.append(target_file)

        result.extend(sorted(file_scores, key=lambda f: -file_scores[f]))
        return result[:max_files]
