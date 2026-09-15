import requests
from time import sleep
from config import HEADERS, JobResponse, FilesystemResponse, TaskResponse, JobState, TaskStatus

print("\n==========")
print("SUBMIT JOB")
print("==========\n")

# Choose ALCF cluster
resource_id = "55c1c993-1124-47f9-b823-514ba3849a9a" # Polaris
#resource_id = "8b9b42f7-572a-4909-8472-a0453436304c" # Crux

# Define job submission parameters
job_name = "my_job"
queue = "debug"
nodes = 1
walltime_sec = 300
compute_allocation = "<your-compute-allocation>"
stdout_path = "/home/<username>/log.out"
stderr_path = "/home/<username>/log.err"

# Define job submission script 
# This is equivalent to the body of a `qsub` script (excluding `#PBS` directives)
commands = """
echo Start
sleep 5
whoami
echo End
"""

# Submit job
print(f"Submitting job to {resource_id} ...")
response = requests.post(
    f"https://api.alcf.anl.gov/api/v1/compute/job/{resource_id}",
    json={
        "executable": "/bin/bash",
        "arguments": ["-lc", commands],
        "name": job_name,
        "stdout_path": stdout_path,
        "stderr_path": stderr_path,
        "resources": {
            "node_count": nodes
        },
        "attributes": {
            "duration": walltime_sec,
            "queue_name": queue,
            "account": compute_allocation,
            "custom_attributes": {"filesystems": "home:eagle"}
        }
    },
    headers=HEADERS
)
job = JobResponse.model_validate(response.json())
print(job.model_dump_json(indent=2))

print("\n===============")
print("QUERY JOB STATE")
print("===============\n")

# Extract job ID
job_id = job.id.split(".")[0]
print(f"Waiting for PBS job {job_id} to complete ...")

# Query job status every 2 seconds until completed
while True:
    sleep(2)
    response = requests.get(
        f"https://api.alcf.anl.gov/api/v1/compute/status/{resource_id}/{job_id}",
        headers=HEADERS
    )
    job = JobResponse.model_validate(response.json())
    print(f"  Current state: {job.status.state.value}")
    if job.status.state not in (JobState.queued, JobState.active):
        break

# ==============
# EXTRACT RESULT
# ==============
print("\n==============")
print("EXTRACT OUTPUT")
print("==============\n")

# Choose filesystem
resource_id = "6115bd2c-957a-4543-abff-5fae52992ff2" # Home
#resource_id = "1c3ad9d4-2e91-42bc-becb-72b1fde1235c" # Eagle

# Submit filesystem view command to see the content of the output file
print(f"Submitting filesystem view command to {resource_id} ...")
response = requests.get(
    f"https://api.alcf.anl.gov/api/v1/filesystem/view/{resource_id}",
    params={"path": stdout_path, "size": 1000, "offset": 0},
    headers=HEADERS
)
fs_response = FilesystemResponse.model_validate(response.json())
print(fs_response.model_dump_json(indent=2))

# Extract task ID
task_id = fs_response.task_id
print(f"\nWaiting for filesystem task {task_id} to complete ...")

# Query task status every 2 seconds until completed
while True:
    sleep(2)
    response = requests.get(
        f"https://api.alcf.anl.gov/api/v1/task/{task_id}",
        headers=HEADERS
    )
    task = TaskResponse.model_validate(response.json())
    print(f"  Current status: {task.status.value}")
    if task.status not in (TaskStatus.pending, TaskStatus.active):
        break

# Print the output log of the job
print(task.result.output.content)



