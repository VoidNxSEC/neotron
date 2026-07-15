from neutron.langmath.config import settings


def init_llm():
    if settings.llm_provider == "nvidia":
        from langchain_openai import ChatOpenAI

        if not settings.nvidia_api_key:
            raise ValueError("LANGMATH_NVIDIA_API_KEY environment variable is missing.")
        return ChatOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.nvidia_api_key,
            model=settings.nvidia_model,
        )

    elif settings.llm_provider == "llamacpp":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            base_url=settings.llama_cpp_base_url,
            api_key="sk-no-key-required",
            model=settings.llama_cpp_model,
        )
    else:
        raise ValueError(f"Unknown provider: {settings.llm_provider}")


def ask_oracle(query: str):
    from neutron.langmath.core.rag import collection

    # Retrieve top 5 semantic matches from chroma
    results = collection.query(query_texts=[query], n_results=5)

    # check if anything was returned
    if not results["documents"] or not len(results["documents"][0]):
        return {
            "answer": "I haven't learned anything about this yet in my local dataset.",
            "sources": [],
        }

    context_chunks = results["documents"][0]
    context = "\n\n---\n\n".join(context_chunks)

    prompt = f"""You are the LangMath Oracle, an assistant operating purely on the user's second brain.
Your goal is to answer the user's question USING ONLY the provided context below.
If the answer is not contained in the context, explicitly state that you don't know it based on your stored knowledge.
Do not hallucinate or extrapolate outside the context.

Context:
{context}

Question: {query}
"""

    llm = init_llm()
    response = llm.invoke(prompt)

    return {"answer": response.content, "sources": context_chunks}
