#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Interactive agent chat tester for local and remote agents

Tests agent invocation with conversation continuity:
- Remote mode (default): Chat with deployed agent via Cognito authentication
- Local mode (--local): Chat with agent running on localhost:8080
- Automatically detects pattern from config.yaml

Usage:
    # Remote agent testing (prompts for credentials)
    uv run scripts/test-agent.py

    # Local agent testing (agent must be running on localhost:8080)
    uv run scripts/test-agent.py --local

    # Override pattern from config
    uv run scripts/test-agent.py --pattern strands-single-agent
"""

import argparse
import atexit
import getpass
import json
import signal
import socket
import subprocess  # nosec B404 - subprocess used securely with explicit parameters
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import requests
from colorama import Fore, Style

# Add scripts directory to path for reliable imports
scripts_dir = Path(__file__).parent.parent / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

# Import shared utilities
from utils import (
    authenticate_cognito,
    create_mock_jwt,
    generate_session_id,
    get_stack_config,
    print_msg,
    print_section,
)

# Global variable to track agent process
_agent_process: Optional[subprocess.Popen] = None


def generate_trace_id() -> str:
    """
    Generate X-Amzn-Trace-Id header value for AWS request tracing.

    Returns:
        str: Trace ID in AWS X-Ray format
    """
    timestamp_hex = format(int(time.time()), "x")
    return f"1-{timestamp_hex}-{generate_session_id()}"


def check_port_available(port: int = 8080) -> bool:
    """
    Check if a port is available for connection.

    Args:
        port (int): Port number to check

    Returns:
        bool: True if port is available, False otherwise
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex(("localhost", port))
        sock.close()
        return result == 0
    except Exception:
        return False


