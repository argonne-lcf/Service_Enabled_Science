# Facility (IRI) API

... under construction ...

Template for the `.env` file
```bash
# ==============
# JOB SUBMISSION
# ==============

# Select compute cluster
RESOURCE_ID="<targetted-compute-resource-id>"

# Define job submission parameters
NODES=1
WALLTIME_SEC=300
QUEUE="debug"
COMPUTE_ALLOCATION="<your-compute-allocation>"
STDOUT_PATH="/home/<your-alcf-username>/log_example.out"
STDERR_PATH="/home/<your-alcf-username>/log_example.err"

# Define commands to be executed
COMMANDS="
echo Start
sleep 5
whoami
hostname
echo End
"
```
