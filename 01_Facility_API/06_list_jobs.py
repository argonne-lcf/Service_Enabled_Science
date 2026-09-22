"""
Script to list PBS jobs on a compute resource.
"""

import json
import requests

from utils import HEADERS

# Select compute cluster
#RESOURCE_ID="8b9b42f7-572a-4909-8472-a0453436304c" # Crux
RESOURCE_ID="55c1c993-1124-47f9-b823-514ba3849a9a" # Polaris

# Define query parameters
params = {
    "historical": "true", # "true" will include completed jobs
    "limit": 10, # maximum number of jobs returned
    "offset": 0,
}

# Define filters
#filters = {}
filters = {"states": ["active"]}
#filters = {"states": ["active", "queued"]}
#filters = {"owner": "<your-alcf-username>"}
#filters = {"jobIds": ["12345", "12346", "12347"]}
#filters = {"queue": "debug"}
#filters = {"accountingId": "alcf_training"}
#filters = {"states": ["active"], "queue": "debug"}


# Submit request
response = requests.post(
    f"https://api.alcf.anl.gov/api/v1/compute/status/{RESOURCE_ID}",
    params=params,
    json=filters,
    headers=HEADERS,
)
print(json.dumps(response.json(), indent=2))