import os
import time

from dotenv import load_dotenv
from groq import Groq, RateLimitError


load_dotenv()


GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
)


if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is missing from your .env file."
    )


client = Groq(
    api_key=GROQ_API_KEY
)


def generate_text(
    prompt: str,
    max_retries: int = 3,
) -> str:

    for attempt in range(max_retries):

        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.2,
            )

            return response.choices[0].message.content

        except RateLimitError:

            if attempt == max_retries - 1:
                raise

            wait_time = 2 ** attempt

            print(
                f"Groq rate limit hit. Retrying in "
                f"{wait_time} seconds..."
            )

            time.sleep(wait_time)