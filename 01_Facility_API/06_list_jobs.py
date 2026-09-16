"""
Script to list PBS jobs on a compute resource.
TODO: Adapt query parameteres and filters below.
"""

import json
import requests
from config import HEADERS, RESOURCE_ID

# =============================
# TODO: Define query parameters
# =============================
params = {
    "historical": "false", # "true" will include completed jobs
    "limit": 10, # maximum number of jobs returned
    "offset": 0,
}

# ====================
# TODO: Define filters
# ====================
filters = {}
#filters = {"states": ["active"]}
#filters = {"states": ["active", "queued"]}
#filters = {"owner": "<your-alcf-username>"}
#filters = {"jobIds": ["12345", "12346", "12347"]}
#filters = {"queue": "debug"}
#filters = {"accountingId": "<your-compute-allocation>"}
#filters = {"states": ["active"], "queue": "debug"}

# Submit request
response = requests.post(
    f"https://api.alcf.anl.gov/api/v1/compute/status/{RESOURCE_ID}",
    params=params,
    json=filters,
    headers=HEADERS,
)
print(json.dumps(response.json(), indent=2))