import os
from dotenv import load_dotenv

from alcf_tokens.auth import get_access_token, ServiceName

HEADERS = {
    "Authorization": f"Bearer {get_access_token(ServiceName.iri)}",
    "Content-Type": "application/json"
}

load_dotenv()
RESOURCE_ID = os.environ.get("RESOURCE_ID")
NODES = os.environ.get("NODES")
WALLTIME_SEC = os.environ.get("WALLTIME_SEC")
QUEUE = os.environ.get("QUEUE")
COMPUTE_ALLOCATION = os.environ.get("COMPUTE_ALLOCATION")
STDOUT_PATH = os.environ.get("STDOUT_PATH")
STDERR_PATH = os.environ.get("STDERR_PATH")
COMMANDS = os.environ.get("COMMANDS")

