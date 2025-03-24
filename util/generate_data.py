import json
import openai
import time
import os
import sys
import random
from dotenv import load_dotenv

INPUT_FILE = "util/data/parsed_poems.json"  # Input JSON file with poems.
TRAINING_FILE = "util/data/training_data.jsonl"  # Output JSONL file for fine-tuning.
VALIDATION_FILE = "util/data/validation_data.jsonl" # Output JSONL file for validation.

VALIDATION_RATIO = 0.2
NUM_PROMPTS_PER_POEM = 5  # Generate 5 (or more) prompt variants per poem.

# Load environment variables from .env (make sure it contains OPENAI_API_KEY)
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


# Load poems from a JSON file (each poem must have "title" and "content")
def load_poems(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


# Save a list of JSON objects to a JSONL file (one JSON object per line)
def save_jsonl(lines, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        for obj in lines:
            json_line = json.dumps(obj, ensure_ascii=False)
            f.write(json_line + "\n")


# Updated meta-prompt for generating creative prompts
# This prompt instructs the model to produce two types of prompts: one detailed and one simple.
META_PROMPT = """
<reasoning>
- Simple Change: yes
- Reasoning: no
- Structure: yes
- Examples: yes
- Complexity: 1
- Specificity: 1
- Prioritization: prompt clarity and variety
- Conclusion: Generate two creative prompts for an AI poem generator: one detailed (rich in style, tone, and imagery) and one simple (direct and concise). Separate the two outputs with a newline.
</reasoning>
Generate two creative prompts to guide an AI poem generator:
1. A detailed prompt with rich instructions on style, tone, and imagery.
2. A simple, direct prompt that states the task plainly.
Do not include any extra commentary. Separate the two prompts with a newline.
""".strip()


def generate_mete_prompt(poem_title, poem_text):
    """
    Generates creative prompts using the meta-prompt.
    For diversity, each call randomly varies the temperature (e.g., 0.5, 0.7, or 0.9).
    The API is expected to return two prompts separated by a newline; we then randomly select one.
    """
    task_description = (
        f"Poem Title: {poem_title}\n"
        f"Poem Content:\n{poem_text}\n\n"
        "Generate two creative prompts that instruct an AI poem generator to compose a poem similar in style, tone, and imagery to the above. "
        "The first prompt should be detailed and elaborate, while the second should be simple and direct (e.g., 'Write a poem about being gay in the 1960s'). "
        "Separate the two prompts with a newline."
    )
    messages = [
        {"role": "system", "content": META_PROMPT},
        {"role": "user", "content": task_description}
    ]

    # Randomize temperature to encourage different styles (simple vs. detailed)
    temperature = random.choice([0.5, 0.7, 0.9])

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-2024-08-06",  # Adjust model if necessary
            messages=messages,
            temperature=temperature,
            max_tokens=1500
        )
        result_text = response["choices"][0]["message"]["content"].strip()
        # Split the result into two prompts (if available)
        prompts = result_text.split("\n", 1)
        if len(prompts) < 2:
            # If the API did not return two prompts, use the result as is.
            return result_text
        # Randomly choose one of the two prompts.
        selected_prompt = random.choice(prompts)
        return selected_prompt.strip()
    except Exception as e:
        print(f"Error generating Mete-Prompt for poem '{poem_title}': {e}")
        sys.exit(1)


def format_chat_finetune_examples(poem, num_variants):
    """
    For a given poem, generate multiple training examples.
    Each example is a chat conversation containing:
      - A system message instructing the model to generate a poem in the desired style.
      - A user message with a generated creative prompt.
      - An assistant message with the original poem (title and content).
    Returns a list of these examples.
    """
    title = poem.get("title", "Untitled").strip()
    content = poem.get("content", "").strip()
    examples = []

    for i in range(num_variants):
        generated_prompt = generate_mete_prompt(title, content)
        system_msg = {
            "role": "system",
            "content": "You are a creative poem generator. Generate a poem in the style of Frank O’Hara based on the instructions provided."
        }
        user_msg = {
            "role": "user",
            "content": generated_prompt
        }
        assistant_msg = {
            "role": "assistant",
            "content": f"Title: {title}\nContent:\n{content}"
        }
        example = {"messages": [system_msg, user_msg, assistant_msg]}
        examples.append(example)
        print(f"Generated prompt variant {i + 1} for poem: {title}")
        time.sleep(1)  # Delay to avoid rate limits
    return examples


def main():
    """
    Process the input JSON file containing poems.
    For each poem, generate multiple training examples (each with a unique prompt),
    then randomly split the total examples into training and validation sets based on VALIDATION_RATIO.
    The training examples are saved to OUTPUT_FILE and the validation examples to VALIDATION_FILE.
    """
    poems = load_poems(INPUT_FILE)
    all_examples = []

    for poem in poems:
        examples = format_chat_finetune_examples(poem, NUM_PROMPTS_PER_POEM)
        all_examples.extend(examples)
        print(f"Processed poem: {poem.get('title', 'Untitled')}")

    # Shuffle the examples for a random split
    random.shuffle(all_examples)
    n_validation = int(len(all_examples) * VALIDATION_RATIO)
    validation_examples = all_examples[:n_validation]
    training_examples = all_examples[n_validation:]

    save_jsonl(training_examples, TRAINING_FILE)
    save_jsonl(validation_examples, VALIDATION_FILE)

    print(f"Conversion complete. Training data saved to '{TRAINING_FILE}' with {len(training_examples)} examples.")
    print(f"Validation data saved to '{VALIDATION_FILE}' with {len(validation_examples)} examples.")


if __name__ == "__main__":
    main()