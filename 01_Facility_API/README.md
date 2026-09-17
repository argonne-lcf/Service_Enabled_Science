# Facility (IRI) API

The ALCF Facility API (also named IRI API) allows you to programatically execute jobs on HPC systems, trigger filesystem operations, and view your current allocations. This demo focuses on the execution of simple jobs to demonstrate the overall capabilities of the V1 version of the API.

For more information:
- [ALCF documentation](https://docs.alcf.anl.gov/services/iri-api/)
- [API Swagger page](https://api.alcf.anl.gov/)
- [API OpenAPI spec](https://api.alcf.anl.gov/openapi.json)


*Note: The API is under active development. We are working towards improving access to the filesystems, adding more resources, adding status to more machines, and improving the speed of accounting queries.*

## Setup

### Authentication

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

### Environment Variables

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

By default, jobs will be submitted to Polaris, but you can change the `RESOURCE_ID` to target another HPC cluster:

| Resource | ID |
|---|---|
| Polaris | `55c1c993-1124-47f9-b823-514ba3849a9a` |
| Crux | `8b9b42f7-572a-4909-8472-a0453436304c` |

Make sure you replace placeholder values in the `.env` file with your compute allocation and your ALCF username.

## Exercises

.. under construction ..