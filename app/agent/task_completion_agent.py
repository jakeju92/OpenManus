import os
from typing import List, Optional

from pydantic import Field

from app.agent.swe import SWEAgent
from app.logger import logger
from app.prompt.task_completion import (COMPLETION_CHECK_PROMPT,
                                        COMPLETION_SYSTEM_PROMPT)
from app.schema import AgentState, Message


class TaskCompletionAgent(SWEAgent):
    """
    An agent that dynamically determines when a task is complete, rather than
    running a fixed number of steps.

    This agent extends SWEAgent with a task completion checking mechanism that evaluates
    whether the objectives have been achieved based on the conversation history.
    """

    name: str = "TaskCompletionAgent"
    description: str = "An agent that dynamically determines when tasks are complete"

    # Completion checking configuration
    completion_check_interval: int = Field(default=1, description="Check completion every N steps")
    completion_system_prompt: str = Field(default=COMPLETION_SYSTEM_PROMPT, description="System prompt for completion checking")
    completion_check_prompt: str = Field(default=COMPLETION_CHECK_PROMPT, description="Prompt template for completion checking")
    completion_confidence_threshold: float = Field(default=0.7, description="Confidence threshold (0-1) to consider a task complete")

    async def run(self, request: Optional[str] = None) -> str:
        """
        Execute the agent's main loop with dynamic completion checking.

        Args:
            request: Optional initial user request to process.

        Returns:
            A string summarizing the execution results.
        """
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        if request:
            self.update_memory("user", request)

        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            while (
                self.current_step < self.max_steps and
                self.state != AgentState.FINISHED
            ):
                self.current_step += 1
                logger.info(f"Executing step {self.current_step}/{self.max_steps}")
                step_result = await self.step()

                # Check for stuck state
                if self.is_stuck():
                    self.handle_stuck_state()

                results.append(f"Step {self.current_step}: {step_result}")

                # Check for task completion at specified intervals
                if self.current_step % self.completion_check_interval == 0:
                    is_complete, confidence = await self.check_task_completion()
                    logger.info(f"Task completion check: {is_complete} (confidence: {confidence:.2f})")

                    if is_complete:
                        logger.info(f"Task determined to be complete with confidence {confidence:.2f}")
                        self.state = AgentState.FINISHED
                        results.append(f"Task completed with confidence {confidence:.2f}")
                        break

            if self.current_step >= self.max_steps:
                self.current_step = 0
                self.state = AgentState.IDLE
                results.append(f"Terminated: Reached max steps ({self.max_steps})")

        return "\n".join(results) if results else "No steps executed"

    async def check_task_completion(self) -> tuple[bool, float]:
        """
        Check if the current task is complete based on conversation history.

        Returns:
            Tuple of (is_complete, confidence) where:
                - is_complete: Boolean indicating whether the task is complete
                - confidence: Float between 0 and 1 indicating confidence in completion
        """
        # Find the original user request
        user_requests = [msg for msg in self.memory.messages if msg.role == "user"]
        if not user_requests:
            return False, 0.0

        original_request = user_requests[0].content
        if not original_request:
            return False, 0.0

        # Check if this is a git clone operation
        is_git_clone = "clone" in original_request.lower() and "git" in original_request.lower()

        # For git clone operations, check if target directory exists and contains code
        if is_git_clone:
            # Extract target directory from the request or use default
            repo_name = None

            # Try to extract repo name from the request
            if "github.com" in original_request or "gitlab.com" in original_request:
                # Find the URL pattern
                import re
                url_pattern = r'https?://[^\s]+\.git|git@[^\s]+\.git|https?://[^\s]+'
                urls = re.findall(url_pattern, original_request)

                if urls:
                    url = urls[0]
                    # Extract repo name from URL
                    if "/" in url:
                        repo_name = url.split("/")[-1]
                        if repo_name.endswith(".git"):
                            repo_name = repo_name[:-4]

            # If we couldn't extract repo name, use a generic name
            if not repo_name:
                repo_name = "repository"

            # Check for repo in workspace directory
            workspace_path = self.workspace_path
            repo_path = os.path.join(workspace_path, repo_name)

            logger.info(f"Checking for repository at {repo_path}")

            if os.path.exists(repo_path):
                # Check if directory contains git files and code
                has_git = os.path.exists(os.path.join(repo_path, ".git"))

                if has_git:
                    logger.info(f"Found git repository at {repo_path}")
                    # Check if directory contains code files
                    code_extensions = ('.py', '.js', '.java', '.cpp', '.c', '.h', '.html', '.css', '.ts', '.jsx', '.tsx')
                    has_code = False

                    for root, _, files in os.walk(repo_path):
                        if any(f.endswith(code_extensions) for f in files):
                            has_code = True
                            break

                    if has_code:
                        logger.info(f"Repository contains code files")
                        return True, 0.9  # High confidence for existing valid repository

                    logger.info(f"Repository exists but no code files were found")

        # Prepare completion check prompt
        completion_prompt = self.completion_check_prompt.format(
            original_request=original_request,
            conversation_history="\n".join([f"{m.role}: {m.content}" for m in self.memory.messages if m.content])
        )

        # Ask the LLM if the task is complete
        messages = [
            Message.system_message(self.completion_system_prompt),
            Message.user_message(completion_prompt)
        ]

        response = await self.llm.ask(messages=messages)

        # Handle both string and object responses
        content = response.content if hasattr(response, 'content') else response
        if not isinstance(content, str):
            return False, 0.0

        # Look for YES/NO and confidence in the response
        content = content.strip().upper()

        if "YES" in content and "CONFIDENCE:" in content:
            try:
                # Extract confidence value
                confidence_part = content.split("CONFIDENCE:")[1].strip()
                confidence_str = "".join(c for c in confidence_part if c.isdigit() or c == '.')
                confidence = float(confidence_str) if confidence_str else 0.0

                # Normalize to 0-1 range if necessary
                if confidence > 1.0:
                    confidence = confidence / 100.0

                return confidence >= self.completion_confidence_threshold, confidence
            except (ValueError, IndexError):
                return False, 0.0

        return False, 0.0
