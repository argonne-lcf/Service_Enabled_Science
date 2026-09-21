from globus_compute_sdk import Client, Executor
from globus_compute_sdk.serialize import ComputeSerializer, AllCodeStrategies

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
ACCOUNT = "alcf_training"
QUEUE = "debug"

source = '''
def adder(a, b):
    return a + b
'''

# Register the function with the Globus service and get back its id.
gcc = Client()
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
    serializer=serializer,
    user_endpoint_config={
        "account": ACCOUNT,
        "queue": QUEUE,
    },
)

print("Calling registered adder on the Polaris MEP, waiting for result...")
future = polaris_gce.submit_to_registered_function(args=(5, 10), function_id=func_id)
print(f"5 + 10 = {future.result()}")

polaris_gce.shutdown()
