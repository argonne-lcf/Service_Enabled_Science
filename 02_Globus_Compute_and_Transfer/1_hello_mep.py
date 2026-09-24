from globus_compute_sdk import Executor, Client
from globus_compute_sdk.serialize import ComputeSerializer, AllCodeStrategies
from alcf_tokens.auth import get_service_authorizer

# This script is intended to be run from your local machine where you have
# built the workshop client environment.  It sends a function to the 
# facility-supported Polaris multi-user endpoint (MEP), which runs the 
# function on a Polaris compute node by submitting a PBS job on the user's behalf.

# The Polaris MEP is already running as a facility service -- there is no
# endpoint for you to configure or start.  You only need its UUID.
POLARIS_MEP = "9a947ba5-f537-4681-acf3-cc66485aadec"
CRUX_MEP = "fd8b54bb-9452-411d-8e3a-09408156a886" # You can also try with Crux

# Project and queue used to charge and schedule the PBS jobs the MEP submits
# on your behalf.
ACCOUNT = "datascience"
QUEUE = "debug"

# A simple function that reports the environment it runs in on Polaris.
# This is a useful first test when checking that the MEP is reachable.
def hello_affinity():
    import sys
    import socket
    import parsl
    import globus_compute_endpoint

    return f""" Hello! I'm Polaris! Here's some of my info:
                hostname: {socket.gethostname()}
                remote environment: {sys.executable}
                python version: {sys.version}
                parsl version: {parsl.__version__}
                GCE version: {globus_compute_endpoint.__version__}
            """

# To use alcf-tokens for authentication, create a Client and Authorizer:
# To authenticate directly with the Executor, this is not necessary
authorizer = get_service_authorizer("globus-compute")
gcc = Client(authorizer=authorizer)

# The AllCodeStrategies serializer avoids serialization errors 
# when the client (Aurora) and the MEP workers (Polaris, python 3.13) 
# run different python versions.
serializer = ComputeSerializer(strategy_code=AllCodeStrategies())

# user_endpoint_config is passed to the MEP, which uses it to provision a
# user endpoint (UEP) that submits PBS jobs under your account.  "account"
# and "queue" are always required.
polaris_gce = Executor(
    endpoint_id=POLARIS_MEP,
    serializer=serializer,
    client=gcc,
    user_endpoint_config={
        "account": ACCOUNT,
        "queue": QUEUE,
    },
)

crux_gce = Executor(
    endpoint_id=CRUX_MEP,
    serializer=serializer,
    client=gcc,
    user_endpoint_config={
        "account": ACCOUNT,
        "queue": QUEUE,
    },
)

print("Submitting hello_affinity to the Polaris MEP, waiting for result...")
polaris_future = polaris_gce.submit(hello_affinity)
print("Submitting hello_affinity to the Crux MEP, waiting for result...")
crux_future = crux_gce.submit(hello_affinity)

print('Polaris result:')
print(polaris_future.result())
print('Crux result:')
print(crux_future.result())

gce.shutdown()
