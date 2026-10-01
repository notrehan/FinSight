import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from search import search


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("OPENAI_API_KEY")
model_name = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY is missing from .env"
    )

client = OpenAI(api_key=api_key)


def answer_question(company: str, question: str):
    # 1. Retrieve evidence from the selected company.
    results = search(
        company=company,
        query=question,
        top_k=5,
    )

    # 2. Format the retrieved evidence for the LLM.
    source_blocks = []

    for i, result in enumerate(results, start=1):
        source_blocks.append(
            f"""
[Source {i}]
Company: {result["company"]}
Document: {result["document"]}
Page: {result["page"]}

Content:
{result["text"]}
"""
        )

    context = "\n".join(source_blocks)

    # 3. Tell the model how to answer.
    instructions = """
You are FinSight, a financial research assistant.

Answer the user's question using ONLY the retrieved sources.

Rules:
- Do not invent facts.
- Do not use outside knowledge.
- If the sources are insufficient, clearly say so.
- Give a concise, clear explanation.
- Only cite information supported by the retrieved sources.
- Do not give investment advice.
- Do not tell the user to buy, sell, or hold a stock.
- Return the answer using the required JSON structure.
"""

    prompt = f"""
Company: {company}

User question:
{question}

Retrieved sources:
{context}
"""

    # 4. Ask the model for a schema-constrained JSON response.
    response = client.responses.create(
        model=model_name,
        instructions=instructions,
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "financial_research_answer",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "answer": {
                            "type": "string"
                        },
                        "sources": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "document": {
                                        "type": "string"
                                    },
                                    "page": {
                                        "type": "integer"
                                    }
                                },
                                "required": [
                                    "document",
                                    "page"
                                ],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": [
                        "answer",
                        "sources"
                    ],
                    "additionalProperties": False
                }
            }
        }
    )

    # Structured Outputs gives us JSON text matching the schema.
    answer_data = json.loads(response.output_text)

    return answer_data, results


def main():
    company = input(
        "Company (infosys/tcs): "
    ).strip()

    question = input(
        "Ask a question: "
    ).strip()

    try:
        answer_data, sources = answer_question(
            company=company,
            question=question,
        )

        print("\nSTRUCTURED RESPONSE")
        print("=" * 80)
        print(
            json.dumps(
                answer_data,
                indent=2,
                ensure_ascii=False,
            )
        )

    except Exception as error:
        print(f"\nError: {error}")


if __name__ == "__main__":
    main()
