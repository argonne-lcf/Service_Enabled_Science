# Facility (IRI) API

The ALCF Facility API (also named IRI API) allows you to programmatically execute jobs on HPC systems, trigger filesystem operations, and view your current allocations. This demo focuses on the execution of simple jobs to demonstrate the overall capabilities of the V1 version of the API.

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

*Note: The API is under active development. We are working towards adding more resources, adding status to more machines, and reducing latency.*

## 1. Setup

### 1.a. Authentication

If you already authenticated with `alcf-tokens` **with your ALCF credentials**, test your IRI token:
```bash
alcf-tokens test-token iri
```

If your token is valid and ready to use with the IRI API, you should see:
```json
{
    "ready": true, 
    "error": null
}
```

If you get an error, please try to re-generate your token:
```bash
alcf-tokens login iri --authorize-transfer eagle --authorize-transfer home
```

If you still get an error, logout from Globus by visiting [https://app.globus.org/logout](https://app.globus.org/logout), open a new **incognito browser**, and restart the above login command.

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

For each resource, `current_status` reports whether the resource is *up* and ready to use, and `id` uniquely identifies the resource. To query a specific resource from its ID without going through a list, execute the following:

```bash
python 02_get_resource.py 55c1c993-1124-47f9-b823-514ba3849a9a
```

### 2.b. Submit Jobs

Look into `03_submit_job.py` and modify the `STDOUT_PATH` and `STDERR_PATH` paths to **include your ALCF username**. Then, execute the script to submit a job to Polaris (`RESOURCE_ID=55c1c993-1124-47f9-b823-514ba3849a9a`):
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

The job will execute the content of the `COMMANDS` field defined in the python script. If you kept the default content, the job will run on 1 node and write your username and the compute node hostname in the `STDOUT_PATH` file (`/home/<your-alcf-username>/log_example.out`).

Execute the following to query the state of your job:
```bash
python 04_get_job_state.py <your-job-id>
```

Once your job is `completed` or `failed`, continue to the next section.

### 2.c. View Job Results

You can view the result of your jobs with Filesystem operations. If your PBS job completed, execute the following:
```bash
python 05_view_file.py /home/<your-alcf-username>/log_example.out
```

If your PBS job failed, execute the following:
```bash
python 05_view_file.py /home/<your-alcf-username>/log_example.err
```

All filesystem operations are asynchronous, meaning you will always get back a `task_id` when using the Filesystem component. The `05_view_file.py` script automatically checks the status of your task in a loop until it is completed. 

To trigger a pipeline that automatically goes through steps 2.b and 2.c, execute the following (do not forget to edit your `STDOUT_PATH` and `STDERR_PATH` variables):
```bash
python submit_job_get_result.py
```

## 3. Additional Exercises

### 3.a. Query Lists of Jobs

Execute the following to query a list of jobs:
```bash
python 06_list_jobs.py
```

Edit the script directly to explore various filters in order to customize your list. Available filters are: 

- **states**: List of job states (new, queued, held, active, completed, failed, canceled)
    - Example: `{"states": ["active", "completed"]}`
- **owner**: ALCF username
    - Example: `{"owner": "<my-alcf-username>"}`
- **jobIds**: List of job IDs
    - Example: `{"jobIds": ["12345", "12346", "12347"]}` 
- **queue**: Name of the PBS queue
    - Example: `{"queue": "debug"}`
- **accountingId**: Name of the compute allocation
    - Example: `{"accountingId": "alcf_training"}`

More than one filter can be added at the same time.

### 3.b. Cancel Job

The IRI API allows you to cancel jobs that are already submitted to the PBS scheduler. First, incorporate a longer sleep (`sleep 30`) in your `COMMANDS` field in `03_submit_job.py` to give yourself some time to cancel the job. Then, submit the job with
```bash
python 03_submit_job.py
```

Cancel your job with your job ID by executing:
```bash
python 07_cancel_job.py <your-job-id>
```

Follow the state of your job until it is labeled as `canceled`.
```bash
python 04_get_job_state.py <your-job-id>
```

### 3.c. Query Allocations

Execute the following script to view your active ALCF projects:
```bash
python 08_get_projects.py
```

You can filter the list by adding the project name (e.g., polaris) as an argument:
```bash
python 08_get_projects.py alcf_training
```

Accounting requests may take some time to execute. If you encounter request timeouts, please try again in a minute.

For each entry, `id` uniquely identifies the project. To query a specific project from its ID without going through a list, execute the following:

```bash
python 09_get_project.py 701d99a6-4102-3e80-bd7c-4872b113795b
```

To view the allocations tied to a project ID, execute the following:
```bash
python 10_get_allocations.py 701d99a6-4102-3e80-bd7c-4872b113795b
```

### 3.d. More Filesystem Commands

Please visit our [ALCF documentation](https://docs.alcf.anl.gov/services/iri-api/#3-filesystem) to learn about other Filesystem commands that are currently supported through the API.
