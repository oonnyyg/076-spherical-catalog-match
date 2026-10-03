import csv
import json
import os


def write_outputs(result, output_dir):
    """Write matches.csv and summary.json into output_dir."""
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "matches.csv")
    json_path = os.path.join(output_dir, "summary.json")
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["left_id", "candidate_count", "right_id", "distance_arcsec", "mutual"]
        )
        for row in result["rows"]:
            writer.writerow(
                [
                    row.left_id,
                    row.candidate_count,
                    row.right_id if row.right_id is not None else "",
                    (
                        f"{row.distance_arcsec:.10f}"
                        if row.distance_arcsec is not None
                        else ""
                    ),
                    "true" if row.mutual else "false",
                ]
            )
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(result["summary"], fh, indent=2, sort_keys=True)
        fh.write("\n")
