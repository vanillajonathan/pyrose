def markdown_to_pango(markdown: str) -> str:
    """Convert Markdown to Pango.

    Args:
      markdown: A string in Markdown format.

    Returns:
      A string in Pango markup format.
    """
    lines = markdown.splitlines(keepends=True)
    pango = ""
    code_block = ""
    in_code_block = False

    for line in lines:
        if line.startswith("```"):
            language = line[3:]
            line = ""
            in_code_block = not in_code_block

        if in_code_block:
            code_block += line
            continue
        else:
            if code_block:
                pango += f"<tt>{syntax_highlight(language, code_block)}</tt>"
                code_block = ""
                language = None

        if line.startswith("###"):
            line = f"<span size='large'>{line.lstrip('# ')}</span>"
        elif line.startswith("##"):
            line = f"<span size='x-large'>{line.lstrip('# ')}</span>"
        elif line.startswith("#"):
            line = f"<span size='xx-large'>{line.lstrip('# ')}</span>"
        elif line.startswith("- "):
            line = "•" + line[1:]

        pango += line

    return pango


def syntax_highlight(language: str, code: str) -> str:
    if language == "python" or language == "python3":
        code = syntax_highlight_python(code)
    return code


def syntax_highlight_python(code: str) -> str:
    return code
