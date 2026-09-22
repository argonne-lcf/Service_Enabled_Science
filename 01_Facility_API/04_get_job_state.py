"""
Script to query the state of a PBS job.
TODO: Pass the job ID when calling this script.
"""

import argparse
import json
import requests
from utils import HEADERS

# Select compute cluster
#RESOURCE_ID="8b9b42f7-572a-4909-8472-a0453436304c" # Crux
RESOURCE_ID="55c1c993-1124-47f9-b823-514ba3849a9a" # Polaris


# Query the state of a specific PBS job
def get_job(job_id):
    response = requests.get(
        f"https://api.alcf.anl.gov/api/v1/compute/status/{RESOURCE_ID}/{job_id}",
        headers=HEADERS,
    )
    return json.dumps(response.json(), indent=2)


if __name__ == "__main__":

    # Parse mandatory job_id argument
    parser = argparse.ArgumentParser()
    parser.add_argument("job_id", help="PBS job ID")
    args = parser.parse_args()

    print(get_job(args.job_id))