def start_local_agent(
    memory_id: str, region: str, stack_name: str, pattern: str
) -> subprocess.Popen:
    """
    Start the local agent in a background process.

    Args:
        memory_id (str): Memory ID for the agent
        region (str): AWS region
        stack_name (str): CloudFormation stack name for SSM parameter lookup
        pattern (str): Agent pattern name (e.g., 'strands-single-agent', 'langgraph-single-agent')

    Returns:
        subprocess.Popen: Subprocess object for the running agent
    """
    global _agent_process

    # Map pattern to agent file
    pattern_files = {
        "strands-single-agent": "basic_agent.py",
        "langgraph-single-agent": "langgraph_agent.py",
    }

    agent_file = pattern_files.get(pattern)
    if not agent_file:
        print_msg(f"Unknown pattern: {pattern}", "error")
        print(f"Available patterns: {', '.join(pattern_files.keys())}")
        sys.exit(1)

    agent_path = Path(__file__).parent.parent / "patterns" / pattern / agent_file

    if not agent_path.exists():
        print_msg(f"Agent file not found: {agent_path}", "error")
        sys.exit(1)

    # Security validation: ensure agent_path is within the patterns directory
    patterns_dir = Path(__file__).parent.parent / "patterns"
    try:
        agent_path.resolve().relative_to(patterns_dir.resolve())
    except ValueError:
        print_msg(
            f"Security error: Agent path outside patterns directory: {agent_path}",
            "error",
        )
        sys.exit(1)

    print(f"Starting local agent at {agent_path}...")
    print(f"  Pattern: {pattern}")
    print(f"  Memory ID: {memory_id}")
    print(f"  Region: {region}")
    print(f"  Stack Name: {stack_name}\n")

    # Set up environment variables
    env = {
        **dict(subprocess.os.environ),
        "MEMORY_ID": memory_id,
        "AWS_DEFAULT_REGION": region,
        "STACK_NAME": stack_name,
    }

    # Start agent process
    try:
        _agent_process = subprocess.Popen(  # nosec B607 B603 - command constructed from validated path, shell=False
            ["uv", "run", str(agent_path)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,  # Explicitly disable shell
        )

        # Wait for agent to start (check port becomes available)
        print("Waiting for agent to start on port 8080...")
        for i in range(30):  # Wait up to 30 seconds
            if check_port_available(8080):
                print_msg("Agent started successfully", "success")
                return _agent_process
            time.sleep(1)

        print_msg("Agent failed to start (timeout)", "error")
        _agent_process.terminate()
        sys.exit(1)

    except Exception as e:
        print_msg(f"Failed to start agent: {e}", "error")
        sys.exit(1)


def stop_local_agent() -> None:
    """Stop the local agent process if running."""
    global _agent_process
    if _agent_process:
        print("\nStopping local agent...")
        _agent_process.terminate()
        try:
            _agent_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _agent_process.kill()
        print_msg("Agent stopped", "success")


# Register cleanup handler
atexit.register(stop_local_agent)


def signal_handler(sig, frame):
    """Handle interrupt signal."""
    print("\n")
    stop_local_agent()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def invoke_agent(
    url: str,
    prompt: str,
    session_id: str,
    user_id: str = "local-test-user",
    headers: Optional[Dict[str, str]] = None,
) -> None:
    """
    Invoke agent and print raw streaming events in real-time.

    Args:
        url (str): Agent endpoint URL
        prompt (str): User prompt/query
        session_id (str): Session ID for conversation continuity
        user_id (str): User ID for mock JWT in local testing only. In remote mode,
            the real Cognito JWT carries the user identity, user_id is never sent
            in the payload to prevent prompt injection impersonation.
        headers (Optional[Dict[str, str]]): Optional HTTP headers
    """
    payload = {
        "prompt": prompt,
        "runtimeSessionId": session_id,
    }

    if headers is None:
        # Local mode: generate a mock JWT so the agent can extract user_id
        # from the Authorization header, matching the production auth flow.
        mock_token = create_mock_jwt(user_id)
        headers = {"Authorization": f"Bearer {mock_token}"}
    headers["Content-Type"] = "application/json"

    try:
        response = requests.post(
            url, headers=headers, json=payload, stream=True, timeout=60
        )

        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}: {response.text}")
            return

        # Parse streaming events and display clean text output
        print(f"{Fore.GREEN}Agent:{Style.RESET_ALL} ", end="", flush=True)
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            try:
                chunk = json.loads(line[6:])

                # LangGraph: AIMessageChunk with content array
                if chunk.get("type") == "AIMessageChunk" and isinstance(
                    chunk.get("content"), list
                ):
                    for block in chunk["content"]:
                        if block.get("type") == "text" and block.get("text"):
                            print(block["text"], end="", flush=True)
                        elif block.get("type") == "tool_use" and block.get("name"):
                            print(
                                f"\n{Fore.YELLOW}[Tool: {block['name']}]{Style.RESET_ALL} ",
                                end="",
                                flush=True,
                            )

                # LangGraph: ToolMessage result
                elif chunk.get("type") == "tool":
                    result = chunk.get("content", "")
                    if len(result) > 200:
                        result = result[:200] + "..."
                    print(
                        f"\n{Fore.YELLOW}[Result: {result}]{Style.RESET_ALL}",
                        flush=True,
                    )

                # Strands: text token
                elif isinstance(chunk.get("data"), str):
                    print(chunk["data"], end="", flush=True)

                # Strands: tool use
                elif chunk.get("current_tool_use") and chunk.get(
                    "current_tool_use", {}
                ).get("name"):
                    tool = chunk["current_tool_use"]
                    if chunk.get("delta", {}).get("toolUse", {}).get("input") == "":
                        print(
                            f"\n{Fore.YELLOW}[Tool: {tool['name']}]{Style.RESET_ALL} ",
                            end="",
                            flush=True,
                        )

                # Strands: tool result
                elif chunk.get("message", {}).get("role") == "user":
                    for content in chunk["message"].get("content", []):
                        if "toolResult" in content:
                            result = str(content["toolResult"].get("content", ""))
                            if len(result) > 200:
                                result = result[:200] + "..."
                            print(
                                f"\n{Fore.YELLOW}[Result: {result}]{Style.RESET_ALL}",
                                flush=True,
                            )

            except (json.JSONDecodeError, KeyError):
                continue
        print()  # Final newline

    except requests.exceptions.ConnectionError:
        print_msg(f"Could not connect to {url}", "error")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")


