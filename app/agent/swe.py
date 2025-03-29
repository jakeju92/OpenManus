from typing import List, Optional

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.logger import logger
from app.prompt.swe import NEXT_STEP_TEMPLATE, SYSTEM_PROMPT
from app.tool import Bash, GitTool, StrReplaceEditor, Terminate, ToolCollection


class SWEAgent(ToolCallAgent):
    """An agent that implements the SWEAgent paradigm for executing code and natural conversations."""

    name: str = "swe"
    description: str = "an autonomous AI programmer that interacts directly with the computer to solve tasks."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_TEMPLATE

    available_tools: ToolCollection = ToolCollection(
        Bash(), GitTool(), StrReplaceEditor(), Terminate()
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    max_steps: int = 30

    bash: Bash = Field(default_factory=Bash)
    working_dir: str = "."
    open_file: Optional[str] = None

    async def think(self) -> bool:
        """Process current state and decide next action"""
        # # Change to the workspace directory for all operations
        # workspace_dir = str(self.workspace_path)

        # # Check if the working directory is already in the workspace
        # if not self.working_dir.startswith(workspace_dir):
        #     # Use workspace directory for initial operations
        #     change_dir_result = await self.bash.execute(f"cd {workspace_dir}")
        #     if change_dir_result.success:
        #         result = await self.bash.execute("pwd")
        #         self.working_dir = result.output
        #         logger.info(f"Changed working directory to workspace: {self.working_dir}")
        #     else:
        #         logger.error(f"Failed to change to workspace directory: {workspace_dir}")
        # else:
        #     # Get current directory
        #     result = await self.bash.execute("pwd")
        #     self.working_dir = result.output
        result = await self.bash.execute("pwd")
        self.working_dir = result.output

        # Update prompt with current state
        self.next_step_prompt = self.next_step_prompt.format(
            observation="",
            open_file=self.open_file or "",
            working_dir=self.working_dir
        )

        return await super().think()
