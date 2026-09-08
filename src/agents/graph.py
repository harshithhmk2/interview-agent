from typing import Dict, Any, Union
from langgraph.graph import StateGraph, END, START
from src.agents.state import InterviewState
from src.agents.nodes.planner import PlannerNode
from src.agents.nodes.interviewer import InterviewerNode
from src.agents.nodes.evaluator import EvaluatorNode
from src.agents.nodes.reporter import ReporterNode
from src.services.llm import get_llm_client

# Initialize standard nodes with dynamic client resolution
planner_node = PlannerNode()
interviewer_node = InterviewerNode()
evaluator_node = EvaluatorNode()
reporter_node = ReporterNode()


# --- Node Wrappers ---
async def planner_step(state: InterviewState) -> Dict[str, Any]:
    """
    Executes the planning node to analyze resume/JD and map the interview question plan.
    """
    return await planner_node.execute(state)


async def interviewer_step(state: InterviewState) -> Dict[str, Any]:
    """
    Executes the interviewer node to select or generate the next question.
    """
    return await interviewer_node.execute(state)


async def evaluator_step(state: InterviewState) -> Dict[str, Any]:
    """
    Executes the evaluator node to grade the candidate's last answer.
    """
    return await evaluator_node.execute(state)


async def increment_index_step(state: InterviewState) -> Dict[str, Any]:
    """
    State orchestration step: increments the question plan index by 1.
    """
    return {
        "current_question_index": state.get("current_question_index", 0) + 1
    }


async def reporter_step(state: InterviewState) -> Dict[str, Any]:
    """
    Executes the reporter node to compile final score card summaries.
    """
    return await reporter_node.execute(state)


# --- Routing Decisions ---
def route_after_evaluation(state: InterviewState) -> str:
    """
    Decides whether to formulate an adaptive follow-up or advance to the next planned question index.
    - If turn count reaches session limit (>= 5 turns): advance index to conclude session.
    - If score is shallow (< 6.0) and follow-up count < 2: loop back to 'interviewer' for follow-up.
    - Else: go to 'increment_index' to move on.
    """
    turns_history = state.get("turns_history", [])
    questions_plan = state.get("questions_plan", [])
    total_plan_count = len(questions_plan) if questions_plan else 5
    
    if not turns_history:
        return "interviewer"
        
    if len(turns_history) >= 5 or len(turns_history) >= total_plan_count:
        return "increment_index"

    last_turn = turns_history[-1]
    turn_score = last_turn.get("score")
    follow_ups_count = last_turn.get("follow_ups_asked", 0)

    # Condition 1: Shallow answer and follow-up budget remains -> trigger follow-up
    if turn_score is not None and turn_score < 6.0 and follow_ups_count < 2:
        return "interviewer"

    # Condition 2: Answer satisfactory or budget exhausted -> advance index
    return "increment_index"


def route_after_increment(state: InterviewState) -> str:
    """
    Checks if there are remaining planned questions left in the queue.
    - Yes: Loop back to 'interviewer'.
    - No: Go to 'reporter' to finalize the evaluation sheet.
    """
    current_idx = state.get("current_question_index", 0)
    questions_plan = state.get("questions_plan", [])
    turns_history = state.get("turns_history", [])
    total_plan_count = len(questions_plan) if questions_plan else 5
    
    if current_idx >= total_plan_count or len(turns_history) >= 5:
        return "reporter"
    return "interviewer"


# --- Graph Construction ---
# Define state graph matching workflow design specifications
workflow = StateGraph(InterviewState)

# Add processing nodes
workflow.add_node("planner", planner_step)
workflow.add_node("interviewer", interviewer_step)
workflow.add_node("evaluator", evaluator_step)
workflow.add_node("increment_index", increment_index_step)
workflow.add_node("reporter", reporter_step)

# Wire the graph logic flow
workflow.add_edge(START, "planner")
workflow.add_edge("planner", "interviewer")

# Interrupted states: interviewer yields prompt, candidate responds, then evaluator runs.
workflow.add_edge("interviewer", "evaluator")

# Add conditional routing paths
workflow.add_conditional_edges(
    "evaluator",
    route_after_evaluation,
    {
        "interviewer": "interviewer",
        "increment_index": "increment_index"
    }
)

workflow.add_conditional_edges(
    "increment_index",
    route_after_increment,
    {
        "interviewer": "interviewer",
        "reporter": "reporter"
    }
)

workflow.add_edge("reporter", END)

# Compile graph
# Intercepts execution after the interviewer finishes asking the question
# This allows the API endpoint to yield the question back to the candidate,
# wait for response chunks, and resume the graph run starting at the evaluator node.
compiled_graph = workflow.compile()
