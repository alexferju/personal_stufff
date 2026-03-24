"""
The Agent Factory — Remote Control Entry Point

Usage:
  python main.py submit "Build a REST API for a todo app with FastAPI and SQLite"
  python main.py status
  python main.py watch <project_id>
  python main.py logs  <project_id>
  python main.py steer <project_id> "Use PostgreSQL instead of SQLite"
  python main.py cleanup
  python main.py cleanup <project_id>
  python main.py help

Philosophy: Harness Engineering
  Agent = Model + Harness
  The harness constrains, informs, and verifies.
  Humans steer. Agents execute. No manually-written code.
"""
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

from agent_factory.remote_control.dashboard import RemoteControl


async def main():
    rc = RemoteControl()
    await rc.run(sys.argv[1:])


if __name__ == "__main__":
    asyncio.run(main())
