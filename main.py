from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from src.slide import *
from src.content import *
import random
import glob

TEMPLATE_FOLDER = r"templates"
TEMPLATE_NAMES = os.listdir(TEMPLATE_FOLDER)


class Input(BaseModel):
    text: str
    mode: int = 0
    n_slides: Optional[int] = 10
    n_words_per_slide: Optional[int] = 70
    api_token: str = None


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/generate/")
async def generate(opt: Input):
    # ======================== Clear previous presentation ================================
    pptx_files = glob.glob("*.pptx")
    for pptx_file in pptx_files:
        os.remove(pptx_file)
    tmp_folder = r"tmp_folder"
    if os.path.exists(tmp_folder):
        shutil.rmtree(tmp_folder, ignore_errors=True)
    os.makedirs(tmp_folder)

    POE_API_KEY = opt.api_token if opt.api_token else os.environ["poe_api_key"]
    # ======================== Prepare the content for presentation ================================
    text_query = create_query(
        text=opt.text,
        type_of_text=opt.mode,
        n_slides=opt.n_slides,
        n_words_per_slide=opt.n_words_per_slide,
    )
    response = query_from_API(query=text_query, token=POE_API_KEY)
    content = create_content_from_repsponse(response)

    # ======================== Prepare the template for presentation ================================
    TEMPLATE_PPTX = os.path.join(TEMPLATE_FOLDER, random.choice(TEMPLATE_NAMES))
    template = prepare_template(template_path=TEMPLATE_PPTX)

    # ======================== Create presentation ================================
    file_name = create_file_name(text=opt.text, token=POE_API_KEY)
    font_file = os.path.join("fonts", "Calibri Regular.ttf")
    output_pptx_path = create_slide(
        content=content,
        template=template,
        file_name=file_name,
        tmp_folder=tmp_folder,
        font_file=font_file,
    )
    shutil.rmtree(tmp_folder, ignore_errors=True)

    return FileResponse(
        output_pptx_path,
        filename=output_pptx_path.split("/")[-1],
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
