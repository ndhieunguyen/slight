import poe
import logging
import re
import json

query_template = """{
"input_text": "[[QUERY]]",
"output_format": "json",
"json_structure": {
    "slides":"{{presentation_slides}}"
    }
}"""

fodbidden_chars = [
    "/",
    "\\",
    '"',
    "'",
    "*",
    ":",
    ";",
    "-",
    "?",
    "[",
    "]",
    "(",
    ")",
    "~",
    "!",
    "$",
    "{",
    "}",
    ">",
    "<",
    "#",
    "@",
    "&",
    "|",
    " ",
    "\t",
    "\n",
]


def query_from_API(query: str, token: str, bot_name: str = "chinchilla") -> str:
    response = ""
    try:
        poe.logger.setLevel(logging.INFO)
        client = poe.Client(token)

        for chunk in client.send_message(bot_name, query, with_chat_break=True):
            word = chunk["text_new"]
            response += word

        # delete the 3 latest messages, including the chat break
        client.purge_conversation(bot_name, count=3)
    except Exception as e:
        pass
    return response


def create_query(text: str, type_of_text: int, n_slides: int = 10, n_words_per_slide: int = 55, query=query_template):
    if type_of_text == 0:  # topic
        topic_query = (
            f"Generate a {n_slides} slide presentation for the topic. Produce {n_words_per_slide-5} to {n_words_per_slide+5} words per slide. "
            + text
            + ". Each slide should have a  {{header}}, {{content}}. The final slide should be a thank-you-slide, seperated by a newline character. Return as JSON, only JSON, not the code to generate JSON."
        )
    else:  # file content
        topic_query = (
            f"Generate a {n_slides} slide presentation from the document provided. Produce {n_words_per_slide-5} to {n_words_per_slide+5} words per slide. "
            + ". Each slide should have a  {{header}}, {{content}}. The first slide should only contain the short title. The final slide should be some discussion questions, seperated by a newline character. Return as JSON, only JSON, not the code to generate JSON."
            + " Here is the document: \n"
            + text
        )
    return query.replace("[[QUERY]]", topic_query)


def create_file_name(text: str, token: str, bot_name: str = "chinchilla"):
    if len(text) < 30:  # topic
        file_name = text
    else:  # file content
        query = f'summarize this text to make it become the file name of a presentation file "{text}"'
        file_name = query_from_API(query, token, bot_name)

    for forbidden_char in fodbidden_chars:
        if forbidden_char in file_name:
            file_name = file_name.replace(forbidden_char, "_")
    return file_name


def create_content_from_repsponse(response: str):
    def _create_content_from_json(response):
        match = re.search(r"{(.*?)]\n}", response, re.DOTALL)
        if match:  # response has json inside
            content_json = match.group(0)
            try:
                content_json = json.loads(content_json)
                return content_json
            except:
                return None

    def _create_content_from_python_code(response):
        match_pycode = re.search(r"```python(.*?)\)\n```", response, re.DOTALL)
        if not match_pycode:
            return None
        py_code = match_pycode.group(0)

        match_content = re.search(r"content =(.*?)]", py_code, re.DOTALL)
        if not match_content:
            return None

        content_str = match_content.group(0)
        contents = content_str.split(r"=")[1]
        contents_list = re.findall('"(.*)",', contents)

        match_header = re.search(r"header =(.*?)]", response, re.DOTALL)
        if not match_header:
            return None
        headers_str = match_header.group(0)
        headers_list = re.findall('"Slide \d+: (.+)"', headers_str)

        slides_json = {}
        slides_json["slides"] = []

        for header, content in zip(headers_list, contents_list):
            pair = {}
            pair["header"] = header
            pair["content"] = content
            slides_json["slides"].append(pair)

        return slides_json

    content_json = _create_content_from_json(response)
    if content_json is None:
        content_json = _create_content_from_python_code(response)

    return content_json


def process_header(title: str):
    index = title.find(":")
    return title[index + 1 :]
