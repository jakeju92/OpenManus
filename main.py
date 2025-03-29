import argparse
import asyncio

from app.agent.factory import AGENT_REGISTRY, create_agent
from app.logger import logger


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run OpenManus AI assistant")
    parser.add_argument(
        "--agent",
        type=str,
        default="swe",
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

    args = parser.parse_args()

    # Create the selected agent type with provided parameters
    agent_kwargs = {"max_steps": args.max_steps}

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
        await agent.run(prompt)
        logger.info("Request processing completed.")

        # Display summary info for task_completion agent
        if args.agent == "task_completion":
            logger.info(f"Agent ran for {agent.current_step} steps out of maximum {args.max_steps}")
            if agent.state == "FINISHED":
                logger.info("Task was determined to be complete")
            else:
                logger.info("Task was not determined to be complete")

    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")


if __name__ == "__main__":
    asyncio.run(main())
