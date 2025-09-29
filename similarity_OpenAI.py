
from sentence_transformers import util
from openai import OpenAI

import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

def compute_similarity_open(prompt, elements):

    prompt_vec = client.embeddings.create(input=prompt, model="text-embedding-3-small").data[0].embedding
    element_vecs = []
    for element, _ in elements:
        vec = client.embeddings.create(
            input=element['label'],
            model='text-embedding-3-small'
        ).data[0].embedding

        element_vecs.append(vec)

    # element_vecs = [client.embeddings.create(input=el[0]["label"], model="text-embedding-3-small").data[0].embedding for el in elements]
    
    similarities = [util.cos_sim(prompt_vec, vec).item() for vec in element_vecs]

    return similarities
