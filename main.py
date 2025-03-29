import argparse
import asyncio
import os
from pathlib import Path

from app.agent.factory import AGENT_REGISTRY, create_agent
from app.config import WORKSPACE_ROOT
from app.logger import define_log_level
from app.workspace_manager import workspace_manager


def setup_logging(log_level: str, agent_type: str):
    """Initialize logging with the appropriate configuration"""
    return define_log_level(
        print_level=log_level,
        logfile_level="DEBUG",
        name=agent_type
    )


async def main():
    # Parse arguments first to determine the agent type for logging
    parser = argparse.ArgumentParser(description="Run OpenManus AI assistant")
    parser.add_argument(
        "--agent",
        type=str,
        default="task_completion",
        choices=list(AGENT_REGISTRY.keys()),
        help="Type of agent to use"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Maximum number of steps before termination (default: 20)"
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=1,
        help="Interval for task completion checks (for task_completion agent)"
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.7,
        help="Confidence threshold for task completion (for task_completion agent)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level (default: INFO)"
    )

    args = parser.parse_args()

    # Ensure workspace directory exists
    os.makedirs(WORKSPACE_ROOT, exist_ok=True)

    # Create a timestamped workspace
    current_workspace = workspace_manager.current_workspace

    # Initialize logger with agent name
    logger = setup_logging(args.log_level, args.agent)
    logger.info(f"Created workspace directory: {current_workspace}")

    # Create the selected agent type with provided parameters
    agent_kwargs = {
        "max_steps": args.max_steps,
        "workspace_manager": workspace_manager,  # Pass workspace manager to agent
    }

    # Add task completion specific parameters if applicable
    if args.agent == "task_completion":
        agent_kwargs.update({
            "completion_check_interval": args.check_interval,
            "completion_confidence_threshold": args.confidence
        })

    agent = create_agent(agent_type=args.agent, **agent_kwargs)

    try:
        prompt = input("Enter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        logger.warning(f"Processing your request using {args.agent} agent...")
        logger.info(f"Workspace path: {current_workspace}")
        await agent.run(prompt)
        logger.info("Request processing completed.")

        # Display summary info for task_completion agent
        if args.agent == "task_completion":
            logger.info(f"Agent ran for {agent.current_step} steps out of maximum {args.max_steps}")
            if agent.state == "FINISHED":
                logger.info("Task was determined to be complete")
            else:
                logger.info("Task was not determined to be complete")

        print(f"\nWorkspace directory: {current_workspace}")

    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")


if __name__ == "__main__":
    asyncio.run(main())
