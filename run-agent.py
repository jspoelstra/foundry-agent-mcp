"""Run interaction loop with an existing Azure AI Agent created via create-agent.py.

Usage:
    python run-agent.py --name my-mcp-agent

Type a message and press Enter. Type ":quit" or Ctrl-D to exit.

Relies on .agents.json mapping file created by create-agent.py.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import (
    ListSortOrder,
    RunStepActivityDetails,
    SubmitToolApprovalAction,
    RequiredMcpToolCall,
    ToolApproval,
    RunStatus
)

AGENT_STORE_FILE = Path(".agents.json")


def load_store() -> Dict[str, str]:
    if not AGENT_STORE_FILE.exists():
        raise SystemExit(f"Agent store {AGENT_STORE_FILE} not found. Run create-agent.py first.")
    try:
        return json.loads(AGENT_STORE_FILE.read_text())
    except Exception as e:
        raise SystemExit(f"Failed to read {AGENT_STORE_FILE}: {e}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run interactive loop with existing agent")
    parser.add_argument("--name", required=True, help="Agent name (key in .agents.json)")
    return parser.parse_args()


def main() -> None:
    # Load environment variables from .env if python-dotenv is available
    load_dotenv(override=False)

    args = parse_args()
    store = load_store()

    if args.name not in store:
        raise SystemExit(f"Agent name '{args.name}' not found in {AGENT_STORE_FILE}. Create it first.")

    agent_id = store[args.name]
    # Need to get this also from the store:
    # tool_resources = {'mcp': [{'server_label': 'restapirepo', 'headers': {}, 'require_approval': 'never'}]}

    endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not endpoint:
        raise SystemExit("PROJECT_ENDPOINT env var is required")

    project_client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())

    with project_client:
        agents_client = project_client.agents

        # Validate agent exists (raises if not)
        try:
            agent = agents_client.get_agent(agent_id)
        except Exception as e:  # broad: underlying SDK-specific error types
            raise SystemExit(f"Failed to retrieve agent '{args.name}' (id={agent_id}): {e}")

        thread = agents_client.threads.create()
        print(f"Session thread ID: {thread.id}")
        print("Type messages. Use :quit to exit.\n")

        while True:
            try:
                user_input = input("> ").strip()
            except EOFError:
                print()  # newline after Ctrl-D
                break
            if not user_input:
                continue
            if user_input.lower() in {":quit", ":q", ":exit"}:
                break

            message = agents_client.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_input,
            )
            print(f"Created message: {message.id}")

            # Create run referencing existing agent (no tool resources needed here; tools already on agent)
            run = agents_client.runs.create(
                thread_id=thread.id,
                agent_id=agent_id,
            )
            print(f"Run: {run.id} (status: {run.status})")

            while run.status in [RunStatus.QUEUED, RunStatus.IN_PROGRESS, RunStatus.REQUIRES_ACTION]:
                time.sleep(1)
                run = agents_client.runs.get(thread_id=thread.id, run_id=run.id)

                # Minimal approval handling (if server still requests tool approvals)
                if run.status == RunStatus.REQUIRES_ACTION and isinstance(run.required_action, SubmitToolApprovalAction):
                    tool_calls = run.required_action.submit_tool_approval.tool_calls
                    approvals: list[ToolApproval] = []
                    for tool_call in tool_calls:
                        if isinstance(tool_call, RequiredMcpToolCall):
                            print(f"Approving MCP tool call: {tool_call})")
                            approvals.append(ToolApproval(tool_call_id=tool_call.id, approve=True))
                    if approvals:
                        agents_client.runs.submit_tool_outputs(
                            thread_id=thread.id,
                            run_id=run.id,
                            tool_approvals=approvals,
                        )
                print(f"  Status: {run.status}")

            if run.status == RunStatus.FAILED:
                print(f"Run failed: {run.last_error}")
                continue

            # Retrieve last assistant response
            messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
            last_assistant = None
            for msg in reversed(list(messages)):
                if msg.role == "assistant" and msg.text_messages:
                    last_assistant = msg.text_messages[-1].text.value
                    break
            if last_assistant:
                print("\nAssistant:\n" + last_assistant + "\n")

            # Optional: show tool activity summaries
            run_steps = agents_client.run_steps.list(thread_id=thread.id, run_id=run.id)
            for step in run_steps:
                step_details = step.get("step_details", {})
                if isinstance(step_details, RunStepActivityDetails):
                    for activity in step_details.activities:
                        for fn_name in activity.tools.keys():
                            print(f"  (Tool used: {fn_name})")

        print("Exiting. (Agent not deleted; reuse with another session.)")


if __name__ == "__main__":  # pragma: no cover
    main()
