"""
Submit a job to a compute resource and get the job ID back.
TODO: Adapt variables in your .env file.
"""

import json
import requests

from config import (
    HEADERS,
    RESOURCE_ID,
    COMMANDS,
    STDOUT_PATH,
    STDERR_PATH,
    NODES,
    WALLTIME_SEC,
    QUEUE,
    COMPUTE_ALLOCATION,
)


# Submit job to compute resource
response = requests.post(
    f"https://api.alcf.anl.gov/api/v1/compute/job/{RESOURCE_ID}",
    json={
        "executable": "/bin/bash",
        "arguments": ["-lc", COMMANDS],
        "name": "my-job",
        "stdout_path": STDOUT_PATH,
        "stderr_path": STDERR_PATH,
        "resources": {
            "node_count": NODES
        },
        "attributes": {
            "duration": WALLTIME_SEC,
            "queue_name": QUEUE,
            "account": COMPUTE_ALLOCATION,
            "custom_attributes": {"filesystems": "home:eagle"}
        }
    },
    headers=HEADERS
)

# Print job submission details with the job ID (or error if any) 
print(json.dumps(response.json(), indent=2))