import json
import re
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain.chat_models import init_chat_model
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from typing_extensions import TypedDict
from typing import Annotated

load_dotenv()

# Initialize LLM
llm = init_chat_model("openai:gpt-4o-mini", temperature=0.0)

# Prompt template
prompt = PromptTemplate.from_template("""
You are a claims validation assistant.

Instructions:
- Your job is to determine whether the insurance claim should be ACCEPTED or REJECTED based on the given claim and the company's quotation policy.
- If the member's class and diagnosis are covered in the quotation data and the amount of the claim doesn't exceed the amount in quotation data, ACCEPT the claim.
- If not covered, REJECT the claim.
- If unsure, respond with "REJECT".

Respond strictly in the following JSON format:
{{
    "justification": "Short justification here...",
    "decision": "ACCEPT" or "REJECT"
}}

Claim Data:
{claim}

Quotation Policy:
{quotation_data}
""")

class State(TypedDict):
    messages: Annotated[list, add_messages]
    claim_data: dict
    quotation_data: dict
    justification: str
    decision: str

def build_graph():
    graph_builder = StateGraph(State)

    qa_chain = (
        {
            "claim": lambda state: state["claim_data"],
            "quotation_data": lambda state: state["quotation_data"]
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    def extract_json_from_response(text: str) -> str:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        return match.group(0) if match else "{}"

    def validate_claim(state: State):
        response = qa_chain.invoke(state)
        try:
            clean_json = extract_json_from_response(response)
            parsed = json.loads(clean_json)
            justification = parsed.get("justification", "").strip()
            decision = parsed.get("decision", "").strip().lower()
            if decision not in {"accept", "reject"}:
                raise ValueError("Invalid decision value")
        except Exception as e:
            justification = f"⚠️ Failed to parse response: {e}"
            decision = "reject"
        return {"decision": decision, "justification": justification}

    def final_decision(state: State):
        return {
            "messages": [{
                "role": "system",
                "content": f"Claim is {state['decision']}",
                "justification": state["justification"]
            }]
        }

    graph_builder.add_node("validate_claim", validate_claim)
    graph_builder.add_node("final_decision", final_decision)
    graph_builder.add_edge(START, "validate_claim")
    graph_builder.add_edge("validate_claim", "final_decision")
    graph_builder.add_edge("final_decision", END)

    return graph_builder.compile()

def get_quotation_data(class_: str, company_name: str = "company_X") -> list:
    with open(f"data/processed/{company_name}.json", "r") as f:
        quotation_data = json.load(f)
        return (
            quotation_data['English']['AdditionalBenefits']['Values'].get(class_, []) +
            quotation_data['English']['HighLevelBenefit']['Values'].get(class_, [])
        )

# Graph instance (cached)
GRAPH = build_graph()

def run_claim_validation(claim: dict, quotation_data: list):
    return GRAPH.invoke({
        "claim_data": claim,
        "quotation_data": quotation_data,
        "messages": []
    })