# /// script
# requires-python = ">=3.10"
# dependencies = ["alcf-ai>=0.13"]
# ///
"""
Step 1: Discover which models the ALCF Inference Service offers.

    uv run 01_list_endpoints.py
"""

from alcf_ai import InferenceClient

client = InferenceClient()
catalog = client.list_endpoints()

print(f"{'CLUSTER':<10} {'FRAMEWORK':<12} MODEL")
for cluster_name, cluster in catalog["clusters"].items():
    print("------")
    for framework_name, framework in cluster["frameworks"].items():
        for model in framework["models"]:
            print(f"{cluster_name:<10} {framework_name:<12} {model}")

jobs = client.clusters("metis").get_jobs()

print("\nRunning on Metis right now:")
for job in jobs["running"]:
    print(f"  🔥 {job['Models']}")
