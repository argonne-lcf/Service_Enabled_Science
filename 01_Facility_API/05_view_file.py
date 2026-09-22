"""
Script to view the content of a file on a filesystem.
TODO: Pass the absolute path of the file when calling this script.
"""

import argparse
import json
import requests
from time import sleep

from utils import HEADERS, get_filesystem_id_from_path


# Submit filesystem operation and get back a task ID
def submit_view_file(file_path: str) -> str:

    # Isolate targetted filesystem
    resource_id = get_filesystem_id_from_path(file_path)

    # Submit view command
    print(f"Submitting filesystem view command to {resource_id} ...")
    response = requests.get(
        f"https://api.alcf.anl.gov/api/v1/filesystem/view/{resource_id}",
        params={
            "path": file_path,
            "size": 1000,
            "offset": 0
        },
        headers=HEADERS
    )

    # Print task status
    response = response.json()
    print(json.dumps(response, indent=2))

    # Return task ID
    return response.get("task_id")


if __name__ == "__main__":

    # Parse mandatory file_path argument
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path", help="Absolute path of the file")
    args = parser.parse_args()

    # Submit filesytem operation and get back a task ID
    task_id = submit_view_file(args.file_path)
    print(f"\nWaiting for filesystem task {task_id} to complete ...")

    while True:

        # Query task status every 2 seconds
        sleep(2)
        response = requests.get(
            f"https://api.alcf.anl.gov/api/v1/task/{task_id}",
            headers=HEADERS
        )
        response = response.json()

        # Report task status
        task_status = response.get("status")
        print(f"Current status: {task_status}")

        # Exit loop if needed
        if task_status not in ["pending", "active"]:
            print()
            break

    # Print error or file content
    if task_status == "failed":
        print(json.dumps(response["result"], indent=2))
    else:
        print(response["result"]["output"]["content"])
    