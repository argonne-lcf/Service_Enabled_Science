"""
Script to query projects.
Optional argument to extract a project based on its name.
"""

import argparse
import json
import requests
from config import HEADERS


def get_projects(project_name=None):

    # Query all projects
    response = requests.get(
        "https://api.alcf.anl.gov/api/v1/account/projects",
        headers=HEADERS,
    )
    projects = response.json()

    # Filter to extract a project based on its name
    if project_name is not None:
        projects = [r for r in projects if r["name"].lower() == project_name.lower()]
        
    return json.dumps(projects, indent=2)


if __name__ == "__main__":

    # Parse optional project_name argument
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name", nargs="?", help="Project name")
    args = parser.parse_args()

    print(get_projects(args.project_name))
