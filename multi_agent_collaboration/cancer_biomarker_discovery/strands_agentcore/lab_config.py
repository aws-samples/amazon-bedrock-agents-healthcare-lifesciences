"""Model used by every agent in this lab (notebooks and deployed AgentCore runtimes).

Default: Amazon Nova 2 Lite. Amazon models need no Anthropic use case form and no AWS
Marketplace subscription, so they work in a fresh account. To try another model, change
the default below or set LAB_MODEL_ID before starting the kernel, for example
  apac.amazon.nova-pro-v1:0
  global.anthropic.claude-sonnet-4-6   (needs the Anthropic use case form in the account)
"""
import os

MODEL_ID = os.environ.get("LAB_MODEL_ID", "global.amazon.nova-2-lite-v1:0")
