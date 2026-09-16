"""
Script to query the status of a single resource given its ID.
TODO: Pass the resource ID when calling this script.
"""

import argparse
import json
import requests


# Query the status of a specific resource
def get_resource(resource_id):
    response = requests.get(f"https://api.alcf.anl.gov/api/v1/status/resources/{resource_id}")
    return json.dumps(response.json(), indent=2)


if __name__ == "__main__":

    # Parse mandatory resource_id argument
    parser = argparse.ArgumentParser()
    parser.add_argument("resource_id", help="Resource ID")
    args = parser.parse_args()

    print(get_resource(args.resource_id))
