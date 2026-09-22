import sys

def get_filesystem_id_from_path(file_path: str) -> str | None:
    if file_path.startswith("/home/"):
        return "6115bd2c-957a-4543-abff-5fae52992ff2"
    elif file_path.startswith("/eagle/"):
        return "1c3ad9d4-2e91-42bc-becb-72b1fde1235c"
    else:
        print("File must be on /home/ or /eagle/.")
        sys.exit(1)
