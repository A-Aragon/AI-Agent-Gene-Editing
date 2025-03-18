# WGE - CRISPR based on exons

import json
import os
import requests
from openai import OpenAI
from pydantic import BaseModel, Field

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------
# Función que llama a la API de WGE
# ----------------------------

def get_crisprs_by_exon(species, exon_ids):
    """Esta es una API pública que devuelve guías CRISPR para IDs de exones."""
    url = "https://wge.stemcell.sanger.ac.uk/api/crispr_search"
    params = {"species": species}

    # Aquí corregimos: TODOS los exon_ids deben ir como `exon_id[]`
    for exon_id in exon_ids:
        params.setdefault("exon_id[]", []).append(exon_id)

    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print("Error:", response.status_code, response.text)
        return None

# ----------------------------
# Definimos la herramienta
# ----------------------------

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_crisprs_by_exon",
            "description": "Recupera guías CRISPR para una especie y lista de exon_ids usando la API de WGE.",
            "parameters": {
                "type": "object",
                "properties": {
                    "species": {"type": "string"},
                    "exon_ids": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["species", "exon_ids"],
                "additionalProperties": False  # <-- Añadido aquí
            },
            "strict": True
        }
    }
]


system_prompt = "Eres un asistente que ayuda a encontrar guías CRISPR para genes."

# ----------------------------
# Input del usuario
# ----------------------------

user_input = input("Ask your question (e.g., CRISPR guides for exon ENSMUSE00000106755 in Mouse): ")

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_input},
]

# ----------------------------
# Llamada al modelo
# ----------------------------

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools,
)

# Mostrar qué decidió hacer GPT
print("\nGPT decided to call:")
print("Function:", completion.choices[0].message.tool_calls[0].function.name)
print("Arguments:", json.loads(completion.choices[0].message.tool_calls[0].function.arguments))

# ----------------------------
# Ejecutamos la función real
# ----------------------------

def call_function(name, args):
    if name == "get_crisprs_by_exon":
        # Capitalizamos la especie antes de llamar a la función
        args['species'] = args['species'].capitalize()
        return get_crisprs_by_exon(**args)

for tool_call in completion.choices[0].message.tool_calls:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    messages.append(completion.choices[0].message)

    result = call_function(name, args)
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": json.dumps(result)
    })

# ----------------------------
# Definimos el esquema del resultado
# ----------------------------

class CrisprResponse(BaseModel):
    exon_id: str = Field(description="Exon ID")
    crispr_guides: list[str] = Field(description="Lista de secuencias guía CRISPR")

# ----------------------------
# Segunda llamada a GPT con resultados reales
# ----------------------------

completion_2 = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=messages,
    tools=tools,
    response_format=CrisprResponse,
)

# ----------------------------
# Mostramos respuesta final
# ----------------------------

final_response = completion_2.choices[0].message.parsed

print("\nCRISPR Guides retrieved:")
print("Exon ID:", final_response.exon_id)
for i, guide in enumerate(final_response.crispr_guides, 1):
    print(f"{i}. {guide}")
