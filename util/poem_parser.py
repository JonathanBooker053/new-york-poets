import re
import json


def is_footer_line(line):
    """
    Returns True if the line is a footer (i.e. a page number)
    which is just 1 to 4 digits.
    """
    return bool(re.match(r'^\d{1,4}$', line.strip()))


def remove_non_date_footers(text):
    """
    Removes trailing footer lines that are not valid date lines.
    """
    lines = text.splitlines()
    # Remove trailing lines that are just page numbers.
    while len(lines) > 1 and is_footer_line(lines[-1]):
        lines.pop()
    return "\n".join(lines)


def extract_date(text):
    """
    Searches the last line of the text for a valid date (a 4-digit year or two 4-digit years separated by 'or' or '-').
    If found, removes that line and returns the text and the date string.
    """
    lines = text.splitlines()
    if lines:
        candidate = lines[-1].strip()
        pattern = re.compile(r'^(19|20)\d{2}(?:\s*(?:or|-)\s*(19|20)\d{2})?$')
        m = pattern.match(candidate)
        if m:
            lines.pop()
            if "or" in candidate or "-" in candidate:
                years = re.split(r'\s*(?:or|-)\s*', candidate)
                years = [y.strip() for y in years if y.strip()]
                return "\n".join(lines), ", ".join(years)
            else:
                return "\n".join(lines), candidate
    return text, None


def remove_leading_empty_lines(text):
    """
    Removes empty lines from the beginning of the text.
    """
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines)


def parse_extracted_text(file_path):
    """
    Reads the full extracted text (which uses form-feed characters to separate pages),
    processes the pages to extract poem titles, content, and dates, and returns a list of
    dictionaries (each with "title", "content", and "date" keys).

    The function assumes that the first non-empty line (ignoring footer lines) on a page is a header.
    Pages that contain a header exactly equal to "Poem" (case-insensitive) always start a new poem.
    A poem is finalized (i.e. ends) when a valid date is detected at the end of its content.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # Split the text into pages using the form feed character.
    pages = full_text.split('\f')
    poems = []
    current_title = None
    current_poem_lines = []
    header_word_threshold = 5  # heuristic for determining if a candidate header is part of the poem

    for page in pages:
        lines = page.splitlines()
        if not lines:
            continue

        # Find candidate header: first non-empty line that is not a footer.
        candidate_header = None
        for line in lines:
            if line.strip() and not is_footer_line(line):
                candidate_header = line.strip()
                break

        if candidate_header:
            normalized_candidate = candidate_header.lower()
            # If the header is exactly "poem", always treat it as a new poem.
            if normalized_candidate == "poem":
                if current_title is not None:
                    # Finalize the previous poem.
                    poem_text = "\n".join(current_poem_lines).rstrip()
                    poem_text = remove_non_date_footers(poem_text)
                    poem_text, date = extract_date(poem_text)
                    poem_text = remove_leading_empty_lines(poem_text)
                    poems.append({"title": current_title.title(), "content": poem_text})
                    current_poem_lines = []
                current_title = candidate_header
                header_found = False
                for line in lines:
                    if not header_found and line.strip().lower() == normalized_candidate:
                        header_found = True
                        continue
                    if header_found and not is_footer_line(line):
                        current_poem_lines.append(line)
            else:
                # For non-"poem" headers:
                if current_title is None:
                    # Start a new poem.
                    current_title = candidate_header
                    header_found = False
                    for line in lines:
                        if not header_found and line.strip().lower() == normalized_candidate:
                            header_found = True
                            continue
                        if header_found and not is_footer_line(line):
                            current_poem_lines.append(line)
                else:
                    # There is an active poem.
                    if len(candidate_header.split()) > header_word_threshold:
                        # Assume it is a continuation.
                        filtered_lines = [l for l in lines if not is_footer_line(l)]
                        current_poem_lines.extend(filtered_lines)
                    else:
                        # Compare candidate header with current title.
                        if current_title.strip().lower() == normalized_candidate:
                            header_found = False
                            for line in lines:
                                if not header_found and line.strip().lower() == normalized_candidate:
                                    header_found = True
                                    continue
                                if header_found and not is_footer_line(line):
                                    current_poem_lines.append(line)
                        else:
                            # New header differs: finalize current poem.
                            poem_text = "\n".join(current_poem_lines).rstrip()
                            poem_text = remove_non_date_footers(poem_text)
                            poem_text, date = extract_date(poem_text)
                            poem_text = remove_leading_empty_lines(poem_text)
                            poems.append({"title": current_title.title(), "content": poem_text})
                            current_poem_lines = []
                            current_title = candidate_header
                            header_found = False
                            for line in lines:
                                if not header_found and line.strip().lower() == normalized_candidate:
                                    header_found = True
                                    continue
                                if header_found and not is_footer_line(line):
                                    current_poem_lines.append(line)
        else:
            # If no header on the page, treat all non-footer lines as continuation.
            filtered_lines = [l for l in lines if not is_footer_line(l)]
            current_poem_lines.extend(filtered_lines)

        # Check if the current poem ends with a valid date.
        if current_title is not None and current_poem_lines:
            temp_text = "\n".join(current_poem_lines).rstrip()
            temp_text = remove_non_date_footers(temp_text)
            temp_text, date = extract_date(temp_text)
            if date:
                temp_text = remove_leading_empty_lines(temp_text)
                poems.append({"title": current_title.title(), "content": temp_text})
                current_title = None
                current_poem_lines = []

    # Finalize any remaining poem.
    if current_title is not None:
        poem_text = "\n".join(current_poem_lines).rstrip()
        poem_text = remove_non_date_footers(poem_text)
        poem_text, date = extract_date(poem_text)
        poem_text = remove_leading_empty_lines(poem_text)
        poems.append({"title": current_title.title(), "content": poem_text})

    return poems


def main():
    input_file = "util/data/extracted.txt"  # Your input extracted text file.
    output_file = "util/data/parsed_poems.json"  # The final JSON output file.
    poems = parse_extracted_text(input_file)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(poems, f, ensure_ascii=False, indent=2)
    print(f"Parsed poems have been saved to '{output_file}'.")


if __name__ == "__main__":
    main()