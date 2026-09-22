# /// script
# requires-python = ">=3.10"
# dependencies = ["alcf-ai>=0.13"]
# ///
"""
Step 2: Get an OpenAI client and send your first chat completion.

    uv run 02_chat_completion.py
"""

from alcf_ai import InferenceClient

client = InferenceClient()

# Each cluster exposes an OpenAI-compatible API:
openai_client = client.clusters("metis").openai

# A single request: blocks until full response:
response = openai_client.chat.completions.create(
    model="gpt-oss-120b",
    messages=[
        {"role": "system", "content": "You are a concise assistant for HPC users."},
        {"role": "user", "content": "In two sentences: what is a supercomputer?"},
    ],
)
print("🤖", response.choices[0].message.content)

# Response streamed token-by-token
print("\n🤖 ", end="")
stream = openai_client.chat.completions.create(
    model="gpt-oss-120b",
    messages=[{"role": "user", "content": "Write a sonnet about GPUs."}],
    temperature=1.5,
    stream=True,
)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
print()
