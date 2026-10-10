"""Entry point notice.

This project's agent is a Streamlit app, not a CLI — it needs a chat UI for
the conversation loop. `uv init` generated a placeholder main.py here that
printed "Hello from single-ai-agent-system!", which was misleading.

    uv run streamlit run project/app.py
"""
import sys

MSG = """\
This project runs as a Streamlit app, not from the terminal.

    uv run streamlit run project/app.py

Needs GROQ_API_KEY, TAVILY_API_KEY and WEATHERSTACK_API_KEY in .env
(copy ../../.env.example and fill in those three).

For the CLI-style sibling project, see ../Multi-Agent AI System:
    uv run main.py
"""


def main() -> int:
    print(MSG)
    return 0


if __name__ == "__main__":
    sys.exit(main())