def run_chat(local_mode: bool, config: Dict[str, str]) -> None:
    """
    Run interactive chat session.

    Args:
        local_mode (bool): Whether to use local mode
        config (Dict[str, str]): Configuration dictionary
    """
    session_id = generate_session_id()

    print_section("Interactive Agent Chat")
    print(f"Session ID: {session_id}")
    print(
        f"Mode: {'Local (localhost:8080)' if local_mode else 'Remote (deployed agent)'}"
    )
    print(
        f"\n{Fore.YELLOW}💡 Type 'exit' or 'quit' to end, or press Ctrl+C{Style.RESET_ALL}\n"
    )

    while True:
        try:
            prompt = input(f"{Fore.CYAN}You:{Style.RESET_ALL} ").strip()

            if not prompt:
                continue

            if prompt.lower() in ["exit", "quit"]:
                print(f"\n{Fore.GREEN}Goodbye!{Style.RESET_ALL}")
                break

            # Invoke agent
            start_time = time.time()

            if local_mode:
                # Local mode
                invoke_agent(
                    url="http://localhost:8080/invocations",
                    prompt=prompt,
                    session_id=session_id,
                    user_id="local-test-user",
                )
            else:
                # Remote mode
                endpoint = f"https://bedrock-agentcore.{config['region']}.amazonaws.com"
                escaped_arn = requests.utils.quote(config["runtime_arn"], safe="")
                url = f"{endpoint}/runtimes/{escaped_arn}/invocations?qualifier=DEFAULT"

                headers = {
                    "Authorization": f"Bearer {config['access_token']}",
                    "X-Amzn-Trace-Id": generate_trace_id(),
                    "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
                }

                invoke_agent(
                    url=url,
                    prompt=prompt,
                    session_id=session_id,
                    headers=headers,
                )

            elapsed = time.time() - start_time
            print(f"\n{Fore.CYAN}[Completed in {elapsed:.2f}s]{Style.RESET_ALL}\n")

        except KeyboardInterrupt:
            print(f"\n\n{Fore.GREEN}Goodbye!{Style.RESET_ALL}")
            break
        except EOFError:
            print(f"\n\n{Fore.GREEN}Goodbye!{Style.RESET_ALL}")
            break


