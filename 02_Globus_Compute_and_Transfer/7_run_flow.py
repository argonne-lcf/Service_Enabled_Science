import os
import time

import globus_sdk
from globus_sdk.scopes import GCSCollectionScopes, TransferScopes

from alcf_tokens.auth import build_user_app

# A Globus FLOW chains together actions run by different Globus services into a
# single, automated pipeline.  This flow has two actions:
#
#   1. TransferFile -- transfer the test file from eagle to home (the Globus
#      Transfer action provider), then
#   2. RunAdder     -- run the registered `adder` function on the Polaris MEP
#      (the Globus Compute action provider).
#
# The flow runs *server-side*: once started, Globus drives the transfer to
# completion and only then runs the function.  Your script just starts the run
# and watches its status.
#
# We reuse the public native client bundled with alcf_tokens, so you do NOT
# need your own Globus client ID.  The first time you run this you will be
# prompted to authenticate in a browser (Argonne LCF -> ALCF username +
# MobilePass+), granting consent for Flows, Transfer, and Compute.
#
# Here we define a flow that takes a PAYLOAD OF
# INPUTS at run time:
#
#     {"source_path": ..., "destination_path": ...,
#      "endpoint_id": ..., "a": ..., "b": ...}
#
# The flow definition references those inputs with JSONPath instead of literal
# values (a parameter named "foo.$" whose value is "$.input.foo" is filled in
# from the run input).  The same registered flow can then be started many
# times with different inputs -- different files to move, different numbers to
# add -- without re-registering it.
#

# --- ALCF username to create path to user's home ---------------
ALCF_USERNAME = 

EAGLE_COLLECTION = "05d2c76a-e867-4f67-aa57-76edeb0beda0"  # source (eagle)
HOME_COLLECTION = "9032dd3a-e841-4687-a163-2720da731b5b"   # destination (home)

# --- Compute endpoint and function -------------------------------------------
POLARIS_MEP = "9a947ba5-f537-4681-acf3-cc66485aadec"
ACCOUNT = "alcf_training"
QUEUE = "debug"

# The `adder` function id written by exercise 3 (3_register_function.py).
FUNC_ID_FILE = "REGISTERED_FUNC_ID"

# --- Action provider URLs ----------------------------------------------------
TRANSFER_ACTION_URL = "https://transfer.actions.globus.org/transfer"
COMPUTE_ACTION_URL = "https://compute.actions.globus.org/v3"

# --- The run payload: change these to run the same flow on different inputs ---
FLOW_INPUT = {
    "source_path": "/alcf_training/Service_Enabled_Science/test_transfer_file.txt",
    "destination_path": f"/{ALCF_USERNAME}/test_transfer_file.txt",
    "endpoint_id": POLARIS_MEP,  # which MEP runs adder; swap for another endpoint
    "a": 5,
    "b": 10,
}


def load_function_id() -> str:
    if not os.path.exists(FUNC_ID_FILE):
        raise SystemExit(
            f"'{FUNC_ID_FILE}' not found. Run 3_register_function.py first to "
            "register the adder function."
        )
    with open(FUNC_ID_FILE) as f:
        return f.read().strip()


def build_flow_definition(func_id: str) -> dict:
    """
    The two-state flow, parameterized on the run input.

    Note the "<name>.$" parameter keys: their values are JSONPath strings
    into the flow's run-time state.  The run body we pass becomes the root of
    that state ($), so a field "foo" from the payload is referenced as "$.foo"
    (NOT "$.input.foo" -- that form only applies if the body is nested under an
    "input" key).  Plain keys (source/destination collection ids, account,
    queue) stay constant across runs.
    """
    return {
        "Comment": "Transfer a file from eagle to home, then run adder on its inputs.",
        "StartAt": "TransferFile",
        "States": {
            "TransferFile": {
                "Type": "Action",
                "ActionUrl": TRANSFER_ACTION_URL,
                "Parameters": {
                    "source_endpoint": EAGLE_COLLECTION,
                    "destination_endpoint": HOME_COLLECTION,
                    "DATA": [
                        {
                            # Pulled from the run payload rather than hard-coded.
                            "source_path.$": "$.source_path",
                            "destination_path.$": "$.destination_path",
                        }
                    ],
                },
                "ResultPath": "$.TransferResult",
                "Next": "RunAdder",
            },
            "RunAdder": {
                "Type": "Action",
                "ActionUrl": COMPUTE_ACTION_URL,
                "Parameters": {
                    # Which MEP runs the function is a run-time input.
                    "endpoint_id.$": "$.endpoint_id",
                    "tasks": [
                        {
                            "function_id": func_id,
                            "kwargs": {
                                # adder(a, b) -- both from the run payload.
                                "a.$": "$.a",
                                "b.$": "$.b",
                            },
                        }
                    ],
                    "user_endpoint_config": {
                        "account": ACCOUNT,
                        "queue": QUEUE,
                    },
                },
                "ResultPath": "$.ComputeResult",
                "End": True,
            },
        },
    }


