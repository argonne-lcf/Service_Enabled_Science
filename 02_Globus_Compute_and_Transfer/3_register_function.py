from globus_compute_sdk import Client, Executor
from globus_compute_sdk.serialize import ComputeSerializer, AllCodeStrategies
from alcf_tokens.auth import get_service_authorizer

# This example both REGISTERS a function with the Globus service and CALLS it
# on the Polaris and Crux MEPs by its function id.
#
# Registration talks only to the Globus service (no endpoint, account, or
# queue needed).  A registered function is stored with the service and can be
# called later by its id -- registered functions are also the building blocks
# of Globus Flows.
#
# We register the function's *source code* (rather than a pickled object) so it
# is robust to python-version differences between the local client and the
# MEP workers (python 3.13).

POLARIS_MEP = "9a947ba5-f537-4681-acf3-cc66485aadec"
CRUX_MEP = "fd8b54bb-9452-411d-8e3a-09408156a886"
ACCOUNT = "alcf_training"
POLARIS_QUEUE = "debug"
CRUX_QUEUE = "debug"

source = '''
def adder(a, b):
    return a + b
'''

# Register the function with the Globus service and get back its id.
authorizer = get_service_authorizer('globus-compute')
gcc = Client(authorizer=authorizer)
func_id = gcc.register_source_code(
    source=source,
    function_name="adder",
    description="Adds two numbers",
)
print(f"Registered adder; id {func_id}")
with open("REGISTERED_FUNC_ID", 'w') as f:
    f.write(f"{func_id}")

# Call the registered function on the Polaris MEP by its id.
serializer = ComputeSerializer(strategy_code=AllCodeStrategies())
polaris_gce = Executor(
    endpoint_id=POLARIS_MEP,
    client=gcc,
    serializer=serializer,
    user_endpoint_config={
        "account": ACCOUNT,
        "queue": POLARIS_QUEUE,
    },
)
crux_gce = Executor(
    endpoint_id=CRUX_MEP,
    client=gcc,
    serializer=serializer,
    user_endpoint_config={
        "account": ACCOUNT,
        "queue": CRUX_QUEUE,
    },
)

print("Calling registered adder on the Polaris and Crux MEPs, waiting for results...")
polaris_future = polaris_gce.submit_to_registered_function(args=(5, 10), function_id=func_id)
crux_future = crux_gce.submit_to_registered_function(args=(2, 3), function_id=func_id)
print(f"Polaris result: 5 + 10 = {polaris_future.result()}")
print(f"Crux result: 2 + 3 = {crux_future.result()}")
polaris_gce.shutdown()
crux_gce.shutdown()
