"""
Script to query the status of all resources.
Optional argument to extract a resource based on its name.
"""

import argparse
import json
import requests


def get_resources(resource_name=None):

    # Query the status of all resources
    response = requests.get("https://api.alcf.anl.gov/api/v1/status/resources")
    resources = response.json()

    # Filter to extract a resource based on its name
    if resource_name is not None:
        resources = [r for r in resources if r["name"].lower() == resource_name.lower()]
        
    return json.dumps(resources, indent=2)


if __name__ == "__main__":

    # Parse optional resource_name argument
    parser = argparse.ArgumentParser()
    parser.add_argument("resource_name", nargs="?", help="Resource name (e.g., Polaris)")
    args = parser.parse_args()

    print(get_resources(args.resource_name))
