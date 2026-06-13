"""
Training data generator for AtmaCore.
Programmatically synthesizes prompt-fact-target training pairs representing 5 distinct categories,
saving them as JSON Lines split into train and validation sets.
"""

import json
import os
import random
from typing import Dict, Any, List, Tuple


class AtmaCoreDataGenerator:
    """Generates synthetic prompts, facts, and target answers for training AtmaCore."""

    def __init__(self):
        self.math_exprs = [
            ("45 * 123", 5535, "multiplication"),
            ("18% of 25000", 4500, "percentage"),
            ("124 + 876", 1000, "addition"),
            ("500 / 4", 125, "division"),
            ("101 - 36", 65, "subtraction"),
            ("15 % 4", 3, "modulo"),
            ("7 * 8", 56, "multiplication"),
            ("2026 - 1999", 27, "subtraction")
        ]
        self.languages = ["English", "Python", "Javascript", "Rust", "C++", "Java", "Ruby", "Go"]
        self.pref_keys = ["theme", "username", "notifications", "font_family", "layout"]
        self.pref_vals = ["dark", "Jenil", "enabled", "Fira Code", "sidebar"]

    def generate_category_1(self) -> Dict[str, Any]:
        """Category 1: Verified-fact synthesis pairs (60% of data)."""
        fact_type = random.choice(["math", "language", "code_check", "memory"])
        
        if fact_type == "math":
            expr, res, op_name = random.choice(self.math_exprs)
            prompt = f"Calculate {expr}"
            facts = [{"type": "calculation", "expression": expr, "result": res, "method": f"safe_{op_name}"}]
            target = f"The calculation result of {expr} is {res}."
            
        elif fact_type == "language":
            lang = random.choice(self.languages)
            prompt = f"Greet the user in {lang}"
            facts = [{"type": "greeting", "keyword": "hello", "value": f"Welcome to the Colony in {lang}."}]
            target = f"Welcome to the Colony in {lang}."
            
        elif fact_type == "code_check":
            lang = random.choice(self.languages)
            prompt = f"Check python syntax for {lang}"
            facts = [
                {"type": "code_language", "language": lang},
                {"type": "syntax_check", "language": lang, "valid": True}
            ]
            target = f"Detected code language is {lang} and the syntax is valid."
            
        else: # memory
            key = random.choice(self.pref_keys)
            val = random.choice(self.pref_vals)
            prompt = f"Retrieve my {key} preference"
            facts = [{"type": "retrieved_preference", "key": key, "value": val}]
            target = f"Your remembered {key} preference is {val}."

        return {"prompt": prompt, "facts": facts, "target": target}

    def generate_category_2(self) -> Dict[str, Any]:
        """Category 2: Template synthesis (15% of data)."""
        expr, res, op_name = random.choice(self.math_exprs)
        style = random.choice(["formal", "casual", "concise"])
        
        prompt = f"Calculate {expr} and explain it"
        facts = [{"type": "calculation", "expression": expr, "result": res, "method": f"safe_{op_name}"}]
        
        if style == "formal":
            target = f"Upon evaluating the mathematical expression {expr}, the resultant value is computed as {res}."
        elif style == "casual":
            target = f"Evaluated {expr} and got {res}. Pretty simple math!"
        else: # concise
            target = f"{expr} = {res}."
            
        return {"prompt": prompt, "facts": facts, "target": target}

    def generate_category_3(self) -> Dict[str, Any]:
        """Category 3: Missing-fact responses (10% of data)."""
        missing_topics = ["capital of Mars", "weather in London", "price of bitcoin", "meaning of life"]
        topic = random.choice(missing_topics)
        
        prompt = f"What is the {topic}?"
        facts = []  # Empty facts list
        target = f"I could not find verified facts regarding {topic} in the provided inputs."
        
        return {"prompt": prompt, "facts": facts, "target": target}

    def generate_category_4(self) -> Dict[str, Any]:
        """Category 4: Contradiction handling (10% of data)."""
        lang_1 = random.choice(self.languages)
        lang_2 = random.choice([l for l in self.languages if l != lang_1])
        
        prompt = "Determine the active programming language"
        facts = [
            {"type": "code_language", "language": lang_1, "confidence": 0.85},
            {"type": "code_language", "language": lang_2, "confidence": 0.88}
        ]
        target = f"Contradiction detected: both {lang_1} and {lang_2} are claimed as active languages."
        
        return {"prompt": prompt, "facts": facts, "target": target}

    def generate_category_5(self) -> Dict[str, Any]:
        """Category 5: Style adaptation (5% of data)."""
        key = random.choice(self.pref_keys)
        val = random.choice(self.pref_vals)
        tone = random.choice(["short", "detailed"])
        
        prompt = f"Find preference for {key}"
        facts = [
            {"type": "retrieved_preference", "key": key, "value": val},
            {"type": "memory_context", "key": "tone", "value": tone}
        ]
        
        if tone == "short":
            target = f"{key}: {val}."
        else:
            target = f"Looking up memory context, your preference for {key} is registered as {val}."
            
        return {"prompt": prompt, "facts": facts, "target": target}

    def generate_sample(self) -> Dict[str, Any]:
        """Draws a random sample conforming to the category probability split."""
        roll = random.random()
        if roll < 0.60:
            return self.generate_category_1()
        elif roll < 0.75:
            return self.generate_category_2()
        elif roll < 0.85:
            return self.generate_category_3()
        elif roll < 0.95:
            return self.generate_category_4()
        else:
            return self.generate_category_5()

    def generate_and_save(self, output_dir: str, num_samples: int = 10000, split_ratio: float = 0.9) -> Tuple[str, str]:
        """Generates the dataset and saves it into train and validation split files."""
        os.makedirs(output_dir, exist_ok=True)
        
        samples = [self.generate_sample() for _ in range(num_samples)]
        
        split_idx = int(num_samples * split_ratio)
        train_samples = samples[:split_idx]
        val_samples = samples[split_idx:]
        
        train_path = os.path.join(output_dir, "train_data.jsonl")
        val_path = os.path.join(output_dir, "val_data.jsonl")
        
        with open(train_path, "w", encoding="utf-8") as f:
            for s in train_samples:
                # Convert facts back to string format if we want them as raw strings in datasets
                facts_str = json.dumps(s["facts"])
                f.write(json.dumps({"prompt": s["prompt"], "facts": facts_str, "target": s["target"]}) + "\n")
                
        with open(val_path, "w", encoding="utf-8") as f:
            for s in val_samples:
                facts_str = json.dumps(s["facts"])
                f.write(json.dumps({"prompt": s["prompt"], "facts": facts_str, "target": s["target"]}) + "\n")
                
        print(f"[x] Generated {len(train_samples)} training samples saved to {train_path}")
        print(f"[x] Generated {len(val_samples)} validation samples saved to {val_path}")
        return train_path, val_path


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    generator = AtmaCoreDataGenerator()
    generator.generate_and_save(base_dir, num_samples=10000)
