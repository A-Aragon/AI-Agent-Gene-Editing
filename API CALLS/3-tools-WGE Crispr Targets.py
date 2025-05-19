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
    """Devuelve guías CRISPR para IDs de exones."""
    url = "https://wge.stemcell.sanger.ac.uk/api/crispr_search"
    params = {"species": species}

    for exon_id in exon_ids:
        params.setdefault("exon_id[]", []).append(exon_id)

    response = requests.get(url, params=params)

    if response.status_code == 200:
        raw_data = response.json()
        # Procesar el resultado para devolver solo los campos deseados
        processed = {}
        for exon_id, guides in raw_data.items():
            processed[exon_id] = []
            for guide in guides:
                species_name = "Mouse" if guide.get("species_id") == 2 else "Human" if guide.get("species_id") == 4 else guide.get("species_id")
                processed[exon_id].append({
                    "id": guide.get("id"),
                    "chr_name": guide.get("chr_name"),
                    "chr_start": guide.get("chr_start"),
                    "chr_end": guide.get("chr_end"),
                    "seq": guide.get("seq"),
                    "pam_right": guide.get("pam_right"),
                    "ensembl_exon_id": guide.get("ensembl_exon_id"),
                    "off_target_summary": guide.get("off_target_summary"),
                    "exonic": guide.get("exonic"),
                    "species": species_name
                })
        return processed
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
                "additionalProperties": False
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
    model="gpt-4o-2024-08-06",
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
# Mostrar respuesta final directamente (sin schema en este caso)
# ----------------------------

final_result = json.loads(messages[-1]["content"])

print("\nCRISPR Guides retrieved:")
for exon_id, guides in final_result.items():
    print(f"\nExon ID: {exon_id}")
    for i, guide in enumerate(guides, 1):
        print(f"  {i}. ID: {guide['id']}, Chr: {guide['chr_name']}, Start: {guide['chr_start']}, End: {guide['chr_end']}")
        print(f"     Seq: {guide['seq']} | PAM Right: {guide['pam_right']} | Exonic: {guide['exonic']} | Species: {guide['species']}")
        print(f"     Off-target summary: {guide['off_target_summary']}")



