# ALCF Inference Service


The ALCF Inference Service exposes industry-standard APIs for interacting with LLMs hosted at ALCF:

- [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- [OpenAI Responses](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [Anthropic Messages](https://platform.claude.com/docs/en/api/http/beta/messages/create)

Refer to the [ALCF Inference Service User Guide](https://docs.alcf.anl.gov/services/inference-endpoints/) for additional details on the available clusters, hosted models, and capabilities.  The LLM APIs provide broad interoperability with existing libraries, frameworks, and agentic applications.  Scientific workflows leveraging other AI providers, such as the Genesis Mission Model Access Gateway (MAG), can be readily configured to use the Inference Service as another source of tokens.

## REST API
You can also interact with the ALCF Inference APIs directly using the HTTPS client of your choice.  `curl` often provides a quick, transparent way to test the system:

```bash
token=$(alcf-tokens get-token inference)

curl \
  -H "Authorization: Bearer $token" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-oss-120b", "messages": [{"role": "user", "content": "hello!"}]}' \
  https://inference-api.alcf.anl.gov/resource_server/metis/api/v1/chat/completions | jq
```

## Web Chat UI

Navigate to <https://inference.alcf.anl.gov> and log in with your ALCF credentials.

This is an ALCF deployment of Open WebUI, a web-hosted chat application.  The
backend maintains persistent chat sessions and sends requests (like
the one illustrated above) to the inference API on your behalf.

## alcf-ai CLI

[`alcf-ai`](https://pypi.org/project/alcf-ai/) provides a command-line interface for
convenient shell-based interaction with the inference APIs.

Check your inference access token validity:

```bash
$ alcf-tokens test-token inference
{"ready": true, "error": null}
```

If it's expired or invalid, use `alcf-tokens login` to authenticate with your ALCF credentials.

### CLI: Discover running models

```bash
# Query entire model catalog:
$ alcf-ai ls-endpoints

# Query currently hot models:
$ alcf-ai ls-jobs metis
```

### CLI: Chat

```bash
# Prompt on command line arguments:
alcf-ai chat --cluster metis --model gpt-oss-120b Hello!
Hello! 👋 How can I help you today?                                       

# System prompt + stdin:
url="https://raw.githubusercontent.com/pytorch/pytorch/refs/heads/main/torch/nn/parallel/data_parallel.py"
curl $url | alcf-ai chat -s "Explain this code"  --cluster metis --model gpt-oss-120b --stream
```

## Python SDK

In addition to the CLIs introduced above, `alcf_ai` provides a Python SDK for authenticating with and using the inference service.  

For example, you can obtain a standard OpenAI Python Client that's automatically configured for use with ALCF models on a given cluster:

```python
from rich import print
from alcf_ai import InferenceClient

request = {
    "model": "gpt-oss-120b",
    "messages": [{"role": "user", "content": "hellO"}],
}

print(
 InferenceClient()          # handles your ALCF token
   .clusters("metis")       # picks a cluster
     .openai                # a standard OpenAI client
       .chat.completions.create(**request)
)
```

Run the following examples in a Python environment with [`alcf-ai`](https://pypi.org/project/alcf-ai/) installed.  You can start a REPL with ephemeral dependencies using `uv run --with alcf-ai python`.  The example scripts contain [inline dependencies](https://docs.astral.sh/uv/guides/scripts/#declaring-script-dependencies) and can therefore be run using `uv run example.py` without setting up an environment first.

| Script | Description |
|---|---|
| [`01_list_endpoints.py`](01_list_endpoints.py) | Which models exist, and which are running right now |
| [`02_chat_completion.py`](02_chat_completion.py) | Get an OpenAI client and send your first prompt |
| [`03_response_anatomy.py`](03_response_anatomy.py) | What's inside a response: answers, thinking, and tool calls |
| [`04_agent_loop.py`](04_agent_loop.py) | Build a tiny agent by hand and watch its context grow |



### 1. List endpoints

What models can I use? The API provides **catalog** views, listing every model the service knows about. The **jobs** view tells you which ones are running and ready to answer immediately.


```python
from alcf_ai import InferenceClient

client = InferenceClient()

# Every model:
catalog = client.list_endpoints()

# What's running on Metis right now:
jobs = client.clusters("metis").get_jobs()
print([job["Models"] for job in jobs["running"]])
```

```bash
$ uv run 03_ALCF_Inference_Service/01_list_endpoints.py

Running on Metis right now:
  🔥 gemma-4-31B-it
  🔥 gpt-oss-120b
  🔥 Mistral-Large-3-675B-Instruct-2512
```

### 2. Create OpenAI Chat Completions

Each cluster exposes an OpenAI-compatible API. `.openai` gives you a regular `openai.OpenAI` object that is already wired up to your ALCF credentials:

```python
from alcf_ai import InferenceClient

client = InferenceClient()
openai_client = client.clusters("metis").openai
```

`openai_client` interoperates with any framework that uses the OpenAI Python SDK. 

A chat is a list of **messages**, each with a `role`:

| Role | Who's talking | Example |
|---|---|---|
| `system` | App, setting the ground rules | *"You are a concise assistant for HPC users."* |
| `user` | The human asking | *"What is a supercomputer?"* |
| `assistant` | The model's replies | *"A supercomputer is..."* |
| `tool` | Results from tools you ran (see below) | `{"status": "up"}` |

```python
response = openai_client.chat.completions.create(
    model="gpt-oss-120b",
    messages=[
        {"role": "system", "content": "You are a concise assistant for HPC users."},
        {"role": "user", "content": "In two sentences: what is a supercomputer?"},
    ],
)
print(response.choices[0].message.content)
```

Want to see the words as they're generated? Add `stream=True` and loop over the chunks:

```python
stream = openai_client.chat.completions.create(
    model="gpt-oss-120b",
    messages=[{"role": "user", "content": "Write a sonnet about GPUs."}],
    temperature=1.5,
    stream=True,
)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

```bash
$ uv run 03_ALCF_Inference_Service/02_chat_completion.py

🤖 A supercomputer is an extremely high‑performance computing system that aggregates thousands to millions of processor cores, massive memory, and specialized interconnects to execute complex calculations at speeds far beyond ordinary computers. It is used for tasks such as climate modeling, molecular simulations, and large‑scale data analytics that require massive parallel processing and rapid data throughput.

🤖 **A Silicon Sonnet for the GPU**

When shadowed dawn lifts veil from night’s thin screen,  
The quiet hum of countless cores awakens,  
They stitch together light that none have seen,  
And warp the world in shimmering equations.  

Arrayed in parallel, they fleetly parse  
The data‑sea, where frames are forged and blown—  
From texture’d seas to ray‑traced amber stars,  
Each pixel dances in a breath of chrome.  

Yet in this steel‑born marvel lies such heart—  
A lattice of memory, a spark of art.  
When artists speak in shaders, code, and code,  
The GPU replies, a polyphonic ode.  

So sing, great card, in binary refrain:  
Your power paints both logic’s fire and reign.
```

### 3. Anatomy of a response

`response.choices[0].message.content` got us the answer, but the response has
much more in it.  For a labelled tour:

```bash
$ uv run 03_ALCF_Inference_Service/03_response_anatomy.py
```


### 4. Build an agent from scratch

An **agent** is an LLM plus a loop of ordinary code (the **harness**) that:

1. sends the conversation to the LLM,
2. runs any tools the LLM asks for,
3. appends the tool results to the conversation,
4. repeats until the LLM gives an answer.


The LLM is **stateless**: it remembers nothing between requests.  The harness is responsible for maintaining the full, growing list of messages in memory. 

On every request, the harness re-sends **the whole list**, and after every step it **appends** to it.

```
Request #1  (157 prompt tokens)
│ tools      get_system_status(name)
│ system     You are a helpful ALCF assistant. Be brief.
│ user       Is Aurora up right now?
└──► LLM replies: call get_system_status(name="Aurora")

Request #2  (221 prompt tokens)
│ tools      get_system_status(name)
│ system     You are a helpful ALCF assistant. Be brief.
│ user       Is Aurora up right now?
│ assistant  call get_system_status(name="Aurora")   ◄── the LLM's reply, appended
│ tool       {"name": "Aurora", "status": "up"}       ◄── the tool result, appended
└──► LLM replies: "Aurora is currently up."
```

Each tool call adds messages, so a long-running agent's context keeps getting bigger (and slower and more expensive) until it hits the model's context limit. Managing that growth is one of the central problems in agent design.

```bash
# No tool calls needed:
uv run 03_ALCF_Inference_Service/04_agent_loop.py "what is 8+8?" --step

# Several tool calls:
uv run 03_ALCF_Inference_Service/04_agent_loop.py "Is Aurora up? What about Polaris? Crux? Frontier? Sophia?"
```

#### 🧪 Try it yourself

**Add a second tool.**  Write a new function to leverage the IRI API, describe it in `TOOLS`, and register it in `TOOL_FUNCTIONS`. The loop itself doesn't change.  Can the agent now use the IRI API if you ask a relevant question?