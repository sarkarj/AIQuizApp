"""
AI Quiz Platform - LLM Service
Version: 1.2.1
Changelog: 
- FIXED: Robust JSON extraction for GPT responses (handles extra text, multiple objects)
- Better error handling for malformed LLM responses
- Stack-based brace matching for accurate JSON boundaries
"""

import json
import boto3
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from config.settings import settings
import streamlit as st

class LLMService:
    """Service for interacting with multiple LLM providers via AWS Bedrock"""
    
    def __init__(self):
        # Initialize Bedrock client
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
    
    def _extract_json_from_text(self, text: str) -> Optional[Dict]:
        """
        FIXED: Robust JSON extraction using stack-based brace matching
        Handles cases where LLM adds text before/after JSON
        """
        # Try parsing entire text first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Find first opening brace
        start_idx = text.find('{')
        if start_idx == -1:
            return None
        
        # Use stack to find matching closing brace
        stack = []
        end_idx = -1
        
        for i in range(start_idx, len(text)):
            char = text[i]
            if char == '{':
                stack.append(char)
            elif char == '}':
                if stack:
                    stack.pop()
                    if not stack:  # Found matching closing brace
                        end_idx = i + 1
                        break
        
        if end_idx == -1:
            return None
        
        # Extract JSON substring
        json_str = text[start_idx:end_idx]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # Log for debugging
            if settings.DEBUG_MODE:
                print(f"JSON extraction failed: {str(e)}")
                print(f"Attempted to parse: {json_str[:200]}...")
            return None
    
    def _build_comprehensive_validation_prompt(self, question_data: Dict, quiz_metadata: Optional[Dict] = None) -> str:
        """
        Build comprehensive prompt for validation AND explanation generation
        This prompt generates everything needed during admin question creation
        """
        
        context = ""
        if quiz_metadata:
            context = f"""
You are an expert in {quiz_metadata.get('topic_domain', 'this subject')} at the {quiz_metadata.get('target_level', 'intermediate')} level.
{f"This is related to {quiz_metadata.get('cert_reference')}" if quiz_metadata.get('cert_reference') else ""}
"""
        
        expected_note = ""
        if question_data.get('response_type') == 'multiple' and question_data.get('expected_count'):
            expected_note = f"\nEXPECTED SELECTIONS: {question_data['expected_count']}"
        
        stored_answer_note = ""
        if question_data.get('correct_answer'):
            stored_answer_note = f"\n\nSTORED ANSWER (for comparison): {question_data['correct_answer']}"
        
        prompt = f"""{context}
Analyze the following question and provide a comprehensive educational response:

QUESTION:
{question_data['question_text']}

OPTIONS:
{question_data['options_text']}

RESPONSE TYPE: {question_data['response_type']}{expected_note}{stored_answer_note}

Your task:
1. Determine the correct answer(s) based on your expertise
2. Provide a detailed explanation of WHY the correct answer is correct
3. Explain WHY each wrong option is incorrect
4. Identify the key concept being tested
5. Provide references or documentation sources
6. If a stored answer is provided, compare with it

CRITICAL: Respond with ONLY valid JSON, no additional text before or after.

JSON format:
{{
  "your_answer": "A" or "A,B,C",
  "confidence": "high" or "medium" or "low",
  "agrees_with_stored": true or false or null,
  "explanation": "Full explanation of why the correct answer is right (2-3 sentences)",
  "why_wrong": {{
    "B": "Explanation of why B is wrong",
    "C": "Explanation of why C is wrong",
    "D": "Explanation of why D is wrong"
  }},
  "key_concept": "One-sentence main takeaway or concept being tested",
  "references": ["Specific documentation URL or source 1", "Source 2"],
  "concerns": "Any issues with question quality or null if none"
}}

Remember: ONLY return the JSON object, nothing else."""
        
        return prompt
    
    def _call_claude(self, prompt: str) -> Dict[str, Any]:
        """Call Claude via Bedrock"""
        try:
            response = self.bedrock_client.invoke_model(
                modelId=settings.BEDROCK_LLM_ID_CLAUDE,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": settings.LLM_MAX_TOKENS,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": settings.LLM_TEMPERATURE
                })
            )
            
            result = json.loads(response['body'].read())
            content = result['content'][0]['text']
            
            # Use robust JSON extraction
            parsed = self._extract_json_from_text(content)
            
            if parsed:
                return {"success": True, "data": parsed, "model": "claude"}
            else:
                return {"success": False, "error": "Could not extract valid JSON from response", "model": "claude", "raw_content": content[:500]}
                
        except Exception as e:
            return {"success": False, "error": str(e), "model": "claude"}
    
    def _call_gpt(self, prompt: str) -> Dict[str, Any]:
        """FIXED: Call GPT via Bedrock with robust JSON extraction"""
        try:
            response = self.bedrock_client.invoke_model(
                modelId=settings.BEDROCK_LLM_ID_GPT,
                body=json.dumps({
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": settings.LLM_MAX_TOKENS,
                    "temperature": settings.LLM_TEMPERATURE
                })
            )
            
            result = json.loads(response['body'].read())
            
            # Handle different response formats from Bedrock GPT
            content = ""
            if 'content' in result:
                if isinstance(result['content'], list):
                    content = result['content'][0].get('text', '')
                else:
                    content = result['content']
            elif 'choices' in result:
                content = result['choices'][0].get('message', {}).get('content', '')
            elif 'completion' in result:
                content = result['completion']
            else:
                # Fallback: try to find text in any nested structure
                content = str(result)
            
            # Use robust JSON extraction
            parsed = self._extract_json_from_text(content)
            
            if parsed:
                return {"success": True, "data": parsed, "model": "gpt"}
            else:
                return {
                    "success": False, 
                    "error": "Could not extract valid JSON from GPT response", 
                    "model": "gpt",
                    "raw_content": content[:500] if content else "No content"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e), "model": "gpt"}
    
    def validate_question(self, question_data: Dict, quiz_metadata: Optional[Dict] = None) -> Dict:
        """
        Validate question with 2 LLMs in PARALLEL (Claude and GPT)
        Uses ThreadPoolExecutor for concurrent execution
        
        Returns:
            {
                'all_agree': bool,
                'claude': dict with full explanation,
                'gpt': dict with full explanation,
                'agreement_count': int,
                'consensus_answer': str
            }
        """
        prompt = self._build_comprehensive_validation_prompt(question_data, quiz_metadata)
        
        # Parallel execution using ThreadPoolExecutor
        results = {}
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_model = {
                executor.submit(self._call_claude, prompt): 'claude',
                executor.submit(self._call_gpt, prompt): 'gpt'
            }
            
            for future in as_completed(future_to_model):
                model_name = future_to_model[future]
                try:
                    results[model_name] = future.result()
                except Exception as e:
                    results[model_name] = {"success": False, "error": str(e), "model": model_name}
        
        # Extract results
        claude_result = results.get('claude', {"success": False, "error": "No result", "model": "claude"})
        gpt_result = results.get('gpt', {"success": False, "error": "No result", "model": "gpt"})
        
        # Count agreements
        stored_answer = question_data.get('correct_answer', '').upper().replace(' ', '')
        agreements = 0
        answers = []
        
        # Collect answers from successful LLM calls
        for result in [claude_result, gpt_result]:
            if result['success']:
                llm_answer = result['data'].get('your_answer', '').upper().replace(' ', '')
                answers.append(llm_answer)
                
                # If stored answer exists, check agreement
                if stored_answer:
                    if llm_answer == stored_answer:
                        agreements += 1
                    # Update agrees_with_stored flag
                    result['data']['agrees_with_stored'] = (llm_answer == stored_answer)
        
        # Determine consensus answer
        consensus_answer = stored_answer if stored_answer else ''
        
        # If no stored answer or both LLMs agree on same answer
        if len(answers) == 2:
            if answers[0] == answers[1]:
                consensus_answer = answers[0]
                all_agree = True
            else:
                all_agree = False
                # Use first valid answer as consensus if no stored answer
                if not stored_answer:
                    consensus_answer = answers[0]
        else:
            all_agree = False
        
        # If stored answer exists, check if both agree with it
        if stored_answer and len(answers) == 2:
            all_agree = (agreements == 2)
        
        return {
            'all_agree': all_agree,
            'claude': claude_result,
            'gpt': gpt_result,
            'agreement_count': agreements if stored_answer else (2 if len(answers) == 2 and answers[0] == answers[1] else 0),
            'consensus_answer': consensus_answer
        }
    
    def get_stored_explanation(self, validation_data: Dict) -> Dict:
        """
        Extract stored explanations from validation_data for display during quiz
        Returns both Claude and GPT explanations
        
        Returns:
            {
                'claude': {explanation, key_concept, references, why_wrong},
                'gpt': {explanation, key_concept, references, why_wrong},
                'has_claude': bool,
                'has_gpt': bool
            }
        """
        result = {
            'claude': None,
            'gpt': None,
            'has_claude': False,
            'has_gpt': False
        }
        
        # Extract Claude explanation
        if validation_data.get('claude', {}).get('success'):
            claude_data = validation_data['claude']['data']
            result['claude'] = {
                'explanation': claude_data.get('explanation', 'No explanation available'),
                'key_concept': claude_data.get('key_concept', 'No key concept provided'),
                'references': claude_data.get('references', []),
                'why_wrong': claude_data.get('why_wrong', {})
            }
            result['has_claude'] = True
        
        # Extract GPT explanation
        if validation_data.get('gpt', {}).get('success'):
            gpt_data = validation_data['gpt']['data']
            result['gpt'] = {
                'explanation': gpt_data.get('explanation', 'No explanation available'),
                'key_concept': gpt_data.get('key_concept', 'No key concept provided'),
                'references': gpt_data.get('references', []),
                'why_wrong': gpt_data.get('why_wrong', {})
            }
            result['has_gpt'] = True
        
        return result

# Singleton instance
_llm_service_instance = None

def get_llm_service():
    """Get or create LLM service singleton"""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance

# Create instance only when explicitly called
llm_service = None

def init_llm_service():
    """Initialize LLM service - call this after set_page_config"""
    global llm_service
    if llm_service is None:
        llm_service = get_llm_service()
    return llm_service