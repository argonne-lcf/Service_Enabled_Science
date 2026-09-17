# Facility (IRI) API

The ALCF Facility API (also named IRI API) allows you to programatically execute jobs on HPC systems, trigger filesystem operations, and view your current allocations. This demo focuses on the execution of simple jobs to demonstrate the overall capabilities of the V1 version of the API.

For more information:
- [ALCF documentation](https://docs.alcf.anl.gov/services/iri-api/)
- [API Swagger page](https://api.alcf.anl.gov/)
- [API OpenAPI spec](https://api.alcf.anl.gov/openapi.json)

Below are relevant resources for this demo.

| Resource | ID |
|---|---|
| Polaris | `55c1c993-1124-47f9-b823-514ba3849a9a` |
| Crux | `8b9b42f7-572a-4909-8472-a0453436304c` |
| Eagle | `1c3ad9d4-2e91-42bc-becb-72b1fde1235c` |
| Home | `6115bd2c-957a-4543-abff-5fae52992ff2` |

*Note: The API is under active development. We are working towards improving access to the filesystems, adding more resources, adding status to more machines, and improving the speed of accounting queries.*

## 1. Setup

### 1.a. Authentication

If you already authenticated with `alcf-tokens` **with your ALCF credentials**, test your IRI token:
```bash
alcf-tokens test-token iri
```

If your token if valid and ready to use with the IRI API, you should see:
```json
{"ready": true, "error": null}
```

If you get an error, please try to re-generate your token:
```bash
alcf-tokens login iri
```

If you still get an error, logout from Globus by visiting [https://app.globus.org/logout](https://app.globus.org/logout), open a new **incognito browser**, and restart the entire authentication flow:
```bash
alcf-tokens login
```

### 1.b. Environment Variables

Some of the scripts in this demo rely on variables stored in an `.env` file, which are thereafter loaded with the `python-dotenv` package. Withing this folder (`01_Facility_API/`), create your `.env` file:
```bash
touch .env
```
and copy-paste the content below.

```bash
# =====================
# JOB SUBMISSION CONFIG
# =====================

# Select compute cluster (here Polaris)
RESOURCE_ID="55c1c993-1124-47f9-b823-514ba3849a9a"

# Define job submission parameters
NODES=1
WALLTIME_SEC=300
QUEUE="debug"
COMPUTE_ALLOCATION="alcf_training"
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

By default, jobs will be submitted to Polaris, but you can change the `RESOURCE_ID` to target another HPC cluster. Make sure you replace placeholder values in the `.env` file with your ALCF username.

## 2. Main Exercises

### 2.a. View Resources and their Status

Execute the following script to view the metadata of ALCF resources:
```bash
python 01_get_resources.py
```

You can filter the list by adding the resource name (e.g., polaris) as an argument:
```bash
python 01_get_resources.py polaris
```

For each resource, `current_status` reports whether the resource is *up* and ready to use, and `id` uniquely identities the resource. To query a specific resource from its ID without going through a list, execute the following:

```bash
python 02_get_resource.py 55c1c993-1124-47f9-b823-514ba3849a9a
```

### 2.b. Submit Jobs

Execute the following script to submit a job to Polaris (`RESOURCE_ID=55c1c993-1124-47f9-b823-514ba3849a9a`):
```bash
python 03_submit_job.py
```

If successful, the above command should return the PBS job ID (**keep this ID for the following steps**).
```json
{
  "id": "<your-job-id>.polaris-pbs-01.hsn.cm.polaris.alcf.anl.gov",
  "status": {
    "state": "queued",
    "exit_code": 0
  }
}
```

The job will execute the content of the `COMMANDS` field in your `.env` file. If you kept the default content from the above template, the job will run on 1 node and write your username and the compute node hostname in the `STDOUT_PATH` file (`/home/<your-ALCF-username>/log_example.out`).

Execute the following to query the state of your job:
```bash
python 04_get_job_state.py <your-job-id>
```

Once the your job is `completed` or `failed`, continue to the next section.

### 2.c. View Job Results

You can view the result of your jobs with Filesystem operations. If your PBS job completed, execute the following:
```bash
python 05_view_file.py /home/<your-ALCF-username>/log_example.out
```

If your PBS job failed, execute the following:
```bash
python 05_view_file.py /home/<your-ALCF-username>/log_example.err
```

All filesystem operations are asynchronous, meaning you will always get back a `task_id` when using the Filesystem component. The `05_view_file.py` script automatically checks the status of your task in a loop until it is completed. 

To trigger a pipeline that automatically goes through steps 2.b and 2.c, execute:
```bash
python submit_job_get_result.py
```