def build_input_schema() -> dict:
    """
    A JSON Schema describing the run payload.  Flows uses it to validate input
    before starting a run and to render an input form in the web app.
    """
    return {
        "type": "object",
        "required": ["source_path", "destination_path", "endpoint_id", "a", "b"],
        "properties": {
            "source_path": {
                "type": "string",
                "description": "Path of the file on the eagle collection.",
            },
            "destination_path": {
                "type": "string",
                "description": "Path to write on the home collection.",
            },
            "endpoint_id": {
                "type": "string",
                "description": "UUID of the compute endpoint (MEP) that runs adder.",
            },
            "a": {"type": "number", "description": "First number to add."},
            "b": {"type": "number", "description": "Second number to add."},
        },
    }


def run_flow_scope(flow_id: str) -> globus_sdk.Scope:
    """
    The scope needed to START this flow: the flow's user scope, with the
    Transfer scope as a dependency, which in turn needs each mapped
    collection's data_access scope.  (See 7_run_flow.py for the full
    explanation.)
    """
    transfer_scope = (
        TransferScopes.all
        .with_dependency(
            GCSCollectionScopes(EAGLE_COLLECTION).data_access.with_optional(True)
        )
        .with_dependency(
            GCSCollectionScopes(HOME_COLLECTION).data_access.with_optional(True)
        )
    )
    flow_scope = globus_sdk.SpecificFlowClient(flow_id).scopes.user
    return flow_scope.with_dependency(transfer_scope)


def main() -> None:
    func_id = load_function_id()

    #app = globus_sdk.UserApp("alcf-tokens", client_id=AUTH_CLIENT_ID)
    app = build_user_app(authorize_transfer=["eagle:data_access", "home:data_access"])

    # 1. Register the flow, now with an input schema describing its payload.
    flows_client = globus_sdk.FlowsClient(app=app)
    print("Registering flow with the Globus Flows service...")
    flow = flows_client.create_flow(
        title="Service Enabled Science: parameterized transfer then adder",
        definition=build_flow_definition(func_id),
        input_schema=build_input_schema(),
    )
    flow_id = flow["id"]
    print(f"Registered flow. Flow ID: {flow_id}")

    # 2. Add the run scope and start the flow, passing the payload as the run
    #    body.  Flows validates it against the input schema, then substitutes
    #    each "$.input.<field>" reference in the definition.
    app.add_scope_requirements({flow["globus_auth_scope"]: run_flow_scope(flow_id)})
    if app.login_required():
        app.login()
    flow_client = globus_sdk.SpecificFlowClient(flow_id, app=app)

    print(f"Starting flow run with input: {FLOW_INPUT}")
    run = flow_client.run_flow(body=FLOW_INPUT, label="param-transfer-then-adder")
    run_id = run["run_id"]
    print(f"Started run. Run ID: {run_id}")
    print(f"Monitor it at https://app.globus.org/runs/{run_id}")

    # 3. Poll until for flow completion.
    print("Waiting for flow to complete (Ctrl-C to stop watching)...")
    poll_interval = 15
    while True:
        run = flows_client.get_run(run_id)
        status = run["status"]
        if status in ("SUCCEEDED", "FAILED"):
            break
        print(f"  flow {status}...")
        time.sleep(poll_interval)

    print(f"Flow {status}.")
    if status == "SUCCEEDED":
        details = run.get("details", {})
        result = details.get("output", {}).get("ComputeResult", {})
        print(f"Compute action output ({FLOW_INPUT['a']} + {FLOW_INPUT['b']}): {result}")
    else:
        print(run.get("details"))


if __name__ == "__main__":
    main()
