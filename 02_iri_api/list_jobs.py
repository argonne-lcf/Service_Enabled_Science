import json
import requests
from alcf_tokens.auth import get_access_token, ServiceName

# Build request headers with your IRI token
headers = {
    "Authorization": f"Bearer {get_access_token(ServiceName.iri)}",
    "Content-Type": "application/json"
}

# Choose ALCF cluster
resource_id = "55c1c993-1124-47f9-b823-514ba3849a9a" # Polaris
#resource_id = "8b9b42f7-572a-4909-8472-a0453436304c" # Crux

# Define query parameters
params = {
    "historical": "true", # "true" will include completed jobs
    "limit": 10, # maximum number of jobs returned
    "offset": 0,
}

# Define optional filters
filters = {}
#filters = {"states": ["active"]}
#filters = {"states": ["active", "queued"]}
#filters = {"owner": "<your-alcf-username>"}
#filters = {"jobIds": ["12345", "12346", "12347"]}
#filters = {"queue": "debug"}
#filters = {"accountingId": "<your-compute-allocation>"}
filters = {"states": ["active"], "queue": "debug"}

# Submit request
response = requests.post(
    f"https://api.alcf.anl.gov/api/v1/compute/status/{resource_id}",
    params=params,
    json=filters,
    headers=headers,
)
print(json.dumps(response.json(), indent=2))