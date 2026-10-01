from deepeval.models import DeepEvalBaseLLM
from groq import Groq, RateLimitError
import os
import time
from dotenv import load_dotenv
import re

load_dotenv()

class GroqModel(DeepEvalBaseLLM):
    """"
        Wraps Groq's API so DeepEval can use it as a model for evaluation.
    """
    def __init__(self,model_name : str = "openai/gpt-oss-120b"):
        self.model_name = model_name
        
        self.client = Groq(api_key=os.environ["GROQ_API_KEY"])

    def load_model(self):
        """
            Loads the model from Groq's API.
        """
        return self.client

    def generate(self, prompt: str) -> str:
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0 # more deterministic, less likely to add extra commentary
                )

                content = response.choices[0].message.content

                if not content or not content.strip():
                    raise ValueError("Empty response from model")

                #strip markdown code fences if model wrapped its JSON in them
                content = re.sub(r"^```(?:json)?\s*", "", content.strip())
                content = re.sub(r"\s*```$", "", content)

                return content 
            
            except RateLimitError:
                wait_time = 5 * (attempt + 1)
                print(f"Rate limited, waiting {wait_time}s before retry ({attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
            except ValueError as e:
                print(f"Bad response ({e}), retrying ({attempt + 1}/{max_retries})...")
                time.sleep(2)

        raise RuntimeError("Exceeded max retries due to rate limiting or invalid responses.")


        
       

    async def a_generate(self, prompt: str) -> str:
        # DeepEval sometimes calls this async version; just reuse the sync client for now
        
        return self.generate(prompt)

    def get_model_name(self) -> str:
        return f"Groq-{self.model_name}"