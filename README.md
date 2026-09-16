# Service_Enabled_Science
Demo materials for ALCF Service-Enabled Science Workshop

## ALCF Tokens

To gain access to services covered in this hackathon, we recommend to use the [alcf-tokens](https://pypi.org/project/alcf-tokens/) python package. With one single authentication, this centralized ALCF CLI tool will generate and retrieve Globus access tokens for the following services:

| Service | service-name |
|---|---|
| [ALCF Inference Service](https://docs.alcf.anl.gov/services/inference-endpoints/) | `inference` |
| [ALCF IRI API](https://docs.alcf.anl.gov/services/iri-api/) | `iri` |
| [Globus Compute](https://www.globus.org/compute) | `globus-compute` |
| [Globus Transfer](https://www.globus.org/data-transfer) | `globus-transfer` |

### Installation

If you prefer to use `uvx`, you can skip the installation instruction. 

```bash
pip install alcf-tokens
```

### Authentication

To properly gain access to all ALCF services, **make sure you authenticate with your ALCF credentials**.

```bash
alcf-tokens login --authorize-transfer home --authorize-transfer eagle
```

With a terminal, you can store your tokens with:
```bash
inference_token=$(alcf-tokens get-token inference)
iri_token=$(alcf-tokens get-token iri)
globus_compute_token=$(alcf-tokens get-token globus-compute)
globus_transfer_token=$(alcf-tokens get-token globus-transfer)
```

With python, you can store them with:
```python
from alcf_tokens.auth import get_access_token, ServiceName

inference_token = get_access_token(ServiceName.inference)
iri_token = get_access_token(ServiceName.iri)
globus_compute_token = get_access_token(ServiceName.globus_compute)
globus_transfer_token = get_access_token(ServiceName.globus_transfer)
```

### Troubleshooting

If you have issues with your tokens, please logout from Globus by visiting [https://app.globus.org/logout](https://app.globus.org/logout), open a new incognito browser, and restart a new authentication flow. 