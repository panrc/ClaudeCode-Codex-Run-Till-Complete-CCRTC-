#!/usr/bin/env python3
"""
Auto-test script that monitors code execution and auto-fixes errors
by communicating with CodeX or Claude Code processes.
"""

import argparse
import subprocess
import psutil
import time
import os
import sys
import signal
import threading
from typing import List, Optional, Tuple
import re


class ProcessMonitor:
    def __init__(self, command: str, timeout: int):
        self.command = command
        self.timeout = timeout
        self.target_process = None
        self.target_pid = None
        self.target_cwd = None
        self.ai_command = None  # Will be 'claude' or 'codex'

    def find_code_processes(self) -> List[Tuple[int, str, str]]:
        """Find Claude Code or CodeX processes only"""
        processes = []

        # Only look for Claude and CodeX related processes
        target_keywords = [
            'claude',      # Claude, Claude Code
            'codex',       # CodeX
        ]

        # Additional specific process names that might contain Claude/CodeX
        specific_names = [
            'claude code',
            'claude-code',
            'claudecode',
            'codex',
            'openai-codex'
        ]

        print("Searching for Claude Code and CodeX processes...")

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = proc.info['name'].lower()
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                cmdline_lower = cmdline.lower()

                # Check if this is a Claude or CodeX process
                is_target_process = False
                process_type = ""

                # Check process name and command line for keywords
                for keyword in target_keywords:
                    if keyword in name or keyword in cmdline_lower:
                        is_target_process = True
                        if 'claude' in keyword:
                            process_type = "Claude"
                        elif 'codex' in keyword:
                            process_type = "CodeX"
                        break

                # Check for specific process names
                if not is_target_process:
                    for specific_name in specific_names:
                        if specific_name in name or specific_name in cmdline_lower:
                            is_target_process = True
                            if 'claude' in specific_name:
                                process_type = "Claude"
                            elif 'codex' in specific_name:
                                process_type = "CodeX"
                            break

                if is_target_process:
                    # Get additional process info
                    try:
                        # Check if process has a terminal
                        tty_cmd = f"ps -p {proc.info['pid']} -o tty --no-headers"
                        tty_result = subprocess.run(tty_cmd, shell=True, capture_output=True, text=True)
                        has_tty = tty_result.returncode == 0 and tty_result.stdout.strip() not in ["?", "??", ""]

                        # Create descriptive display name
                        display_name = f"🤖 {process_type}: {proc.info['name']}"
                        if has_tty:
                            display_name += " (TTY)"

                        # Check if process is active (has CPU activity)
                        cpu_percent = proc.cpu_percent(interval=0.1)
                        if cpu_percent > 0:
                            display_name += " (Active)"

                        processes.append((proc.info['pid'], display_name, cmdline))
                        print(f"Found: PID {proc.info['pid']} - {display_name}")

                    except Exception as e:
                        # Still add the process even if we can't get extra info
                        display_name = f"🤖 {process_type}: {proc.info['name']}"
                        processes.append((proc.info['pid'], display_name, cmdline))
                        print(f"Found: PID {proc.info['pid']} - {display_name}")

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not processes:
            print("❌ No Claude Code or CodeX processes found!")
            print("Make sure Claude Code or CodeX is running before using this script.")
        else:
            print(f"✅ Found {len(processes)} Claude/CodeX process(es)")

        # Sort by process name for consistent ordering
        processes.sort(key=lambda x: x[1])
        return processes

    def display_processes(self, processes: List[Tuple[int, str, str]]) -> int:
        """Display available Claude/CodeX processes and let user choose"""
        if not processes:
            print("\n❌ No Claude Code or CodeX processes found!")
            print("Please make sure one of the following is running:")
            print("   - Claude Code (CLI or desktop app)")
            print("   - CodeX")
            print("   - Any application with 'claude' or 'codex' in its name")
            sys.exit(1)

        print(f"\n🤖 Found Claude/CodeX processes:")
        print("=" * 80)
        for i, (pid, name, cmdline) in enumerate(processes):
            print(f"{i+1}. PID: {pid}")
            print(f"   📱 {name}")
            if cmdline:
                # Truncate very long command lines
                cmd_display = cmdline[:100] + "..." if len(cmdline) > 100 else cmdline
                print(f"   💻 Command: {cmd_display}")
            print("-" * 80)

        while True:
            try:
                choice = int(input(f"\n🎯 Select target process (1-{len(processes)}): ")) - 1
                if 0 <= choice < len(processes):
                    selected_pid = processes[choice][0]
                    selected_name = processes[choice][1]
                    print(f"✅ Selected: {selected_name} (PID: {selected_pid})")
                    return selected_pid
                else:
                    print(f"❌ Invalid choice. Please enter a number between 1 and {len(processes)}.")
            except ValueError:
                print("❌ Please enter a valid number.")

    def bind_to_process(self, pid: int) -> bool:
        """Bind to the selected process and get its working directory"""
        try:
            self.target_process = psutil.Process(pid)
            self.target_pid = pid

            # Get the working directory of the target process
            try:
                self.target_cwd = self.target_process.cwd()
                print(f"✅ Successfully bound to process {pid}")
                print(f"📁 Working directory: {self.target_cwd}")
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                # If we can't get the cwd, use current directory as fallback
                self.target_cwd = os.getcwd()
                print(f"✅ Bound to process {pid} (using current directory as fallback)")
                print(f"📁 Working directory: {self.target_cwd}")

            # Determine which AI command to use based on process
            self._detect_ai_command()

            return True
        except psutil.NoSuchProcess:
            print(f"❌ Process {pid} not found!")
            return False

    def _detect_ai_command(self) -> None:
        """Detect whether to use 'claude' or 'codex' command"""
        try:
            name = self.target_process.name().lower()
            cmdline = ' '.join(self.target_process.cmdline()).lower()

            if 'claude' in name or 'claude' in cmdline:
                self.ai_command = 'claude'
                print(f"🤖 Will use 'claude' command for AI assistance")
            elif 'codex' in name or 'codex' in cmdline:
                self.ai_command = 'codex'
                print(f"🤖 Will use 'codex' command for AI assistance")
            else:
                # Default to claude
                self.ai_command = 'claude'
                print(f"🤖 Defaulting to 'claude' command for AI assistance")

        except Exception as e:
            self.ai_command = 'claude'
            print(f"🤖 Defaulting to 'claude' command (detection failed: {e})")

    def execute_command(self) -> Tuple[bool, str]:
        """Execute the command and capture output/errors"""
        try:
            result = subprocess.run(
                self.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.target_cwd or os.getcwd()
            )

            if result.returncode != 0:
                return False, result.stderr or result.stdout
            else:
                return True, result.stdout

        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {self.timeout} seconds"
        except Exception as e:
            return False, str(e)

    def ask_ai_for_fix(self, error_message: str) -> bool:
        """Ask Claude or CodeX to fix the error by executing the AI command"""
        try:
            if not self.ai_command or not self.target_cwd:
                print("❌ AI command or working directory not available")
                return False

            # Create a prompt for the AI
            prompt = f"""The following command failed with an error:

Command: {self.command}
Error: {error_message}

Please analyze this error and fix the issue. Focus on:
1. Understanding what went wrong
2. Making the necessary code changes to fix the error
3. Ensuring the command will run successfully

Please fix the code and don't just explain the problem."""

            print(f"🤖 Asking {self.ai_command.upper()} to fix the error...")
            print(f"📁 Executing in: {self.target_cwd}")

            # Execute the AI command in the target directory with appropriate flags
            if self.ai_command == 'claude':
                ai_cmd = f'{self.ai_command} "{prompt}" --dangerously-skip-permissions'
            elif self.ai_command == 'codex':
                ai_cmd = f'{self.ai_command} "{prompt}" --dangerously-bypass-approvals-and-sandbox'
            else:
                ai_cmd = f'{self.ai_command} "{prompt}"'

            # Show what we're about to execute (truncated for readability)
            prompt_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
            print(f"💬 Prompt: {prompt_preview}")

            result = subprocess.run(
                ai_cmd,
                shell=True,
                cwd=self.target_cwd,
                timeout=120,  # Give AI 2 minutes to respond
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("✅ AI command executed successfully")
                if result.stdout:
                    # Show a preview of AI response
                    response_preview = result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout
                    print(f"🤖 AI Response: {response_preview}")
                return True
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                print(f"❌ AI command failed: {error_msg}")
                return False

        except subprocess.TimeoutExpired:
            print(f"⏰ AI command timed out (120 seconds)")
            return False
        except Exception as e:
            print(f"❌ Failed to execute AI command: {e}")
            return False

    def wait_for_ai_completion(self, wait_seconds: int = 30) -> bool:
        """Wait for AI to potentially make changes"""
        print(f"⏳ Waiting {wait_seconds} seconds for AI to make changes...")
        time.sleep(wait_seconds)

        # Check if the target process is still active
        if self.target_process and self.target_process.is_running():
            try:
                # Check if there's been any recent activity
                cpu_percent = self.target_process.cpu_percent(interval=1.0)
                if cpu_percent > 0:
                    print(f"✅ AI process shows activity (CPU: {cpu_percent:.1f}%)")
                    return True
                else:
                    print(f"⚠️ AI process appears idle (CPU: {cpu_percent:.1f}%)")
                    return False
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                print("⚠️ Cannot monitor AI process activity")
                return False
        else:
            print("⚠️ AI process is no longer running")
            return False


    def run(self):
        """Main monitoring loop using AI commands for error fixing"""
        print(f"🚀 Starting auto-test with command: {self.command}")
        print(f"⏰ Timeout: {self.timeout} seconds (will run continuously after this)")

        # Find and select AI process
        processes = self.find_code_processes()
        selected_pid = self.display_processes(processes)

        if not self.bind_to_process(selected_pid):
            sys.exit(1)

        start_time = time.time()
        consecutive_successes = 0
        retry_count = 0
        max_retries = 15  # Increased because AI fixing might take more attempts
        stable_period_start = None

        print(f"\n🎯 Will monitor for {self.timeout} seconds before considering program stable")
        print(f"🤖 Using '{self.ai_command}' command for error fixing")

        while True:
            current_time = time.time()
            elapsed = current_time - start_time

            print(f"\n[{elapsed:.1f}s] 🔄 Attempt #{retry_count + 1} - Executing: {self.command}")

            success, output = self.execute_command()

            if success:
                consecutive_successes += 1
                retry_count = 0  # Reset retry count on success

                if stable_period_start is None:
                    stable_period_start = current_time
                    print(f"✅ Command executed successfully! Starting stability monitoring...")

                stable_duration = current_time - stable_period_start
                print(f"✅ Success #{consecutive_successes} (stable for {stable_duration:.1f}s)")

                if len(output.strip()) > 0:
                    output_preview = output[:200] + "..." if len(output) > 200 else output
                    print(f"📝 Output: {output_preview}")

                # If program has been stable for the timeout period, let it run continuously
                if stable_duration >= self.timeout:
                    print(f"\n🎉 Program has been running successfully for {self.timeout} seconds!")
                    print("🚀 Program appears stable. Switching to continuous execution mode...")

                    try:
                        print(f"▶️ Executing final continuous run: {self.command}")
                        result = subprocess.run(self.command, shell=True, cwd=self.target_cwd)
                        print(f"\n✅ Program completed with exit code: {result.returncode}")
                        break
                    except KeyboardInterrupt:
                        print("\n⚠️ Monitoring stopped by user.")
                        break

            else:
                # Reset stability tracking on failure
                consecutive_successes = 0
                stable_period_start = None
                retry_count += 1

                print(f"❌ Command failed (attempt {retry_count}/{max_retries}):")
                print(f"🚫 Error: {output}")

                if retry_count >= max_retries:
                    print(f"\n💥 Max retries ({max_retries}) reached. Giving up.")
                    print("🤔 The AI may need more context or manual intervention.")
                    break

                # Ask AI to fix the error
                if self.ask_ai_for_fix(output):
                    print("✅ AI command executed successfully")

                    # Wait for AI to make changes
                    self.wait_for_ai_completion(20)  # Wait 20 seconds for AI to work

                    print("🔄 Retrying command after AI assistance...")
                else:
                    print("❌ AI command failed, retrying anyway...")

                # Shorter wait since AI should have already worked
                wait_time = min(retry_count * 2, 10)  # Progressive wait, cap at 10 seconds
                if wait_time > 0:
                    print(f"⏸️ Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)

            # Check if we've exceeded total time limit (more generous for AI fixing)
            total_limit = self.timeout * 3  # Triple the timeout for the entire process
            if elapsed > total_limit:
                print(f"\n⏰ Total time limit exceeded ({total_limit} seconds)")
                print("🤔 Consider increasing timeout or checking the complexity of the problem.")
                break

        print("\n🏁 Auto-test monitoring completed.")


def main():
    parser = argparse.ArgumentParser(
        description="Auto-test script that monitors code execution and communicates with CodeX/Claude Code"
    )
    parser.add_argument("command", help="Command to execute")
    parser.add_argument("timeout", type=int, help="Timeout in seconds for normal execution")

    args = parser.parse_args()

    monitor = ProcessMonitor(args.command, args.timeout)

    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\nShutdown requested by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()