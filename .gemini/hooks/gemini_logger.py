#!/usr/bin/env python3
import sys
import json
import os
import subprocess
from datetime import datetime

# Configuration
LOG_FILE = "gemini.log"

def run_gemini_prompt(prompt, input_text=None):
    """Runs gemini --prompt with the given prompt and optional input text."""
    try:
        process = subprocess.Popen(
            ["gemini", "--prompt", prompt],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=input_text)
        if process.returncode != 0:
            return None
        return stdout.strip()
    except Exception as e:
        return None

def update_journal_and_changelog(data):
    """Updates journal and changelog based on the transcript."""
    try:
        transcript_path = data.get("transcript_path")
        if not transcript_path or not os.path.exists(transcript_path):
            return

        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_data = json.load(f)

        if not transcript_data:
            return

        # Handle transcript provided as a dictionary (standard CLI behavior)
        if isinstance(transcript_data, dict):
            for key in ["messages", "transcript", "history"]:
                if key in transcript_data and isinstance(transcript_data[key], list):
                    transcript_data = transcript_data[key]
                    break
            else:
                if not isinstance(transcript_data, list):
                    return

        # Check for tool calls in the last 15 messages (be generous)
        last_few = transcript_data[-15:]
        has_tool_call = False
        for msg in last_few:
            if msg.get("type") == "gemini" and msg.get("toolCalls"):
                has_tool_call = True
                break

        if not has_tool_call:
            return

        transcript_text = json.dumps(transcript_data)
        today = datetime.now().strftime("%Y-%m-%d")
        journal_path = f"journal/{today}.md"

        # 1. Update Journal
        journal_prompt = (
            "Based on the following conversation transcript, provide a very short (one sentence, max 2) "
            "description of the actions performed in the VERY LAST turn. "
            "Output ONLY the description, starting with a dash (-)."
        )
        summary = run_gemini_prompt(journal_prompt, transcript_text)
        if summary:
            os.makedirs("journal", exist_ok=True)
            file_exists = os.path.exists(journal_path)
            with open(journal_path, "a", encoding="utf-8") as f:
                if not file_exists:
                    f.write(f"## {today}\n\n## Status\n")
                f.write(f"{summary}\n")

        # 2. Update Changelog
        changelog_path = "CHANGELOG.md"
        if os.path.exists(changelog_path):
            with open(changelog_path, "r", encoding="utf-8") as f:
                current_changelog = f.read()
            changelog_prompt = (
                "Based on the following conversation transcript and the current CHANGELOG.md, "
                "determine if an update to CHANGELOG.md is necessary due to the changes in the LAST turn. "
                "If it is, provide the updated CHANGELOG.md content. "
                "Focus on the 'Unreleased' or the latest version section. "
                "If no update is needed, output 'NO_UPDATE'.\n\n"
                f"CURRENT CHANGELOG:\n{current_changelog}\n\n"
                "Output ONLY the new CHANGELOG.md content or 'NO_UPDATE'."
            )
            new_changelog = run_gemini_prompt(changelog_prompt, transcript_text)
            if new_changelog and new_changelog != "NO_UPDATE":
                with open(changelog_path, "w", encoding="utf-8") as f:
                    f.write(new_changelog)
    except Exception as e:
        pass

def main():
    try:
        input_data = sys.stdin.read()
        if not input_data:
            data = {}
        else:
            data = json.loads(input_data)

        event = data.get("hook_event_name")

        if event == "SessionStart":
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write(f"--- Session Started ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---\n\n")

        elif event == "AfterModel":
            llm_response = data.get("llm_response", {})
            candidates = llm_response.get("candidates", [])
            if candidates:
                candidate = candidates[0]
                content_obj = candidate.get("content", {})
                parts = content_obj.get("parts", [])
                finish_reason = candidate.get("finishReason")

                if parts or finish_reason:
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        for part in parts:
                            if isinstance(part, str):
                                f.write(part)
                            elif isinstance(part, dict) and "text" in part:
                                f.write(part["text"])
                        if finish_reason:
                            f.write("\n\n")

        elif event == "AfterAgent":
            update_journal_and_changelog(data)

        print(json.dumps({}))

    except Exception as e:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
