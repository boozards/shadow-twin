"""
Failure Signature Clustering (Context Compaction):
Collapses high-volume raw shadow diffs into a compact set of distinct root-cause signatures,
selecting exactly 1 minimal reproducer per cluster to protect LLM context windows and token budgets.
"""

from typing import List, Dict, Any, Optional
import json

class FailureClusterer:
    """Groups raw request/response/db diffs into canonical failure signatures."""

    @staticmethod
    def extract_signature_key(diff_item: Dict[str, Any]) -> str:
        """
        Signature Tuple: (endpoint, status_mismatch, primary_diff_path, db_table_diff)
        """
        endpoint = diff_item.get("endpoint", "UNKNOWN")
        legacy_status = diff_item.get("legacy_status", 200)
        candidate_status = diff_item.get("candidate_status", 200)
        status_mismatch = f"STATUS_{legacy_status}_vs_{candidate_status}" if legacy_status != candidate_status else "STATUS_MATCH"

        # HTTP JSON Diff Path
        field_diffs = diff_item.get("field_diffs", [])
        if field_diffs:
            primary_path = field_diffs[0].get("path", "ROOT_BODY")
            diff_type = field_diffs[0].get("diff_type", "VALUE_DIFF")
            http_key = f"{primary_path}:{diff_type}"
        else:
            http_key = "JSON_MATCH"

        # DB Divergence
        db_diffs = diff_item.get("db_diff", {}).get("divergent_tables", [])
        db_key = f"DB_{','.join(sorted(db_diffs))}" if db_diffs else "DB_MATCH"

        return f"{endpoint} | {status_mismatch} | {http_key} | {db_key}"

    @classmethod
    def cluster_failures(cls, raw_diffs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregates raw failure records and returns cluster summaries with minimal reproducers.
        """
        clusters: Dict[str, Dict[str, Any]] = {}

        for diff in raw_diffs:
            if not diff.get("is_failure", False):
                continue

            sig_key = cls.extract_signature_key(diff)

            if sig_key not in clusters:
                clusters[sig_key] = {
                    "signature": sig_key,
                    "endpoint": diff.get("endpoint"),
                    "count": 0,
                    "affected_request_ids": [],
                    "minimal_reproducer": diff,
                    "sample_legacy_response": diff.get("legacy_body"),
                    "sample_candidate_response": diff.get("candidate_body"),
                    "sample_field_diffs": diff.get("field_diffs", []),
                    "db_divergence": diff.get("db_diff", {}).get("divergent_tables", [])
                }

            clusters[sig_key]["count"] += 1
            if len(clusters[sig_key]["affected_request_ids"]) < 10:
                clusters[sig_key]["affected_request_ids"].append(diff.get("request_id"))

            # Update minimal reproducer if this diff has a smaller payload
            current_payload = json.dumps(diff.get("request_payload", {}))
            existing_payload = json.dumps(clusters[sig_key]["minimal_reproducer"].get("request_payload", {}))
            if len(current_payload) < len(existing_payload):
                clusters[sig_key]["minimal_reproducer"] = diff

        raw_failure_count = sum(c["count"] for c in clusters.values())
        cluster_count = len(clusters)
        compaction_ratio = (
            ((raw_failure_count - cluster_count) / raw_failure_count * 100.0)
            if raw_failure_count > 0 else 0.0
        )

        return {
            "total_raw_failures": raw_failure_count,
            "unique_cluster_count": cluster_count,
            "compaction_ratio_pct": round(compaction_ratio, 1),
            "clusters": list(clusters.values())
        }

    @classmethod
    def format_for_critic(cls, cluster_result: Dict[str, Any]) -> str:
        """Renders a concise, structured markdown report for the Critic agent prompt."""
        lines = [
            f"### Clustered Failure Signatures Report ({cluster_result['unique_cluster_count']} Unique Signatures from {cluster_result['total_raw_failures']} Raw Failures | {cluster_result['compaction_ratio_pct']}% Token Compaction)",
            ""
        ]

        for idx, cluster in enumerate(cluster_result["clusters"], 1):
            lines.append(f"#### Signature #{idx} (Hits: {cluster['count']} requests)")
            lines.append(f"- **Key:** `{cluster['signature']}`")
            lines.append(f"- **Endpoint:** `{cluster['endpoint']}`")
            lines.append(f"- **DB Divergence:** {cluster['db_divergence'] or 'None'}")
            lines.append("- **Minimal Reproducer Request:**")
            lines.append(f"```json\n{json.dumps(cluster['minimal_reproducer'].get('request_payload', {}), indent=2)}\n```")
            lines.append("- **Legacy Output (Authoritative):**")
            lines.append(f"```json\n{json.dumps(cluster['sample_legacy_response'], indent=2)}\n```")
            lines.append("- **Candidate Output:**")
            lines.append(f"```json\n{json.dumps(cluster['sample_candidate_response'], indent=2)}\n```")
            if cluster["sample_field_diffs"]:
                lines.append(f"- **Field Diffs:** `{json.dumps(cluster['sample_field_diffs'])}`")
            lines.append("")

        return "\n".join(lines)
