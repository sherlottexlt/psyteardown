"""Quick test to verify DeepSeek API connectivity and basic functionality."""

import os
from psyteardown.product.contract_model import DeepSeekProductContractModel
from psyteardown.product.env import get_project_env

# Test basic connectivity
api_key = get_project_env("DEEPSEEK_API_KEY")
if not api_key:
    print("❌ DEEPSEEK_API_KEY not set")
    exit(1)

print(f"✅ API key configured: {api_key[:6]}...{api_key[-4:]}")

try:
    model = DeepSeekProductContractModel()
    print(f"✅ Model initialized: {model.model}")
    print(f"   Base URL: {model._base_url}")
    print(f"   Timeout: {model._timeout}s")
    print()

    # Test simple generation
    print("Testing simple generation...")
    system = "You are a helpful assistant."
    prompt = "Say 'hello' in JSON format: {\"message\": \"hello\"}"

    print(f"System: {system}")
    print(f"Prompt: {prompt}")
    print()

    reply = model.generate(system=system, prompt=prompt)

    print(f"✅ Generation successful!")
    print(f"   Model: {reply.model}")
    print(f"   Input tokens: {reply.input_tokens}")
    print(f"   Output tokens: {reply.output_tokens}")
    print(f"   Truncated: {reply.truncated}")
    print(f"   Response: {reply.text[:200]}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
