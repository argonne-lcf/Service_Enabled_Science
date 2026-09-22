"""
Script to query the allocations of a specific project given its ID.
TODO: Pass the project ID when calling this script.
"""

import argparse
import json
import requests

from utils import HEADERS


# Query a specific project
def get_allocations(project_id):
    response = requests.get(
        f"https://api.alcf.anl.gov/api/v1/account/projects/{project_id}/project_allocations",
        headers=HEADERS,
    )
    return json.dumps(response.json(), indent=2)


if __name__ == "__main__":

    # Parse mandatory project_id argument
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id", help="Project ID")
    args = parser.parse_args()

    print(get_allocations(args.project_id))
