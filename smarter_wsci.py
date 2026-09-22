from pathlib import Path
from ollama import chat
import json



question = """
I changed my university password this morning.
Now my Windows laptop won't connect to campus Wi-Fi,
but my phone still works.
"""

## WRITE ##
service_status = {
    "wifi": "operational"
}

state = {
    "problem": question,
    "device": "Windows laptop",
    "wi_fi status": "operational",
    "wi-fi_check": True
}

with open("state.json", "w") as file:
    json.dump(
        state,
        file,
        indent=2
    )

with open("state.json", "r") as file:
    state = json.load(file)

print(state)


## SELECT CONTEXT FILES BASED ON QUESTION
## Create the function that takes the student's question, takes some keywords and chooses the relevant files from the knowledge base. Return a list of the selected files.
## For example, if the question has the kyeword "print" or "printer", then the function should return the file "knowledge/printer_setup.txt" in a list.
def select_context(question):
    q = question.lower()
    mapping = {
        "wifi": "knowledge/wifi_setup.txt",
        "wi-fi": "knowledge/wifi_setup.txt",
        "password": "knowledge/password_changes.txt",
        "service": "knowledge/service_status.txt",
        "status": "knowledge/service_status.txt",
    }
    selected = set()
    for keyword, path in mapping.items():
        if keyword in q:
            selected.add(path)
    if not selected:
        selected = {
            "knowledge/wifi_setup.txt",
            "knowledge/password_changes.txt",
            "knowledge/service_status.txt",
        }
    return sorted(selected)


selected_files = select_context(question)
print("Selected:", selected_files)

## READ SELECTED FILES and add their contents to the context variable.
context = ""
for file in selected_files:
    p = Path(file)
    if p.exists():
        context += p.read_text() + "\n\n"
    else:
        print(f"[skip] {file}")

print("Context characters:", len(context))

## 
## COMPRESS CONTEXT
## Add logic to compress the context from above by calling Qwen with "context" and the "question" as the parameter
## The response from Qwen should be the compressed context. Store it in a variable called "compressed_context" 

def compress_context(context, question):
    prompt = f"""You are a university IT support assistant.
Extract ONLY the information relevant to the student's problem below.
Keep:
- Windows Wi-Fi troubleshooting steps
- password change effects (cached credentials)
- current service status (operational / down)
Drop:
- printing, projectors, VPN, email, software installation

STUDENT QUESTION:
{question}

RAW CONTEXT:
{context}

Return a short, structured summary in plain text. Do not include the original text verbatim."""

    resp = chat(
        model="qwen3:8b", 
        messages=[{"role": "user", "content": prompt}],
        options={
            "num_predict": 400,
            "temperature": 0.3,
        }
    )
    return resp.message.content


compressed_context = compress_context(context, question)



## Print the length of the compressed context
print(len(compressed_context))
print(compressed_context)
## Now, call Qwen again with the compressed context and the student's question. Store the response in a variable called "response" and print the response from Qwen.
## Ensure the model produces a structured output 

system_prompt = """You are a university IT support assistant.
Respond ONLY with a valid JSON object matching this schema:
{
  "issue": "string",
  "device": "string",
  "likely_cause": "string",
  "steps": ["step1", "step2"],
  "priority": "LOW" | "MEDIUM" | "HIGH"
}
Rules:
- No text outside the JSON.
- No markdown code fences.
- Start with { and end with }."""

response = chat(
    model="qwen3:8b",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Question: {question}\n\nRelevant context:\n{compressed_context}"}
    ],
    options={
        "num_predict": 500,
        "temperature": 0.2,
    }
)


print(response.message.content)

## WRITE the above output in an artifact called "state"
raw = response.message.content.strip()

if raw.startswith("```"):
    raw = raw.strip("`")
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()

try:
    answer = json.loads(raw)
except json.JSONDecodeError:
    answer = {"raw": raw}

with open("state.json", "r") as file:
    state = json.load(file)

state["diagnosis"] = answer

with open("state.json", "w") as file:
    json.dump(
        state,
        file,
        indent=2
    )

print(state)
## Update the rest of the code so that it uses the "state" artifact as part of the context. 
## It is important to ensure that the model uses only the relevant parts from the "state" artifact and not the entire artifact.
## For this, you may have to think of a good structure for the "state" artifact and how to use it in the context.
def load_relevant_state(task):
    with open("state.json", "r") as file:
        st = json.load(file)

    if task == "diagnosis":
        keys = ("problem", "device", "wi_fi status", "diagnosis")
    elif task == "report":
        keys = ("wi_fi status", "wi-fi_check", "diagnosis")
    else:
        keys = ()

    return {k: st[k] for k in keys if k in st}


diagnostic_context = load_relevant_state("diagnosis")
report_context = load_relevant_state("report")

print("Diagnostic context:", diagnostic_context)
print("Report context:", report_context)

