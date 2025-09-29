
import os
from openai import OpenAI

import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")


client = OpenAI(api_key=api_key)

response = client.embeddings.create(
    input="buy the latest airpods pro",
    model="text-embedding-3-small"
)

print(response.data[0].embedding)
