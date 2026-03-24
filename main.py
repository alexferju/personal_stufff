import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()


def chat(user_message: str) -> str:
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text


if __name__ == "__main__":
    print("AI App ready. Type 'quit' to exit.\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        if not user_input:
            continue
        response = chat(user_input)
        print(f"Claude: {response}\n")
