import os

from dotenv import load_dotenv
from openai import OpenAI


DEFAULT_PROMPT = "Write a haiku about AI"


def create_client() -> OpenAI:
    load_dotenv()
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def summarize_prompt(prompt: str = DEFAULT_PROMPT, client: OpenAI | None = None) -> str:
    openai_client = client or create_client()
    completion = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    return completion.choices[0].message.content


def main() -> None:
    print(summarize_prompt())


if __name__ == "__main__":
    main()
