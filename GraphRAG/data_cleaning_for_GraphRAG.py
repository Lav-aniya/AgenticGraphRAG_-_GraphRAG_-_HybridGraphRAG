
import fitz
import json
import re
from collections import Counter
from datetime import datetime



path = "/content/drive/MyDrive/Cancer_Monographs_GraphRAG/"
doc_path = path + "Cancer_Monographs-new.pdf"
#doc = fitz.open(doc_path)




def detect_chapters(doc):
  chapter_map = [
      {"chapter": 1, "title": "Population and Cancer Incidence", "start_page": 28},
      {"chapter": 2, "title": "Leading sites of Cancer", "start_page": 36},
      {"chapter": 3, "title": "Breast Cancer", "start_page": 54},
      {"chapter": 4, "title": "Cervical Cancer Research", "start_page": 79},
      {"chapter": 5, "title": "Cancer Research in North-East", "start_page": 112},
      {"chapter": 6, "title": "Tobacco Related Cancers", "start_page": 137},
      {"chapter": 7, "title": "Prostrate Cancer", "start_page": 186},
      {"chapter": 8, "title": "Diet and Cancer", "start_page": 195},
      {"chapter": 9, "title": "Extramural Research Activities", "start_page": 201}
  ]

  for i in range(len(chapter_map) - 1):
    chapter_map[i]["end_page"] = chapter_map[i + 1] ["start_page"] - 1

  chapter_map[-1]["end_page"] = len(doc)

  return chapter_map

def detect_common_headers_footers(doc, sample_pages=20, threshold=0.5):
  header_lines = Counter()
  footer_lines = Counter()

  start_sample = max(10, len(doc) // 4)
  end_sample = min(len(doc) - 10, start_sample + sample_pages)

  num_sampled = 0
  for page_num in range(start_sample, end_sample):
    lines = doc[page_num].get_text().split('\n')
    if len(lines) > 2:
      num_sampled += 1
      for line in lines:
        if line.strip():
          header_lines[line.strip()] += 1
          break
      for line in reversed(lines):
        if line.strip():
          footer_lines[line.strip()] += 1
          break


  min_count = int(num_sampled * threshold)
  common_headers = {line for line, count in header_lines.items() if count >= min_count}
  common_footers = {line for line, count in footer_lines.items() if count >= min_count}

  common_footers.add("icma")
  footer_pattern = re.compile(r"Cancer Monograph\s*\d+")
  for page in doc:
    text = page.get_text()
    for match in footer_pattern.findall(text):
      common_footers.add(match.strip())


  return common_headers, common_footers

def clean_page_text(text, common_headers, common_footers):
  # CLeans the raw text of a single page

  lines = text.split('\n')

  cleaned_lines = [
      line for line in lines
      if line.strip() not in common_headers and line.strip() not in common_footers
      ]

  text = '\n'.join(cleaned_lines)
  text = re.sub(r'(\w+)\s*-\s*\n\s*(\w+)', r'\1\2', text )        # Removes Hyphen across lines
  text = re.sub(r'(?<!\n)\n(?!\n|\s*.|\s*\d+\.\s)', ' ', text)    # Merge broken lines into paragraph, it will join lines unless they look like a list item, new para., or headings

  text = re.sub(r'\s+', ' ', text).strip()                        # Normalize whitespace

  return text


def format_tables_as_json(table_data):
# Converts extracted table data into a JSON
  if not table_data or len(table_data) < 1:
    return None

  headers = table_data[0]
  cleaned_headers = [
      re.sub(r'[\n\r]+', ' ', h).strip() if h else f"column-{i}"
      for i, h in enumerate(headers)
  ]

  data = []
  for row in table_data[1:]:
    row_data = {}
    for i, header in enumerate(cleaned_headers):
      if i < len(row):
        cell = row[i]
        clean_cell = re.sub(r'[n\r]+', ' ', cell).strip() if cell else""
        row_data[header] = clean_cell
      else:
        row_data[header] = ""

    if any(row_data.values()):
      data.append(row_data)

  return data if data else None


def main():
  pdf_path = doc_path
  output_json_path = path + "cleaned.json"
  monograph_data = []

  with fitz.open(pdf_path) as doc:
    chapters = detect_chapters(doc)
    common_headers, common_footers = detect_common_headers_footers(doc)

    print("detected common headers:", common_headers)
    print("detected common footers:", common_footers)
    print(f"detected {len(chapters)} chapters")

    for chapter_info in chapters:
      print(f"Processing chapter {chapter_info['chapter']}: {chapter_info['title']}...")

      chapter_text = ""
      chapter_tables = []

      start_page_index = chapter_info['start_page'] - 1
      end_page_index = chapter_info['end_page'] - 1

      for page_num in range(start_page_index, min(end_page_index + 1, len(doc))):
        page = doc[page_num]

        # Clean the main text
        raw_text = page.get_text()
        if raw_text:
          cleaned_text = clean_page_text(raw_text, common_headers, common_footers)
          chapter_text += cleaned_text + " "

        # Extract tables
        found_tables = page.find_tables()
        if found_tables:
          for i, table_obj in enumerate(found_tables):
            table_data = table_obj.extract()
            formatted_table = format_tables_as_json(table_data)
            if formatted_table:
              chapter_tables.append({
                  "table_name": f"Table on Page { page.number + 1}, Index {i}",
                  "data": formatted_table
              })


      monograph_data.append({
          "chapter": chapter_info["chapter"],
          'title': chapter_info["title"],
          "content": chapter_text.strip(),
          "tables": chapter_tables
      })

  output = {
      "source_file": pdf_path,
    # "extracted_on": datetime.now().strftime("%y-%m-%d"),
      "chapters": monograph_data
  }

  # Save to JSON
  with open(output_json_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii = False)


  print(f"\n extraction done")


if __name__ == "__main__":
  main()




