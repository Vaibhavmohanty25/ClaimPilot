import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)


if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is missing from your .env file."
    )


client = Groq(
    api_key=GROQ_API_KEY
)


def generate_text(prompt: str) -> str:
    """
    Send a prompt to Groq and return the generated text.
    """

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