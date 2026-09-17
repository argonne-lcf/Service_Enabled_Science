import json
import requests
from time import sleep
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

job_id = response["id"]
print(f"Waiting for PBS job {job_id} to complete ...")

while True:
    sleep(2)
    response = requests.get(
        f"https://api.alcf.anl.gov/api/v1/compute/status/{RESOURCE_ID}/{job_id}",
        headers=HEADERS
    )
    response = response.json()
    job_state = response["status"]["state"]
    print(f"  Current state: {job_state}")
    if job_state not in ("queued", "active"):
        break
