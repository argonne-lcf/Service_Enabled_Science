from globus_compute_sdk import Executor, Client
from globus_compute_sdk.serialize import ComputeSerializer, AllCodeStrategies
from concurrent.futures import as_completed
from alcf_tokens.auth import get_service_authorizer

# By default the MEP runs functions with the SimpleLauncher on a single node.
# To spread work across multiple nodes, switch the launcher to MpiExecLauncher
# and request a multi-node block.  This example runs one function per node.

POLARIS_MEP = "9a947ba5-f537-4681-acf3-cc66485aadec"
ACCOUNT = "alcf_training"
QUEUE = "debug"
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
    # place=scatter is important for multi-node jobs: it spreads the job's
    # nodes across the machine.  Remember: Polaris filesystems only.
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

    # Two tasks per node.  With one worker per node they run one at a time
    # on each node, so you should see each hostname reported twice.
    futures = [gce.submit(query_host) for _ in range(2 * NUM_NODES * 4)]

    print(f"Submitted {2 * NUM_NODES * 4} tasks across {NUM_NODES} nodes, "
            "waiting for results...")
    for f in as_completed(futures):
        print(f.result())
