"""Cypher query constants for the pipeline report generator."""

from __future__ import annotations

from typing import LiteralString

_Q_STATS: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE f.isTest = false OR $include_tests
WITH count(f) AS total
OPTIONAL MATCH (:Function {repo: $repo})-[r:SIMILAR_TO]->(:Function {repo: $repo})
RETURN total, count(r) AS edges
"""

_Q_TEST_COUNT: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false, isTest: true})
RETURN count(f) AS test_count
"""

_Q_NO_EDGES: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE (f.isTest = false OR $include_tests)
  AND f.isAnonymous = false
  AND NOT (f)-[:SIMILAR_TO]-(:Function {repo: $repo})
RETURN count(f) AS isolated
"""

_Q_TOP_PAIRS: LiteralString = """
MATCH (a:Function {repo: $repo})-[r:SIMILAR_TO]->(b:Function {repo: $repo})
WHERE (a.isTest = false OR $include_tests) AND (b.isTest = false OR $include_tests)
RETURN
  a.qualifiedName AS a_name,
  a.filePath      AS a_file,
  b.qualifiedName AS b_name,
  b.filePath      AS b_file,
  r.combinedSimilarity AS score
ORDER BY score DESC
LIMIT $limit
"""

# Updated: intra/inter breakdown replaces simple connection count.
_Q_MOST_CONNECTED: LiteralString = """
MATCH (f:Function {repo: $repo})-[r:SIMILAR_TO]-(b:Function {repo: $repo})
WHERE f.isTest = false OR $include_tests
WITH f.qualifiedName AS name, f.filePath AS file,
     count(r) AS connections,
     sum(CASE WHEN b.filePath = f.filePath THEN 1 ELSE 0 END) AS intra,
     sum(CASE WHEN b.filePath <> f.filePath THEN 1 ELSE 0 END) AS inter
ORDER BY connections DESC
LIMIT $limit
RETURN name, file, connections, intra, inter
"""

_Q_LANGUAGE_BREAKDOWN: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE f.isTest = false OR $include_tests
RETURN f.language AS language, count(f) AS count
ORDER BY count DESC
"""

_Q_EMBEDDING_COVERAGE: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE f.isTest = false OR $include_tests
RETURN f.codeEmbeddingStatus AS status, count(f) AS cnt
"""

_Q_DESCRIPTION_COVERAGE: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE f.isTest = false OR $include_tests
RETURN f.descriptionStatus AS status, count(f) AS cnt
"""

_Q_EMBEDDING_FAILURES: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE (f.isTest = false OR $include_tests)
  AND (f.codeEmbeddingStatus IN ['timeout', 'context_overflow', 'error']
    OR f.descriptionStatus IN ['timeout', 'invalid_json', 'error'])
RETURN f.qualifiedName AS name, f.filePath AS file,
       f.codeEmbeddingStatus AS code_status,
       f.descriptionStatus AS desc_status
ORDER BY f.filePath
LIMIT $limit
"""

_Q_INTRA_INTER_EDGES: LiteralString = """
MATCH (a:Function {repo: $repo})-[r:SIMILAR_TO]->(b:Function {repo: $repo})
WHERE a.isTest = false OR $include_tests
RETURN
  sum(CASE WHEN a.filePath = b.filePath THEN 1 ELSE 0 END) AS intra,
  sum(CASE WHEN a.filePath <> b.filePath THEN 1 ELSE 0 END) AS inter
"""

_Q_SIMILARITY_DISTRIBUTION: LiteralString = """
MATCH (a:Function {repo: $repo})-[r:SIMILAR_TO]->(b:Function {repo: $repo})
WHERE a.isTest = false OR $include_tests
RETURN
  sum(CASE WHEN r.combinedSimilarity > $bin_high THEN 1 ELSE 0 END) AS gt_high,
  sum(CASE WHEN r.combinedSimilarity > $bin_mid AND r.combinedSimilarity <= $bin_high THEN 1 ELSE 0 END) AS b_mid_high,
  sum(CASE WHEN r.combinedSimilarity > $bin_low AND r.combinedSimilarity <= $bin_mid THEN 1 ELSE 0 END) AS b_low_mid,
  sum(CASE WHEN r.combinedSimilarity <= $bin_low THEN 1 ELSE 0 END) AS lt_low
"""

_Q_PER_FILE_INTER: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE f.isTest = false OR $include_tests
WITH f.filePath AS path, count(f) AS fn_count
OPTIONAL MATCH (a:Function {repo: $repo, filePath: path})-[r:SIMILAR_TO]-(b:Function {repo: $repo})
RETURN path, fn_count,
  count(r) AS edge_count,
  sum(CASE WHEN b.filePath <> path THEN 1 ELSE 0 END) AS inter_edges
ORDER BY edge_count DESC
LIMIT $limit
"""

_Q_CLUSTER_EDGES: LiteralString = """
MATCH (a:Function {repo: $repo})-[r:SIMILAR_TO]->(b:Function {repo: $repo})
WHERE r.combinedSimilarity >= $threshold
  AND (a.isTest = false OR $include_tests)
RETURN
  a.qualifiedName AS a_name, a.filePath AS a_file,
  b.qualifiedName AS b_name, b.filePath AS b_file,
  r.combinedSimilarity AS score
"""

_Q_TEST_POLLUTION: LiteralString = """
MATCH (a:Function {repo: $repo})-[r:SIMILAR_TO]-(b:Function {repo: $repo})
WHERE a.isTest = true AND b.isTest = false
RETURN count(r) AS cross_edges
"""

_Q_ISOLATED_FUNCTIONS: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE (f.isTest = false OR $include_tests)
  AND f.isAnonymous = false
  AND NOT (f)-[:SIMILAR_TO]-(:Function {repo: $repo})
RETURN f.qualifiedName AS name, f.filePath AS file,
       f.codeEmbeddingStatus AS code_status,
       f.descriptionStatus AS desc_status
ORDER BY f.filePath, f.qualifiedName
LIMIT $limit
"""

_Q_FILE_EMBEDDINGS: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE (f.isTest = false OR $include_tests)
  AND (f.codeEmbedding IS NOT NULL OR f.descriptionEmbedding IS NOT NULL)
RETURN f.filePath AS filePath, f.className AS className,
       f.qualifiedName AS qualifiedName,
       f.codeEmbedding AS codeEmbedding,
       f.descriptionEmbedding AS descriptionEmbedding
ORDER BY f.filePath
"""

_Q_FILES_BY_FUNCTION_COUNT: LiteralString = """
MATCH (f:Function {repo: $repo, isDeleted: false})
WHERE f.isTest = false OR $include_tests
RETURN f.filePath AS path, count(f) AS fn_count
ORDER BY fn_count DESC
LIMIT $limit
"""
