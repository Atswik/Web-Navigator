
from sentence_transformers import SentenceTransformer, util

def compute_similarity(prompt, elements):
    model = SentenceTransformer("all-MiniLM-L6-v2")

    prompt_vec = model.encode(prompt, convert_to_tensor=True)
    element_vecs = [model.encode(el["label"], convert_to_tensor=True) for el in elements]
    
    similarities = [util.cos_sim(prompt_vec, vec).item() for vec in element_vecs]

    return similarities
