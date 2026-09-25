from globus_compute_sdk import Executor, Client
from globus_compute_sdk.serialize import ComputeSerializer, AllCodeStrategies
from concurrent.futures import as_completed
from alcf_tokens.auth import get_service_authorizer

# A multiuser globus compute endpoint is configured at *submit time* through the
# user_endpoint_config dictionary.  This example shows some common options and
# how to use them with the Polaris MEP.

POLARIS_MEP = "9a947ba5-f537-4681-acf3-cc66485aadec"
ACCOUNT = "alcf_training"
QUEUE = "debug"


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
# As an alternative to example 1, here we open a context for the Executor and
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
