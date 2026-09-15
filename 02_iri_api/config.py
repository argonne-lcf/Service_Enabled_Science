from alcf_tokens.auth import get_access_token, ServiceName

# Build request headers with your IRI token
HEADERS = {
    "Authorization": f"Bearer {get_access_token(ServiceName.iri)}",
    "Content-Type": "application/json"
}