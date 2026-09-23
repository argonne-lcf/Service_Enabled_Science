import sys
from alcf_tokens.auth import get_access_token, ServiceName

HEADERS = {
    "Authorization": f"Bearer {get_access_token(ServiceName.iri)}",
    "Content-Type": "application/json"
}

def get_filesystem_id_from_path(file_path: str) -> str | None:
    if file_path.startswith("/home/"):
        return "6115bd2c-957a-4543-abff-5fae52992ff2"
    elif file_path.startswith("/eagle/") or file_path.startswith("/lus/eagle/"):
        return "1c3ad9d4-2e91-42bc-becb-72b1fde1235c"
    else:
        print("File must be on /home/, /eagle/, or /lus/eagle/.")
        sys.exit(1)
