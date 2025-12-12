from pathlib import Path


def json_to_md(data: dict) -> str:
    """
    Convert the given JSON dict into a clean Markdown documentation.
    """

    md_output = ["# API Route Documentation\n"]

    # Loop each top-level group like "users", "places"
    for group_name, group_data in data.items():
        md_output.append(f"## {group_name.capitalize()}\n")
        md_output.append(f"**Base Path:** `{group_data.get('path', '')}`\n")
        md_output.append(f"**Handler:** `{group_data.get('handler', '')}`\n")
        md_output.append(f"**Handler File:** `{group_data.get('handler_file_info', '')}`\n")

        md_output.append("\n### Endpoints\n")

        # Loop keys inside each group
        for key, value in group_data.items():
            # Skip meta fields
            if key in ("path", "handler", "handler_file_info"):
                continue

            md_output.append(f"#### `{value.get('sub_path', '')}`\n")
            md_output.append(f"- **Method:** `{value.get('httpMethod', '')}`")
            md_output.append(f"- **Middlewares / Handlers:**")

            handlers = value.get("handlerFunc", [])
            if isinstance(handlers, list):
                for h in handlers:
                    md_output.append(f"  - `{h}`")
            else:
                md_output.append(f"  - `{handlers}`")

            md_output.append("")  # blank line

        md_output.append("\n---\n")

    return "\n".join(md_output)

def convert_file(testJson):

    markdown = json_to_md(testJson)

    # Save output to file
    output_path = Path("routes.md")
    output_path.write_text(markdown)

    print(f"Markdown generated → {output_path.resolve()}")



if __name__ == "__main__":
    convert_file(testJson={})

