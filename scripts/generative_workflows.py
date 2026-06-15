import json
import operator
from typing import TypedDict, List, Annotated
from pydantic import BaseModel, Field
from langchain_community.llms import GPT4All 
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, START, END

# 1. Define the desired JSON structure using Pydantic
class Expert(BaseModel):
	name: str = Field(description="The professional title or role of the expert")
	description: str = Field(description="A few sentences detailing their specialized domain and how they connect with other agents")

class ExpertTeam(BaseModel):
	team: List[Expert] = Field(description="A list of the experts organized to answer the user query")

parser = JsonOutputParser(pydantic_object=ExpertTeam)
expert_parser = JsonOutputParser(pydantic_object=Expert)

# 2. Define the Prompt Template
# -> Added {chat_history} to give the LLM previous context
template = """
           Here is the conversation history and the experts we have created so far:
           {chat_history}
           
           Please organize a team of experts to help answer the following question:
           
           {user_query}
           
           Please organize your team to help cover every single aspect of this question in full detail and connection with the other agents in the team. Please focus on providing as much specialization to the expert domains as you can. Feel free to add as many different kinds of members to the team as you like. 
           
           {format_instructions}
           
           Return ONLY valid JSON. Do not include any introductory or concluding text.
           """

recovery_template = """
                    Please help recover the malformed Expert that has been constructed to answer the following question:
                    
                    {user_query}
                    
                    Here's the expert:
                    
                    {malformed_expert}
                    
                    Please focus on providing as much specialization to the expert domains as you can.
                    
                    {format_instructions}
                    """

# -> Added "chat_history" to input_variables
prompt = PromptTemplate(
	template=template, 
	input_variables=["user_query", "chat_history"],
	partial_variables={"format_instructions": parser.get_format_instructions()}
)

recovery_template = PromptTemplate(
	template=recovery_template, 
	input_variables=["user_query", "malformed_expert"],
	partial_variables={"format_instructions": expert_parser.get_format_instructions()}
)


# 3. Initialize the Model
model_name = "Nous-Hermes-2-Mistral-7B-DPO.Q4_0.gguf"

llm = GPT4All(
	model=model_name, 
	device="gpu", 
	verbose=True, 
)

# 4. Define the Graph State
class State(TypedDict):
	user_query: str
	parsed_team: List[dict] # Updated to List[dict] to handle the team array natively
	# -> operator.add tells LangGraph to APPEND new items to this list, not overwrite it!
	chat_history: Annotated[List[str], operator.add] 

# 5. Define the Modular Node Functions
def generate_expert_team(state: State):
	"""Node 1: Generates the initial batch of experts."""
	history_list = state.get("chat_history", [])
	history_str = "\n".join(history_list) if history_list else "No previous history."

	chain = prompt | llm | parser
	result = chain.invoke({
		"user_query": state["user_query"],
		"chat_history": history_str
	})

	print(result)
	
	# Extract the list of experts and save it to the state
	return {"parsed_team": result.get("team", [])}

def check_team_validity(state: State) -> str:
	"""Router: Evaluates the current state and decides the next step."""
	for expert in state.get("parsed_team", []):
		name = expert.get("name", "")
		desc = expert.get("description", "")
		if len(name) < 3 or len(desc) < 10:
			return "needs_recovery"
	return "is_valid"

def recover_experts(state: State):
	"""Node 2: Iterates through the team and fixes ONLY the malformed ones."""
	recovered_team = []
	for expert in state.get("parsed_team", []):
		name = expert.get("name", "")
		desc = expert.get("description", "")
		
		# If malformed, run the recovery chain
		if len(name) < 3 or len(desc) < 10:
			recovery_chain = recovery_template | llm | expert_parser
			fixed_expert = recovery_chain.invoke({
				"user_query": state["user_query"], 
				"malformed_expert": expert
			})
			print(fixed_expert)
			recovered_team.append(fixed_expert)
		else:
			# Otherwise, keep the healthy expert untouched
			recovered_team.append(expert)
			
	return {"parsed_team": recovered_team}

def record_history(state: State):
	"""Node 3: Formats the final, approved team into the chat history."""
	new_interaction = [
		f"User: {state['user_query']}",
		f"AI (Team Created): {json.dumps(state['parsed_team'])}"
	]
	return {"chat_history": new_interaction}

# 6. Build and Compile the LangGraph
builder = StateGraph(State)

# Add our separate nodes
builder.add_node("generate_expert_team", generate_expert_team)
builder.add_node("recover_experts", recover_experts)
builder.add_node("record_history", record_history)

# Step 1: Start -> Generate
builder.add_edge(START, "generate_expert_team")

# Step 2: Generation -> Check Validity
# If valid, go record history. If invalid, divert to recovery.
builder.add_conditional_edges(
	"generate_expert_team",
	check_team_validity,
	{
		"needs_recovery": "recover_experts",
		"is_valid": "record_history"
	}
)

# Step 3: Recovery -> Check Validity
# This creates a native "while loop" in the graph architecture! 
# It will keep looping back to recovery until the team is perfect.
builder.add_conditional_edges(
	"recover_experts",
	check_team_validity,
	{
		"needs_recovery": "recover_experts",
		"is_valid": "record_history"
	}
)

# Step 4: Record History -> End
builder.add_edge("record_history", END)

graph = builder.compile()

# 7. Run the Graph
if __name__ == "__main__":
	# --- Turn 1 ---
	query_1 = "What is the most effective way of finding beauty in the subtle and unexpected things I don't think about often?"
	print(f"Invoking Turn 1: '{query_1}'...\n")
	
	# Initial state: history is an empty list
	state_1 = graph.invoke({"user_query": query_1, "chat_history": []})
	print(json.dumps(state_1["parsed_team"], indent=4))

	
	# --- Turn 2 ---
	query_2 = "Please make sure that the descriptions are complete"
	print(f"\nInvoking Turn 2: '{query_2}'...\n")
	
	# We pass the resulting state from Turn 1 straight back into Turn 2!
	# We just update the user_query. LangGraph handles keeping the history intact.
	state_1["user_query"] = query_2
	state_2 = graph.invoke(state_1)

	print("--- Final Parsed JSON Object (Turn 2) ---\n")
	print(json.dumps(state_2["parsed_team"], indent=4))