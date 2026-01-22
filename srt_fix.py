

from datetime import datetime
import re

RTL_MARK = '\u200F'  # Right-To-Left Mark

def parse_time(time_str):
    return datetime.strptime(time_str, "%H:%M:%S,%f")

def format_time(time_obj):
    return time_obj.strftime("%H:%M:%S,%f")[:-3]

def fix_overlaps_and_rtl(srt_content):
    entries = []
    blocks = re.split(r'\n(?=\d+\n)', srt_content.strip())

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        index = lines[0]
        time_line = lines[1]
        text_lines = lines[2:]

        start_str, end_str = time_line.split(" --> ")
        start = parse_time(start_str)
        end = parse_time(end_str)

        # Prepend RTL marker to each line of text
        text_lines = [RTL_MARK + line for line in text_lines]
        text = '\n'.join(text_lines)

        entries.append({
            "index": index,
            "start": start,
            "end": end,
            "text": text
        })

    # Adjust end times to prevent overlaps
    for i in range(len(entries) - 1):
        current = entries[i]
        next_entry = entries[i + 1]
        if current["end"] > next_entry["start"]:
            current["end"] = next_entry["start"]

    # Rebuild SRT content
    fixed_srt = ""
    for entry in entries:
        fixed_srt += f"{entry['index']}\n{format_time(entry['start'])} --> {format_time(entry['end'])}\n{entry['text']}\n\n"

    return fixed_srt.strip()

# Example usage
input_file = r"C:\Users\mturky\Desktop\to ssd\Summer.Snow.2014.1080p.WEBRip.x264.AAC-LAMA_bad.srt"
output_file = r"C:\Users\mturky\Desktop\to ssd\Summer.Snow.2014.1080p.WEBRip.x264.AAC-LAMA_fix.srt"


with open(input_file, 'r', encoding='utf-8') as f:
    srt_data = f.read()

fixed_srt = fix_overlaps_and_rtl(srt_data)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(fixed_srt)

print("Overlaps fixed and RTL direction added. Output saved to:", output_file)
