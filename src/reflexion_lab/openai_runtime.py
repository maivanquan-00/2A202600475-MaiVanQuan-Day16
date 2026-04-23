from __future__ import annotations
import json
import os
from typing import Any
from dotenv import load_dotenv
from openai import OpenAI
from .schemas import QAExample, JudgeResult, ReflectionEntry
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM
from .utils import normalize_answer

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=120.0,
    max_retries=5
)

def _parse_json_from_response(text: str) -> dict[str, Any]:
    """Extract and parse JSON from LLM response."""
    # Try to find JSON in the response
    text = text.strip()
    
    # If it starts with {, try to parse it directly
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON block
    start_idx = text.find("{")
    if start_idx != -1:
        # Find matching closing brace
        brace_count = 0
        for i, char in enumerate(text[start_idx:]):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    try:
                        return json.loads(text[start_idx:start_idx + i + 1])
                    except json.JSONDecodeError:
                        pass
    
    # If we couldn't parse, return empty dict
    return {}

def actor_answer(example: QAExample, attempt_id: int, agent_type: str, reflection_memory: list[str]) -> str:
    """Call OpenAI to generate an answer."""
    
    # Build context string
    context_str = "\n".join([f"Title: {chunk.title}\nText: {chunk.text}" for chunk in example.context])
    
    # Build reflection memory into the message if available
    reflection_hint = ""
    if reflection_memory:
        reflection_hint = "\n\nPrevious Reflection Feedback:\n" + "\n".join(reflection_memory)
    
    # Build user message
    user_message = f"""Question: {example.question}

Context:
{context_str}
{reflection_hint}"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": ACTOR_SYSTEM},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        answer_text = response.choices[0].message.content
        
        # Extract final answer from response
        if "Final Answer:" in answer_text:
            final_answer = answer_text.split("Final Answer:")[-1].strip()
        else:
            final_answer = answer_text.strip()
        
        return final_answer
    except Exception as e:
        print(f"Error calling OpenAI Actor: {e}")
        return ""

def evaluator(example: QAExample, answer: str) -> JudgeResult:
    """Call OpenAI to evaluate an answer."""
    
    user_message = f"""Please evaluate the following answer:

Question: {example.question}
Gold Answer: {example.gold_answer}
Predicted Answer: {answer}

Respond in JSON format with score (1 for correct, 0 for incorrect), reason, missing_evidence, and spurious_claims."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": EVALUATOR_SYSTEM},
                {"role": "user", "content": user_message}
            ],
            temperature=0,
            max_tokens=300
        )
        
        response_text = response.choices[0].message.content
        result_json = _parse_json_from_response(response_text)
        
        # Fallback: use basic normalization if JSON parsing fails
        if not result_json or "score" not in result_json:
            is_correct = normalize_answer(example.gold_answer) == normalize_answer(answer)
            return JudgeResult(
                score=1 if is_correct else 0,
                reason="Answer matches gold answer" if is_correct else "Answer does not match gold answer",
                missing_evidence=[],
                spurious_claims=[]
            )
        
        return JudgeResult(
            score=result_json.get("score", 0),
            reason=result_json.get("reason", ""),
            missing_evidence=result_json.get("missing_evidence", []),
            spurious_claims=result_json.get("spurious_claims", [])
        )
    except Exception as e:
        print(f"Error calling OpenAI Evaluator: {e}")
        # Fallback to simple comparison
        is_correct = normalize_answer(example.gold_answer) == normalize_answer(answer)
        return JudgeResult(
            score=1 if is_correct else 0,
            reason="Answer matches gold answer" if is_correct else "Answer does not match gold answer",
            missing_evidence=[],
            spurious_claims=[]
        )

def reflector(example: QAExample, attempt_id: int, judge: JudgeResult) -> ReflectionEntry:
    """Call OpenAI to generate reflection."""
    
    user_message = f"""Based on the failed attempt below, please provide a reflection:

Question: {example.question}
Evaluation Reason: {judge.reason}
Missing Evidence: {', '.join(judge.missing_evidence) if judge.missing_evidence else 'None identified'}

Please respond in JSON format with failure_reason, lesson, and next_strategy."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": REFLECTOR_SYSTEM},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        response_text = response.choices[0].message.content
        result_json = _parse_json_from_response(response_text)
        
        if not result_json or "failure_reason" not in result_json:
            # Fallback
            return ReflectionEntry(
                attempt_id=attempt_id,
                failure_reason=judge.reason,
                lesson="Try a different reasoning approach",
                next_strategy="Reconsider the evidence and try again"
            )
        
        return ReflectionEntry(
            attempt_id=attempt_id,
            failure_reason=result_json.get("failure_reason", judge.reason),
            lesson=result_json.get("lesson", ""),
            next_strategy=result_json.get("next_strategy", "")
        )
    except Exception as e:
        print(f"Error calling OpenAI Reflector: {e}")
        return ReflectionEntry(
            attempt_id=attempt_id,
            failure_reason=judge.reason,
            lesson="Try a different reasoning approach",
            next_strategy="Reconsider the evidence and try again"
        )

def get_token_count(response: dict) -> int:
    """Extract token count from OpenAI response."""
    if "usage" in response:
        return response["usage"].get("total_tokens", 0)
    return 0
