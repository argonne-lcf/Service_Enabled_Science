import time
from globus_sdk import TransferClient, TransferData
from alcf_tokens.auth import get_service_authorizer

# This script transfers a file with Globus without needing your own Globus
# client ID.  It uses the public native client bundled with alcf_tokens, so
# authentication is handled for you -- just log in once with:
#
#     alcf-tokens login --authorize-transfer eagle:data_access --authorize-transfer home:data_access
#
# after which the stored tokens are reused (and refreshed) automatically.

# Specify your ALCF USERNAME to find your home directory on the home collection, e.g.:
ALCF_USERNAME = "csimpson"
#ALCF_USERNAME = 

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
