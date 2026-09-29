Globus Services at ALCF: Compute, Transfer & Flows
===============================================

This session will demonstrate how to use Globus tools on ALCF systems.  We will focus on Globus Compute with the ALCF Multi-user Endpoints (MEPs), Globus file transfers, and Globus Flows.

# Setup

If you have done this setup at the start of the workshop, you do not need to repeat this step and can skip to the start of the [exercises](#globus-compute---alcf-multi-user-endpoints).

## Environment

To setup the workshop environment on your local machine, try executing the setup script:
```bash
cd ..
./setup.sh
source .venv/bin/activate
cd 02_Globus_Compute_and_Transfer
```

This environment on your local machine will sometimes be called the "client" environment in these exercises.

## Authentication

To create the authentication tokens needed for the workshop in one command, execute this command:
```bash
alcf-tokens login --authorize-transfer eagle:data_access --authorize-transfer home:data_access
```

This will cover most of the authentication needed for these exercises.  The one exception is that there will be an additional authentication step needed for the Globus Flows example.

# Globus Compute - ALCF Multi-user Endpoints

[Globus Compute](https://globus-compute.readthedocs.io/en/stable/index.html) lets you execute Python functions remotely by submitting them to endpoints running on ALCF systems.  This demo focuses on the **facility-supported multi-user endpoints (MEPs)**, which are persistent endpoints run by ALCF.  The key advantage of a MEP is that **you do not have to configure, start, or monitor an endpoint yourself.** 

In this demo, you will run exercises as a "client" from your local machine and execute tasks on Polaris and Crux compute nodes.

The facility MEPs that we will use are:

| System  | UUID |
| ------  | ---- |
| Polaris | [9a947ba5-f537-4681-acf3-cc66485aadec](https://app.globus.org/compute/endpoints/9a947ba5-f537-4681-acf3-cc66485aadec) |
| Crux    | [fd8b54bb-9452-411d-8e3a-09408156a886](https://app.globus.org/compute/endpoints/fd8b54bb-9452-411d-8e3a-09408156a886) |

The Globus pages linked above give up-to-date details on each endpoint's configuration template, schema, and status.  For full documentation see the [ALCF Globus Compute guide](https://docs.alcf.anl.gov/services/globus-compute/) and the [Globus Compute docs](https://globus-compute.readthedocs.io/en/stable/index.html).


## Exercises

### 1. Hello MEP (`1_hello_mep.py`)

The simplest possible test: submit a simple hello world function to the Crux MEP.  Run this to confirm your client can reach the MEPs and that authentication works.

```bash
python 1_hello_mep.py
```

Because the MEP has to submit and start a PBS jobs on Crux, expect this to take a minute.  The results will say hello and give information about the python environment running the MEP on Crux.

```python
from globus_compute_sdk import Executor, Client
from globus_compute_sdk.serialize import ComputeSerializer, AllCodeStrategies
from alcf_tokens.auth import get_service_authorizer

# This script is intended to be run from your local machine where you have
# built the workshop client environment.  It sends functions to the 
# facility-supported Crux multi-user endpoint (MEP), which runs the 
# functions on compute nodes by submitting a PBS job on the user's behalf.

# The Crux MEPs
CRUX_MEP = "fd8b54bb-9452-411d-8e3a-09408156a886"

# Project and queues used to charge and schedule the PBS jobs the MEP submits
# on your behalf.
ACCOUNT = "alcf_training"
CRUX_QUEUE = "R314927"

# A simple function that reports the environment it runs in on Polaris.
# This is a useful first test when checking that the MEP is reachable.
def hello_affinity():
    import sys
    import socket
    import parsl
    import globus_compute_endpoint

    return f""" Hello! Here's some of my info:
                hostname: {socket.getfqdn()}
                remote environment: {sys.executable}
                python version: {sys.version}
                parsl version: {parsl.__version__}
                GCE version: {globus_compute_endpoint.__version__}
            """

# To use alcf-tokens for authentication, create a Client and Authorizer:
# note that if authenticating directly with the Executor, this is not necessary
authorizer = get_service_authorizer("globus-compute")
gcc = Client(authorizer=authorizer)

# The AllCodeStrategies serializer avoids serialization errors 
# when the client and the MEP workers  
# run different python versions.
serializer = ComputeSerializer(strategy_code=AllCodeStrategies())

# user_endpoint_config is passed to the MEP, which uses it to provision a
# user endpoint (UEP) that submits PBS jobs under your account.  "account"
# and "queue" are always required.
crux_gce = Executor(
    endpoint_id=CRUX_MEP,
    serializer=serializer,
    client=gcc,
    user_endpoint_config={
        "account": ACCOUNT,
        "queue": CRUX_QUEUE,
    },
)

print("Submitting hello_affinity to the Crux MEP, waiting for result...")
crux_future = crux_gce.submit(hello_affinity)
print(crux_future.result())
crux_gce.shutdown()
```

The result should look like this:
```console
$ python 1_hello_mep.py
Submitting hello_affinity to the Crux MEP, waiting for result...
/Users/csimpson/training/Service_Enabled_Science/.venv/lib/python3.12/site-packages/globus_compute_sdk/sdk/client.py:316: UserWarning: 
Environment differences detected between local SDK and endpoint 01368c90-3b6c-10ee-0595-7282b9482e99 workers:
	    SDK: Python 3.12.13/Dill 0.3.9
	Workers: Python 3.13.11/Dill 0.3.9
This may cause serialization issues.  See https://globus-compute.readthedocs.io/en/latest/sdk/executor_user_guide.html#avoiding-serialization-errors for more information.
  warnings.warn(check_result, UserWarning)
 Hello! Here's some of my info:
                hostname: x1000c0s6b0n1.hostmgmt2000.cm.crux.alcf.anl.gov
                remote environment: /opt/globus-compute-agent/venv-py313/bin/python3
                python version: 3.13.11 (main, Mar  2 2026, 18:34:28) [GCC 7.5.0]
                parsl version: 2026.02.23
                GCE version: 4.9.0
```

Note that this function gives some useful information for creating python environments on the remote machine, if necessary.  If you wish to use your own python environment on the remote machine, it is necessary to install `parsl` and `globus-compute-endpoint` in that environment.  However, it is necessary to match the exact version of `parsl` in your remote environment with the version of `parsl` run by the MEP.  This convenient function gives you the `parsl` version run by the MEP.

This exercise will also give you a warning message about version differences in Python and Dill running in the MEP environment and your environment.  This should not be a problem because we are using a [serializer to mitigate the issue](#serialization-across-python-versions). 

## 2. Configuring the user endpoint (`2_configure_endpoint_options.py`)

When using the MEPs, the **MEP user endpoint is configured at submit time** through the `user_endpoint_config` dictionary.  This exercise walks through some common options and shows how they shape the PBS job the MEP submits for you.

The script submits 8 tasks to a node with 4 workers, so the node runs two waves of 4.

```bash
python 2_configure_endpoint_options.py
```

```python
from globus_compute_sdk import Executor, Client
from globus_compute_sdk.serialize import ComputeSerializer, AllCodeStrategies
from concurrent.futures import as_completed
from alcf_tokens.auth import get_service_authorizer

# A multiuser globus compute endpoint is configured at *submit time* through the
# user_endpoint_config dictionary.  This example shows some common options and
# how to use them with the Polaris MEP.

POLARIS_MEP = "9a947ba5-f537-4681-acf3-cc66485aadec"
ACCOUNT = "alcf_training"
QUEUE = "R7645913"


def where_am_i(task_id, sleeptime):
    import os
    import socket
    import time

    start = time.time()
    time.sleep(sleeptime)
    return (f"task {task_id:>2} ran on {socket.gethostname()} and GPU {os.getenv("CUDA_VISIBLE_DEVICES")}"
            f"(pid {os.getpid()}) for {time.time() - start:.1f}s")

serializer = ComputeSerializer(strategy_code=AllCodeStrategies())

# Each key below maps to a documented Polaris MEP configuration option.
user_endpoint_config = {
    # Required: project to charge and queue to submit to
    "account": ACCOUNT,
    "queue": QUEUE,
    # worker_init is where you can add your own environment commands that will be set 
    # before the workload is run on the compute nodes.  Note that if you activate a python
    # environment in worker_init, it is recommended that you match the parsl version in 
    # the MEP environment (returned by the function used in exercise 1).  The machine 
    # conda env on Polaris (activated here) has this installed.
    "worker_init": "module use /soft/modulefiles; module load conda; conda activate base",
    # Walltime of the PBS job the MEP submits on your behalf
    "walltime": "00:10:00",
    # One PBS job (block) of a single node
    "nodes_per_block": 1,
    # Allow up to 4 functions to run concurrently on the node
    "max_workers_per_node": 4,
    # This option will pin one worker per GPU
    "available_accelerators": 4,
    # Shut the PBS job down after 60s idle so you don't burn allocation
    "max_idletime": 60,
    # Polaris-visible filesystems.
    "scheduler_options": "#PBS -l filesystems=home:eagle:grand",
}

authorizer = get_service_authorizer('globus-compute')
gcc = Client(authorizer=authorizer)
# As an alternative to exercise 1, here we open a context for the Executor and
# make calls within the context.
with Executor(endpoint_id=POLARIS_MEP,
                serializer=serializer,
                client=gcc,
                user_endpoint_config=user_endpoint_config) as gce:

    # Submit 8 tasks to 4 workers -> the node runs two waves of 4.
    # Watch the reported durations to see the second wave start after the
    # first finishes.
    futures = [gce.submit(where_am_i, i, 5) for i in range(8)]

    print("Submitted 8 tasks to a 4-worker node, waiting for results...")
    for f in as_completed(futures):
        print(f.result())

```

Outputs should look like this (with a different node and pid):
```console
$ python configure_endpoint_options.py
Submitted 8 tasks to a 4-worker node, waiting for results...
/Users/csimpson/training/Service_Enabled_Science/.venv/lib/python3.12/site-packages/globus_compute_sdk/sdk/client.py:316: UserWarning: 
Environment differences detected between local SDK and endpoint 19d05a3a-deac-f813-19a1-083cd617d18d workers:
	    SDK: Python 3.12.13/Dill 0.3.9
	Workers: Python 3.13.11/Dill 0.3.9
This may cause serialization issues.  See https://globus-compute.readthedocs.io/en/latest/sdk/executor_user_guide.html#avoiding-serialization-errors for more information.
  warnings.warn(check_result, UserWarning)
task  0 ran on x3005c0s13b1n0 and GPU 0(pid 820999) for 5.0s
task  3 ran on x3005c0s13b1n0 and GPU 2(pid 821001) for 5.0s
task  1 ran on x3005c0s13b1n0 and GPU 1(pid 821000) for 5.0s
task  2 ran on x3005c0s13b1n0 and GPU 3(pid 821002) for 5.0s
task  6 ran on x3005c0s13b1n0 and GPU 3(pid 821002) for 5.0s
task  4 ran on x3005c0s13b1n0 and GPU 0(pid 820999) for 5.0s
task  7 ran on x3005c0s13b1n0 and GPU 2(pid 821001) for 5.0s
task  5 ran on x3005c0s13b1n0 and GPU 1(pid 821000) for 5.0s
```

The full list of options and their defaults is in the [MEP configuration options](https://docs.alcf.anl.gov/services/globus-compute/#configuration-options) documentation.

## 3. Registering a function (`3_register_function.py`)

Globus Compute lets you **register** a function with the Globus service so it can be called later by a function id.  Registered functions can be shared, reused, and used as building blocks in [Globus Flows](https://docs.globus.org/api/flows/).

Registration talks only to the Globus service — no endpoint is contacted, so no account or queue is needed here.  We register the function's **source code** with `register_source_code` (rather than a pickled object) so it is robust to python-version differences between the Aurora client and the Polaris workers.  The function itself is a trivial `adder` that adds two numbers:

```python
from globus_compute_sdk import Client

source = '''
def adder(a, b):
    return a + b
'''

gcc = Client()
func_id = gcc.register_source_code(source=source,
                                   function_name="adder",
                                   description="Adds two numbers")
print(f"Registered adder; id {func_id}")
```

The same script then calls the registered function on both MEPs by its id with `submit_to_registered_function`, and prints the results:

```python
polaris_future = polaris_gce.submit_to_registered_function(args=(5, 10), function_id=func_id)
crux_future = crux_gce.submit_to_registered_function(args=(2, 3), function_id=func_id)
print(f"Polaris result: 5 + 10 = {polaris_future.result()}")
print(f"Crux result: 2 + 3 = {crux_future.result()}")
```
To run the example:
```bash
python 3_register_function.py
```

The expected outputs:
```console
$ python 3_register_function.py
Registered adder; id b99adaf0-7545-4324-b41e-67dd2e52fb4d
Calling registered adder on the Polaris and Crux MEPs, waiting for results...
/Users/csimpson/training/Service_Enabled_Science/.venv/lib/python3.12/site-packages/globus_compute_sdk/sdk/client.py:316: UserWarning: 
Environment differences detected between local SDK and endpoint 1ca55003-9cf6-d384-4a52-fd1c4444d7a6 workers:
	    SDK: Python 3.12.13/Dill 0.3.9
	Workers: Python 3.13.11/Dill 0.3.9
This may cause serialization issues.  See https://globus-compute.readthedocs.io/en/latest/sdk/executor_user_guide.html#avoiding-serialization-errors for more information.
  warnings.warn(check_result, UserWarning)
Polaris result: 5 + 10 = 15
/Users/csimpson/training/Service_Enabled_Science/.venv/lib/python3.12/site-packages/globus_compute_sdk/sdk/client.py:316: UserWarning: 
Environment differences detected between local SDK and endpoint 01368c90-3b6c-10ee-0595-7282b9482e99 workers:
	    SDK: Python 3.12.13/Dill 0.3.9
	Workers: Python 3.13.11/Dill 0.3.9
This may cause serialization issues.  See https://globus-compute.readthedocs.io/en/latest/sdk/executor_user_guide.html#avoiding-serialization-errors for more information.
  warnings.warn(check_result, UserWarning)
Crux result: 2 + 3 = 5
```

## 4. Wrapping a compiled executable (`4_wrap_executable.py`)

Globus Compute runs Python functions, but most HPC work is a compiled executable.  The pattern is to **wrap the executable in a Python function** that shells out to it with `subprocess`.  In this example the shell command `hostname; sleep <sleeptime>` stands in for the path to a real compiled executable.

To run the example:
```bash
python 4_wrap_executable.py
```

This is the function that is submitted:
```python
def host_sleep_wrapper(sleeptime):
    import os
    import subprocess

    # Stand-in for a real executable.  A real command must live on a
    # Polaris/Crux-visible filesystem (/home, /eagle, /grand)
    command = f"hostname; sleep {sleeptime}"

    # Create and move into a run directory on the Polaris filesystem
    run_directory = "$HOME/ses_globus_mep"
    os.makedirs(os.path.expandvars(run_directory), exist_ok=True)
    os.chdir(os.path.expandvars(run_directory))

    # Run the application command
    res = subprocess.run(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         shell=True)

    # Save stdout/stderr to the Polaris filesystem for later inspection
    with open("hello.stdout", "w") as f:
        f.write(res.stdout.decode("utf-8"))
    with open("hello.stderr", "w") as f:
        f.write(res.stderr.decode("utf-8"))

    # Error handling: raise on failure, otherwise return the captured output
    if res.returncode != 0:
        raise Exception(f"Application failed with return code {res.returncode}: "
                        f"stderr='{res.stderr.decode('utf-8')}'")
    return res.returncode, res.stdout.decode("utf-8"), res.stderr.decode("utf-8")
```

The wrapper writes its output to a run directory on the Polaris filesystem and also returns stdout/stderr to the client.  A real command must live on a Polaris-visible filesystem (`home`, `eagle`, or `grand`).

The expected outputs should look like:
```console
$ python 4_wrap_executable.py
Submitting host_sleep_wrapper to the Polaris MEP, waiting for result...
/Users/csimpson/training/Service_Enabled_Science/.venv/lib/python3.12/site-packages/globus_compute_sdk/sdk/client.py:316: UserWarning: 
Environment differences detected between local SDK and endpoint 71fa9a90-d0c6-ef55-a8b9-a72235bc8af9 workers:
	    SDK: Python 3.12.13/Dill 0.3.9
	Workers: Python 3.13.11/Dill 0.3.9
This may cause serialization issues.  See https://globus-compute.readthedocs.io/en/latest/sdk/executor_user_guide.html#avoiding-serialization-errors for more information.
  warnings.warn(check_result, UserWarning)
Results of wrapper function:
x3005c0s1b0n0

```


## 5. Running across multiple nodes (`5_multinode.py`)

By default the MEP runs functions with the `SimpleLauncher` on a single node.  To spread work across nodes, switch to the `MpiExecLauncher` and request a multi-node block.

To run the example:
```bash
python 5_multinode.py
```

The full script:
```python
from globus_compute_sdk import Executor, Client
from globus_compute_sdk.serialize import ComputeSerializer, AllCodeStrategies
from concurrent.futures import as_completed
from alcf_tokens.auth import get_service_authorizer

# By default the MEP runs functions with the SimpleLauncher on a single node.
# To spread work across multiple nodes, switch the launcher to MpiExecLauncher
# and request a multi-node block.  This example runs one function per node.

POLARIS_MEP = "9a947ba5-f537-4681-acf3-cc66485aadec"
ACCOUNT = "alcf_training"
QUEUE = "R7645913"
NUM_NODES = 2


def query_host():
    import os
    import socket
    import time

    time.sleep(5)
    return f"Hello from node {socket.gethostname()}, GPU {os.getenv("CUDA_VISIBLE_DEVICES")}"


serializer = ComputeSerializer(strategy_code=AllCodeStrategies())
user_endpoint_config = {
    "account": ACCOUNT,
    "queue": QUEUE,
    # MpiExecLauncher is required to place workers across multiple nodes
    "launcher_type": "MpiExecLauncher",
    # Request a block spanning NUM_NODES nodes
    "nodes_per_block": NUM_NODES,
    # Pin one worker per GPU, there are 4 GPUs on a Polaris node
    "max_workers_per_node": 4,
    "available_accelerators": 4,
    # place=scatter is important for multi-node jobs: it spreads the workers
    # across the allocated nodes.  Remember: Polaris filesystems only.
    "scheduler_options": (
        "#PBS -l filesystems=home:eagle:grand\n"
        "#PBS -l place=scatter"
    ),
    "max_idletime": 60,
}

authorizer = get_service_authorizer('globus-compute')
gcc = Client(authorizer=authorizer)
with Executor(endpoint_id=POLARIS_MEP,
                client=gcc,
                serializer=serializer,
                user_endpoint_config=user_endpoint_config) as gce:

    # Submit two tasks per GPU.  With one worker per GPU they run one at a time
    # on each worker, so you should see each hostname/GPU combination reported twice.
    futures = [gce.submit(query_host) for _ in range(2 * NUM_NODES * 4)]

    print(f"Submitted {2 * NUM_NODES * 4} tasks across {NUM_NODES} nodes, "
            "waiting for results...")
    for f in as_completed(futures):
        print(f.result())
```

The expected outputs will look like this (however, you will have different nodes):
```console
$ python 5_multinode.py
Submitted 16 tasks across 2 nodes, waiting for results...
/Users/csimpson/training/Service_Enabled_Science/.venv/lib/python3.12/site-packages/globus_compute_sdk/sdk/client.py:316: UserWarning: 
Environment differences detected between local SDK and endpoint 31fffd55-aa3b-e2b0-57cb-9e8d704bcd3d workers:
	    SDK: Python 3.12.13/Dill 0.3.9
	Workers: Python 3.13.11/Dill 0.3.9
This may cause serialization issues.  See https://globus-compute.readthedocs.io/en/latest/sdk/executor_user_guide.html#avoiding-serialization-errors for more information.
  warnings.warn(check_result, UserWarning)
Hello from node x3004c0s1b0n0, GPU 2
Hello from node x3004c0s1b0n0, GPU 3
Hello from node x3004c0s1b0n0, GPU 1
Hello from node x3004c0s1b0n0, GPU 0
Hello from node x3004c0s13b0n0, GPU 3
Hello from node x3004c0s13b0n0, GPU 2
Hello from node x3004c0s13b0n0, GPU 1
Hello from node x3004c0s13b0n0, GPU 0
Hello from node x3004c0s1b0n0, GPU 0
Hello from node x3004c0s1b0n0, GPU 1
Hello from node x3004c0s1b0n0, GPU 2
Hello from node x3004c0s1b0n0, GPU 3
Hello from node x3004c0s13b0n0, GPU 2
Hello from node x3004c0s13b0n0, GPU 0
Hello from node x3004c0s13b0n0, GPU 1
Hello from node x3004c0s13b0n0, GPU 3
```

Note the `place=scatter` line, which is important for multi-node jobs so the job's workers are spread across nodes.  With 4 workers per node, the script submits 8 tasks per node which will run in 2 batches.


## Troubleshooting

### Runaway job submission

The most common pitfall is an endpoint that loops, queuing PBS jobs that immediately fail (for example, because of a bad `worker_init` or an unreachable filesystem).  Because the MEP runs your UEP under your account **on Polaris or Crux**, you stop it from one of these machines:

```bash
# Login to Polaris or Crux and remove the endpoint pid file(s)
ssh polaris.alcf.anl.gov
rm ~/.globus_compute/*/daemon.pid
```

This stops all PBS submissions made on your behalf.  To diagnose, inspect the PBS submit scripts and job logs the MEP created under `~/.globus_compute/<endpoint_name>/submit_scripts` on Polaris (MEP user endpoint names begin with `uep`).

### Logs

The MEP creates a user endpoint (UEP) on the target machine.  The UEP will write logs to the user's home directory in `$HOME/.globus_compute`.  It can sometimes be helpful for debugging to examine the logs that live in that directory.  Each MEP created UEP will have its own subdirectory in `$HOME/.globus_compute`.

### Serialization across python versions

The your workstation where you are running the client and the Polaris MEP workers (python 3.13) may run different python versions.  To avoid serialization errors (a `ManagerLost` error mentioning serialization), every script that submits a function uses the `AllCodeStrategies` serializer, which sends the full function source to the endpoint:

```python
from globus_compute_sdk.serialize import ComputeSerializer, AllCodeStrategies
serializer = ComputeSerializer(strategy_code=AllCodeStrategies())
gce = Executor(endpoint_id=..., serializer=serializer, user_endpoint_config=...)
```

### A note on filesystems

The MEP runs your functions **on Polaris or Crux**, so any file paths your functions touch must live on a **Polaris-visible filesystem** — `home`, `eagle`, or `grand`.  This is why the `scheduler_options` in these scripts request `filesystems=home:eagle:grand` and the run directories live under `$HOME`.

## Running your own endpoints

Facility MEPs cover most common workloads, but they are only offered on some systems (currently Polaris and Crux) and expose a fixed set of configuration options.  If you need to run on a system without a MEP (for example, Aurora) or need options the MEP does not support, you can run your own **single-user endpoint** on a login node.  This means you install `globus-compute-endpoint`, write a config, and keep the endpoint process alive yourself — the operational burden the MEP otherwise handles for you.

The [ALCF Globus Compute repository](https://github.com/argonne-lcf/alcf-globus-compute) provides example config templates and instructions for running your own endpoints on ALCF systems.

# Globus Transfer

ALCF supports Globus transfer collections on the Home filesystem (mounted on Polaris, Crux, and Sophia), the Eagle filesystem (mounted on Polaris, Crux, and Sophia), and the Flare filesystem (mounted on Aurora).

| Filesystem  | Collection UUID |
| ------  | ---- |
| Home | 9032dd3a-e841-4687-a163-2720da731b5b |
| Eagle | 05d2c76a-e867-4f67-aa57-76edeb0beda0 |
| Grand | 3caddd4a-bb35-4c3d-9101-d9a0ad7f3a30 |
| Flare | f39a7a0f-5bfc-46ce-9615-ba9f8592814f |

Projects with allocations on Eagle can create their own Guest Collection, with project-specific permissions.  See the [documentation](https://docs.alcf.anl.gov/data-management/acdc/eagle-data-sharing/) for details.

## Example - transfer a file (`6_transfer_file.py`)

Workshop participants that are members of the `alcf_training` project will have access to the `home` and `eagle` filesystems.  This example shows a programmatic way of how to transfer a file from `eagle` to `home`.  We have prestaged a small test file on `eagle` for this example.  Globus also provides a web UI that allows for easy point-and-click transfers and a CLI tool.

To run the example, first paste your ALCF username in the indicated place and then run the script like this:
```bash
python 6_transfer_file.py
```

```python
import time
from globus_sdk import TransferClient, TransferData
from alcf_tokens.auth import get_service_authorizer

# This script transfers a file with Globus from the ALCF home filesystem to the
# eagle filesystem.  Before beginning paste your ALCF username below:

# Specify your ALCF USERNAME to find your home directory on the home collection, e.g.:
# ALCF_USERNAME = "csimpson"
ALCF_USERNAME = 

# Globus collection ids.
SRC_COLLECTION = "05d2c76a-e867-4f67-aa57-76edeb0beda0"  # eagle
DST_COLLECTION = "9032dd3a-e841-4687-a163-2720da731b5b"  # home

# Paths of data on the source collection (eagle) and
# the destination collection (home).
SRC_PATH = "/alcf_training/Service_Enabled_Science/test_transfer_file.txt"
DST_PATH = f"/{ALCF_USERNAME}/test_transfer_file.txt"

def main() -> None:
    authorizer = get_service_authorizer('globus-transfer')
    with TransferClient(authorizer=authorizer) as tc:
        transfer_request = TransferData(SRC_COLLECTION, DST_COLLECTION)
        transfer_request.add_item(SRC_PATH, DST_PATH)

        task = tc.submit_transfer(transfer_request)
        task_id = task["task_id"]
        print(f"Submitted transfer. Task ID: {task_id}.")

        print("Waiting for transfer to complete...")
        # Poll status of submitted transfer. Timeout after 60s.
        timeout = 60
        poll_interval = 15
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < timeout:
            status = tc.get_task(task_id)["status"]
            if status in ("SUCCEEDED", "FAILED"):
                break
            print(f"  still transferring... (status: {status})")
            time.sleep(poll_interval)

        # Print outcome.
        if time.perf_counter() - t0 >= timeout:
            print("Transfer polling timed out.")
            print(tc.get_task(task_id))
        else:
            print(f"Transfer {status}.")

if __name__ == "__main__":
    main()
```

Expected output will look like this:
```console
$ python 6_transfer_file.py
Submitted transfer. Task ID: 26bdd54e-bbb3-11f1-8f35-0affd5e180af.
Waiting for transfer to complete...
  still transferring... (status: ACTIVE)
Transfer SUCCEEDED.
```

You should now find the test file `test_transfer_file.txt` in your home directory on Polaris/Crux.

# Globus Flows

A [Globus Flow](https://docs.globus.org/api/flows/) chains actions run by different Globus services into a single, automated, **server-side** pipeline.  Once you start a run, Globus itself drives each step to completion — your script only starts the run and watches its status.

## Register and run a simple flow (`7_run_flow.py`)

This exercise builds a two-action flow:

1. **TransferFile** — transfer the test file from `eagle` to `home`, using the [Transfer action provider](https://docs.globus.org/api/transfer/action-providers/transfer/).  This is the same transfer as `6_transfer_file.py`, but now driven by the flow rather than by a `TransferClient` in your script.
2. **RunAdder** — run the registered `adder` function (from exercise 3) on a MEP, using the [Compute action provider](https://globus-compute.readthedocs.io/en/stable/actionprovider.html).  The transfer must finish before this step begins.

**Prerequisite:** run `3_register_function.py` first — it writes the `adder` function id to `REGISTERED_FUNC_ID`, which this script reads.

The flow definition is expressed in the form of a JSON object that chains actions as shown in [`7_run_flow.py`](./7_run_flow.py) that can take inputs.

Note that the authentication scope for flows is attached to each flow individually and therefore can't be authenticated prior to the registration of the flow and the creation of the flow id.  Therefore, after your flow is registrered, when the script runs the flow for the first time, you will be prompted to authenticate with Globus.

To run the example, first paste your ALCF username in the spot indicated in the exercise script (like was done for the transfer exercise) and then run the script:
```bash
python 7_run_flow.py
```

The script registers the flow, prompts the user for flow authentication, starts a run, prints a `https://app.globus.org/runs/<run_id>` link you can watch in the web app, and polls until the run reaches `SUCCEEDED` or `FAILED`.  Expect a few minutes: the transfer runs first, then the MEP has to start a PBS job on Polaris for the `adder` step.

The expected output will look like this:
```console
Registering flow with the Globus Flows service...
Registered flow. Flow ID: 1514c08f-4eb5-45c5-b4e7-a422bd9a6dc3

Please authenticate with Globus here:
-------------------------------------
https://auth.globus.org/v2/oauth2/authorize?...
-------------------------------------

Enter the resulting Authorization Code here: ...
Starting flow run with input: {'source_path': '/alcf_training/Service_Enabled_Science/test_transfer_file.txt', 'destination_path': '/csimpson/test_transfer_file.txt', 'endpoint_id': '9a947ba5-f537-4681-acf3-cc66485aadec', 'a': 5, 'b': 10}
Started run. Run ID: 1d224243-b9c1-4e30-b031-d5751792202d
Monitor it at https://app.globus.org/runs/1d224243-b9c1-4e30-b031-d5751792202d
Waiting for flow to complete (Ctrl-C to stop watching)...
  flow ACTIVE...
  flow ACTIVE...
  flow ACTIVE...
  flow ACTIVE...
Flow SUCCEEDED.
Compute action output (5 + 10): {'label': None, 'status': 'SUCCEEDED', 'details': {'result': [15], 'results': [{'output': 15, 'task_id': '907c9298-0b0b-4adf-8cb7-fc5ec2fcf56f'}]}, 'action_id': 'tg_3d1aa0c6-8c26-44d3-a5a7-38f99ff71bf8', 'manage_by': ['urn:globus:auth:identity:bd2b5002-d274-11e5-b446-93314fed2a79'], 'creator_id': 'urn:globus:auth:identity:bd2b5002-d274-11e5-b446-93314fed2a79', 'monitor_by': ['urn:globus:auth:identity:bd2b5002-d274-11e5-b446-93314fed2a79'], 'start_time': '2026-09-29T03:36:52.872171+00:00', 'state_name': 'RunAdder', 'release_after': None, 'display_status': 'All tasks completed', 'completion_time': '2026-09-29T03:37:08.727787+00:00'}
```