def run_terminology_test_suite(
    url: str,
    session_id: str,
    headers: Optional[Dict[str, str]] = None,
) -> None:
    """
    Run automated test suite for Terminology Agent with medical terminology queries.

    Args:
        url (str): Agent endpoint URL
        session_id (str): Session ID for tests
        headers (Optional[Dict[str, str]]): Optional HTTP headers for authentication
    """
    print_section("TERMINOLOGY AGENT TEST SUITE")
    print("Running automated tests with medical terminology queries...\n")

    test_cases = [
        {
            "name": "Simple Term Lookup",
            "prompt": "What is the MONDO ID for diabetes?",
            "expected_keywords": ["MONDO", "diabetes"],
        },
        {
            "name": "Term with Hierarchy",
            "prompt": "Show me the parent and child terms for myocardial infarction in MONDO",
            "expected_keywords": ["myocardial infarction", "parent", "child"],
        },
        {
            "name": "Multi-Ontology Search",
            "prompt": "Find information about 'insulin' in both ChEBI and GO ontologies",
            "expected_keywords": ["insulin", "ChEBI", "GO"],
        },
        {
            "name": "Term Standardization",
            "prompt": "Standardize these terms: heart attack, high blood pressure",
            "expected_keywords": ["heart attack", "blood pressure"],
        },
        {
            "name": "Ontology Information",
            "prompt": "Tell me about the MONDO ontology - what is it for?",
            "expected_keywords": ["MONDO", "ontology"],
        },
    ]

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(test_cases)}: {test['name']}")
        print(f"{'='*60}")
        print(f"{Fore.CYAN}Prompt:{Style.RESET_ALL} {test['prompt']}\n")

        start_time = time.time()

        # Collect response
        response_text = []
        tools_used = []

        try:
            payload = {
                "prompt": test["prompt"],
                "runtimeSessionId": f"{session_id}-test-{i}",
            }

            if headers is None:
                mock_token = create_mock_jwt("test-user")
                test_headers = {"Authorization": f"Bearer {mock_token}"}
            else:
                test_headers = headers.copy()
            test_headers["Content-Type"] = "application/json"

            response = requests.post(
                url, headers=test_headers, json=payload, stream=True, timeout=60
            )

            if response.status_code != 200:
                print(f"{Fore.RED}❌ Error: HTTP {response.status_code}{Style.RESET_ALL}")
                results.append({"name": test["name"], "status": "FAIL", "error": response.text})
                continue

            print(f"{Fore.GREEN}Agent:{Style.RESET_ALL} ", end="", flush=True)
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                try:
                    chunk = json.loads(line[6:])

                    # Extract text
                    if isinstance(chunk.get("data"), str):
                        response_text.append(chunk["data"])
                        print(chunk["data"], end="", flush=True)

                    # Extract tool usage (Strands)
                    elif chunk.get("current_tool_use") and chunk.get("current_tool_use", {}).get("name"):
                        tool = chunk["current_tool_use"]
                        if chunk.get("delta", {}).get("toolUse", {}).get("input") == "":
                            tool_name = tool["name"]
                            tools_used.append(tool_name)
                            print(f"\n{Fore.YELLOW}[Tool: {tool_name}]{Style.RESET_ALL} ", end="", flush=True)

                    # Extract tool usage (LangGraph)
                    elif chunk.get("type") == "AIMessageChunk":
                        for block in chunk.get("content", []):
                            if block.get("type") == "text" and block.get("text"):
                                response_text.append(block["text"])
                                print(block["text"], end="", flush=True)
                            elif block.get("type") == "tool_use" and block.get("name"):
                                tools_used.append(block["name"])
                                print(f"\n{Fore.YELLOW}[Tool: {block['name']}]{Style.RESET_ALL} ", end="", flush=True)

                except (json.JSONDecodeError, KeyError):
                    continue

            print("\n")

            elapsed = time.time() - start_time
            full_response = "".join(response_text)

            # Evaluate result
            has_response = len(full_response) > 0
            has_keywords = any(kw.lower() in full_response.lower() for kw in test["expected_keywords"])

            if has_response and has_keywords:
                status = f"{Fore.GREEN}✅ PASS{Style.RESET_ALL}"
                results.append({"name": test["name"], "status": "PASS"})
            elif has_response:
                status = f"{Fore.YELLOW}⚠️  PARTIAL{Style.RESET_ALL}"
                results.append({"name": test["name"], "status": "PARTIAL"})
            else:
                status = f"{Fore.RED}❌ FAIL{Style.RESET_ALL}"
                results.append({"name": test["name"], "status": "FAIL"})

            print(f"Status: {status}")
            print(f"Time: {elapsed:.2f}s")
            print(f"Response length: {len(full_response)} chars")
            if tools_used:
                print(f"Tools used: {', '.join(set(tools_used))}")

        except Exception as e:
            print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
            results.append({"name": test["name"], "status": "ERROR", "error": str(e)})

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")

    for result in results:
        status_icon = {
            "PASS": f"{Fore.GREEN}✅",
            "PARTIAL": f"{Fore.YELLOW}⚠️ ",
            "FAIL": f"{Fore.RED}❌",
            "ERROR": f"{Fore.RED}❌",
        }.get(result["status"], "❓")

        print(f"{status_icon} {result['name']}{Style.RESET_ALL}")
        if "error" in result:
            print(f"   Error: {result['error']}")

    passed = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)
    print(f"\n{Fore.GREEN}Passed: {passed}/{total}{Style.RESET_ALL}")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Interactive agent chat tester (local or remote)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Remote agent (prompts for credentials)
  uv run scripts/test-agent.py

  # Local agent on localhost:8080 (uses pattern from config.yaml)
  uv run scripts/test-agent.py --local

  # Run automated terminology test suite (remote)
  uv run scripts/test-agent.py --test-suite

  # Run test suite locally
  uv run scripts/test-agent.py --local --test-suite

  # Override pattern for local testing
  uv run scripts/test-agent.py --local --pattern strands-single-agent

