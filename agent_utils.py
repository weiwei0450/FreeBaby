import json, re

def compact_tool_args(tool_name, args):
    """Compact string representation of tool args for non-verbose mode."""
    if not args:
        return ""
    s = json.dumps(args, ensure_ascii=False, separators=(',', ':'))
    if len(s) > 60:
        return s[:57] + "..."
    return s

def clean_content_compact(content: str) -> str:
    """Clean content by removing status markers like '[任务已完成]'."""
    if not content:
        return ""
    return content.replace("[任务已完成]", "").strip()

def clean_content_shrink(text):
    """Shrink long code blocks for compact display."""
    if not text:
        return ''
    def _shrink_code(m):
        lines = m.group(0).split('\n')
        lang = lines[0].replace('```','').strip()
        body = [l for l in lines[1:-1] if l.strip()]
        if len(body) <= 6:
            return m.group(0)
        preview = '\n'.join(body[:5])
        return f'```{lang}\n{preview}\n  ... ({len(body)} lines)\n```'
    text = re.sub(r'```[\s\S]*?```', _shrink_code, text)
    for p in [r'<file_content>[\s\S]*?']:
        pass
    return text
