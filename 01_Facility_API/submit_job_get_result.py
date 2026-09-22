import json
import requests
import sys
from time import sleep

from utils import HEADERS, get_filesystem_id_from_path

# Select compute cluster
RESOURCE_ID="8b9b42f7-572a-4909-8472-a0453436304c" # Crux
#RESOURCE_ID="55c1c993-1124-47f9-b823-514ba3849a9a" # Polaris

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


print("\n==========")
print("SUBMIT JOB")
print("==========\n")

print(f"Submitting job to {RESOURCE_ID} ...")
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
response = response.json()
print(json.dumps(response, indent=2))


print("\n===============")
print("QUERY JOB STATE")
print("===============\n")

# Extract job ID
job_id = response["id"]
print(f"Waiting for PBS job {job_id} to complete ...")

# Query job status every 2 seconds until completed
while True:
    sleep(2)
    response = requests.get(
        f"https://api.alcf.anl.gov/api/v1/compute/status/{RESOURCE_ID}/{job_id}",
        headers=HEADERS
    )
    response = response.json()
    job_state = response["status"]["state"]
    print(f"Current state: {job_state}")
    if job_state not in ("queued", "active"):
        break


# ==============
# EXTRACT RESULT
# ==============
print("\n==============")
print("EXTRACT OUTPUT")
print("==============\n")

# Isolate targetted filesystem
filesystem_id = get_filesystem_id_from_path(STDOUT_PATH)

# Submit filesystem view command to see the content of the output file
print(f"Submitting filesystem view command to {filesystem_id} ...")
response = requests.get(
    f"https://api.alcf.anl.gov/api/v1/filesystem/view/{filesystem_id}",
    params={"path": STDOUT_PATH, "size": 1000, "offset": 0},
    headers=HEADERS
)
response = response.json()
print(json.dumps(response, indent=2))

# Exit if filesystem submission failed
if response.get("status_code") != 200:
    sys.exit(1)

# Extract task ID
task_id = response["task_id"]
print(f"\nWaiting for filesystem task {task_id} to complete ...")

# Query task status every 2 seconds until completed
while True:
    sleep(2)
    response = requests.get(
        f"https://api.alcf.anl.gov/api/v1/task/{task_id}",
        headers=HEADERS
    )
    response = response.json()
    task_status = response["status"]
    print(f"Current status: {task_status}")
    if task_status not in ("pending", "active"):
        print()
        break

# Print error or file content
if task_status == "failed":
    print(json.dumps(response["result"], indent=2))
else:
    print(response["result"]["output"]["content"])

