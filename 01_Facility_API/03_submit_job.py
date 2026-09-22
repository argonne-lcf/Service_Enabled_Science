"""
Submit a job to a compute resource and get the job ID back.
TODO: Modify STDOUT_PATH/STDERR_PATH variables below to include your ALCF username.
"""

import json
import requests

from utils import HEADERS


# Select compute cluster
#RESOURCE_ID="8b9b42f7-572a-4909-8472-a0453436304c" # Crux
RESOURCE_ID="55c1c993-1124-47f9-b823-514ba3849a9a" # Polaris

# Define job submission parameters
NODES=1
WALLTIME_SEC=300
QUEUE="debug"
COMPUTE_ALLOCATION="alcf_training"
STDOUT_PATH="/home/<your-alcf-username>/log_example.out"
STDERR_PATH="/home/<your-alcf-username>/log_example.err"

# Define commands to be executed
COMMANDS="""
echo Start
sleep 5
whoami
hostname
echo End
"""


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