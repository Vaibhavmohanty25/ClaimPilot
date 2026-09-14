from services.llm import generate_text


response = generate_text(
    """
    You are an insurance claims assistant.

    A Hyundai Creta was hit on the front-left side
    while travelling through an intersection.

    Summarize the incident in one sentence.
    """
)

print(response)