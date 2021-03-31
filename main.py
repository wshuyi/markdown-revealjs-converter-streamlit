import streamlit as st 
from io import StringIO
import os
from pathlib import Path
import base64
from zipfile import ZipFile
import shutil


from roam_md_converter import RoamMDConverter
from revealjs_converter import MarkdownRevealjsConverter

def get_all_file_paths(directory):
  
    # initializing empty file paths list
    file_paths = []
  
    # crawling through directory and subdirectories
    for root, directories, files in os.walk(directory):
        for filename in files:
            # join the two strings in order to form the full filepath.
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)
  
    # returning all file paths
    return file_paths        

st.title("Markdown Revealjs Exporter")
st.write("Author: [Shuyi Wang](https://twitter.com/wshuyi)")

md_fname = "input.md"
revealjs_export_dir = "revealjs_export"
markdown_export_dir = "markdown_temp_export"
out_zip = "output.zip"


config = dict()
config["path"] = "config.json"

config["author"] = st.text_input("Author Name:", "王树义")

in_text = st.text_area("Your Indented Markdown goes here: ", "")
with open(md_fname, 'w') as f:
    f.write(in_text)

if st.button("convert!"):
    roam_converter = RoamMDConverter(md_fname, **config)
    roam_converter.convert(roam_doc_mode="slide")
    myconverter = MarkdownRevealjsConverter(roam_converter.output_md, **config) 
    myconverter.convert()

    file_paths = get_all_file_paths(revealjs_export_dir)

    with ZipFile(out_zip, "w") as zip:
        for fname in file_paths:
            zip.write(fname)

    with open(out_zip, "rb") as f:
        bytes = f.read()
        b64 = base64.b64encode(bytes).decode()
        href = f'<a href="data:file/zip;base64,{b64}" download=\'{out_zip}\'>\
            Click to download the zip file\
        </a>'

    shutil.rmtree(revealjs_export_dir)
    shutil.rmtree(markdown_export_dir)
    os.remove(out_zip)

    st.markdown(href, unsafe_allow_html=True)