import re

path = 'backend/app/services/risk.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to replace `render_pdf_report`, `_simple_pdf`, and `_wrap_report_line` (or leave it as is).
# We will use regex to find everything from `def render_pdf_report` to the end of the file.

new_code = """
def render_pdf_report(report: dict[str, Any]) -> bytes:
    import re
    text = render_markdown_report(report)
    lines = []
    for raw_line in text.splitlines():
        # Strip markdown headers (# ) only at the beginning of the line
        line = re.sub(r'^#+\\s*', '', raw_line).strip()
        if not line:
            lines.append("")
        else:
            lines.extend(_wrap_report_line(line, width=92))
    return _simple_pdf(lines)


def _wrap_report_line(line: str, *, width: int) -> list[str]:
    if len(line) <= width:
        return [line]
    words = line.split()
    wrapped: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
            continue
        if current:
            wrapped.append(current)
        current = word[:width]
    if current:
        wrapped.append(current)
    return wrapped


def _pdf_escape(value: str) -> str:
    return value.replace("\\\\", "\\\\\\\\").replace("(", "\\\\(").replace(")", "\\\\)")


def _simple_pdf(lines: list[str]) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
    ]
    
    # We will build page objects and streams
    # Page index starts from 1, but object index mapping:
    # 1: Catalog
    # 2: Pages
    # 3: Font
    # 4: Page 1, 5: Stream 1, 6: Page 2, 7: Stream 2...
    
    font_obj_id = 3
    objects.append(b"") # Placeholder for Pages (object 2)
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>") # Object 3
    
    kids = []
    page_count = 0
    LINES_PER_PAGE = 45
    
    for page_start in range(0, max(1, len(lines)), LINES_PER_PAGE):
        page_lines = lines[page_start:page_start + LINES_PER_PAGE]
        
        content_lines = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
        for index, line in enumerate(page_lines):
            if index:
                content_lines.append("T*")
            if line:
                content_lines.append(f"({_pdf_escape(line)}) Tj")
            else:
                # empty line, just move text position down without printing
                pass
        content_lines.append("ET")
        
        stream = "\\n".join(content_lines).encode("latin-1", errors="replace")
        
        page_obj_id = len(objects) + 1
        stream_obj_id = page_obj_id + 1
        kids.append(f"{page_obj_id} 0 R")
        page_count += 1
        
        page_obj = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_obj_id} 0 R >> >> /Contents {stream_obj_id} 0 R >>".encode('ascii')
        stream_obj = b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\\nstream\\n" + stream + b"\\nendstream"
        
        objects.append(page_obj)
        objects.append(stream_obj)
        
    pages_obj = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {page_count} >>".encode('ascii')
    objects[1] = pages_obj
    
    pdf = bytearray(b"%PDF-1.4\\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\\nendobj\\n")
        
    xref_offset = len(pdf)
    pdf.extend(f"xref\\n0 {len(objects) + 1}\\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \\n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \\n".encode("ascii"))
        
    pdf.extend(f"trailer\\n<< /Size {len(objects) + 1} /Root 1 0 R >>\\nstartxref\\n{xref_offset}\\n%%EOF\\n".encode("ascii"))
    return bytes(pdf)
"""

# Replace in content
import re
new_content = re.sub(r'def render_pdf_report\(.*?$', new_code.strip(), content, flags=re.DOTALL | re.MULTILINE)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
