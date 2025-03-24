import os
import openai
import re
from flask import Flask, render_template_string, request
from dotenv import load_dotenv

# 1. Load environment variables from .env (if you’re storing your API key there).
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 2. Optionally set your fine-tuned model ID via environment variable (or hard-code below).
FINETUNED_MODEL = os.getenv("MODEL_ID")

app = Flask(__name__)


def clean_poem_output(poem):
    """
    Removes any repeated or extraneous lines, especially if the model repeats the prompt
    or includes 'Title:' / 'Prompt:' text again. Adjust the regex or logic as needed.
    """
    # Example: remove lines starting with "Title: Poem" or repeated user prompt lines.
    # You can customize or expand this pattern based on your model's actual responses.

    # 1. Split poem into lines
    lines = poem.split("\n")
    cleaned_lines = []
    for line in lines:
        # Remove lines that might repeat the prompt or contain "User Prompt"
        if line.lower().startswith("title:") or "User Prompt" in line:
            continue
        cleaned_lines.append(line)

    # 2. Rejoin lines
    cleaned_poem = "\n".join(cleaned_lines).strip()

    return cleaned_poem


def generate_poem(prompt):
    """
    Uses the fine-tuned model to generate a poem based on the user's prompt.
    We instruct the model to only return the poem text.
    """
    system_message = (
        "You are a creative poem generator, fine-tuned to write in Frank O’Hara’s style. "
        "Only return the poem text—do not repeat the prompt or add extra headings."
    )
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]
    try:
        response = openai.ChatCompletion.create(
            model=FINETUNED_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        raw_poem = response["choices"][0]["message"]["content"].strip()
        poem = clean_poem_output(raw_poem)
        return poem
    except Exception as e:
        return f"Error: {e}"


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    user_prompt = ""
    if request.method == "POST":
        user_prompt = request.form.get("prompt", "")
        if user_prompt:
            result = generate_poem(user_prompt)
    return render_template_string("""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>Frank O’Hara Poem Generator</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 2em; }
          h1 { color: #333; }
          pre { background-color: #f4f4f4; padding: 1em; white-space: pre-wrap; }
          input[type="text"] { width: 80%; padding: 0.5em; font-size: 1em; }
          input[type="submit"] { padding: 0.5em 1em; font-size: 1em; }
        </style>
      </head>
      <body>
        <h1>Frank O’Hara Poem Generator</h1>
        <form method="post">
          <label for="prompt">Enter your poem prompt:</label><br>
          <input type="text" id="prompt" name="prompt" value="{{ user_prompt }}"><br><br>
          <input type="submit" value="Generate Poem">
        </form>
        {% if result %}
          <h2>Generated Poem:</h2>
          <pre>{{ result }}</pre>
        {% endif %}
      </body>
    </html>
    """, result=result, user_prompt=user_prompt)


if __name__ == "__main__":
    # If you want to run in production, set debug=False or use a production server (e.g., Gunicorn)
    app.run(debug=True)