Notes:
  - Remote mode: Tests deployed agent
  - Local mode: Pattern read from infra-cdk/config.yaml to start correct agent
  - Test suite: Runs automated medical terminology tests
  - Use --pattern to override the config value for local testing
  - Default: interactive conversation mode
        """,
    )

    parser.add_argument(
        "--local",
        action="store_true",
        help="Test local agent on localhost:8080 (default: remote)",
    )

    parser.add_argument(
        "--pattern",
        type=str,
        help="Override agent pattern from config (e.g., 'strands-single-agent', 'langgraph-single-agent')",
    )

    parser.add_argument(
        "--test-suite",
        action="store_true",
        help="Run automated terminology agent test suite instead of interactive mode",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    print("=" * 60)
    print("AgentCore Interactive Chat Tester")
    print("=" * 60 + "\n")

    args = parse_arguments()
    config: Dict[str, str] = {}

    # Get stack configuration
    stack_cfg = get_stack_config()

    # LOCAL MODE
    if args.local:
        # Determine pattern: CLI arg > config.yaml > default (only needed for local mode)
        pattern = (
            args.pattern
            if args.pattern
            else stack_cfg.get("pattern", "strands-single-agent")
        )
        print(f"Using pattern: {pattern}\n")
        print_section("LOCAL MODE - Auto-starting agent")

        # Get memory configuration
        memory_arn = stack_cfg["outputs"]["MemoryArn"]
        memory_id = memory_arn.split("/")[-1]
        region = stack_cfg["region"]
        stack_name = stack_cfg["stack_name"]

        # Check if agent is already running
        if check_port_available(8080):
            print_msg("Agent already running on localhost:8080", "info")
            print("Using existing agent instance...\n")
        else:
            # Start the agent
            start_local_agent(memory_id, region, stack_name, pattern)

    # REMOTE MODE
    else:
        print_section("REMOTE MODE - Testing deployed agent")

        stack_cfg = get_stack_config()
        print(f"Stack: {stack_cfg['stack_name']}\n")

        # Get configuration from CloudFormation outputs
        print("Fetching configuration from stack outputs...")
        outputs = stack_cfg["outputs"]

        # Validate required outputs exist
        required_outputs = ["CognitoUserPoolId", "CognitoClientId", "RuntimeArn"]
        missing = [key for key in required_outputs if key not in outputs]
        if missing:
            print_msg(f"Missing required stack outputs: {', '.join(missing)}", "error")
            sys.exit(1)

        print_msg("Configuration fetched")

        runtime_arn = outputs["RuntimeArn"]
        region = stack_cfg["region"]

        # Get credentials
        print_section("Authentication")

        username = input("Enter username: ").strip()
        if not username:
            print_msg("Username is required", "error")
            sys.exit(1)
        password = getpass.getpass(f"Enter password for {username}: ")

        # Authenticate
        access_token, id_token, user_id = authenticate_cognito(
            outputs["CognitoUserPoolId"], outputs["CognitoClientId"], username, password
        )

        # Use access token for AgentCore runtime (JWT authorizer)
        config["access_token"] = access_token
        config["runtime_arn"] = runtime_arn
        config["region"] = region
        print(f"\nRuntime ARN: {runtime_arn}")
        print(f"Region: {region}\n")

    # Run test suite or interactive chat
    if args.test_suite:
        session_id = generate_session_id()

        if args.local:
            # Local test suite
            run_terminology_test_suite(
                url="http://localhost:8080/invocations",
                session_id=session_id,
                headers=None,  # Will generate mock JWT
            )
        else:
            # Remote test suite
            endpoint = f"https://bedrock-agentcore.{config['region']}.amazonaws.com"
            escaped_arn = requests.utils.quote(config["runtime_arn"], safe="")
            url = f"{endpoint}/runtimes/{escaped_arn}/invocations?qualifier=DEFAULT"

            headers = {
                "Authorization": f"Bearer {config['access_token']}",
                "X-Amzn-Trace-Id": generate_trace_id(),
                "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
            }

            run_terminology_test_suite(
                url=url,
                session_id=session_id,
                headers=headers,
            )
    else:
        # Interactive chat mode
        run_chat(args.local, config)


if __name__ == "__main__":
    main()
