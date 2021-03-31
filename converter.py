import os
from pathlib import Path
import json
import re
import time
import datetime
import shutil
import requests
import urllib


class MarkdownConverter():
    def __init__(self, *args, **kwargs):
        # special for streamlit: author name
        self.author = kwargs['author']
        # all the sensitive information are in the json file
        self.load_json_config(kwargs['path'])
        # get the path to find the code (this python file)
        self.code_dir = Path(__file__).absolute().parent
        # get the source md
        self.source_md_fname = Path(args[0]).expanduser().absolute() 
        if self.source_md_fname.suffix == ".textbundle":
            #text bundle:
            self.textbundle_tmp_create()
            markdown_suffix_list = list(self.source_md_fname.glob("*.markdown"))
            md_suffix_list = list(self.source_md_fname.glob("*.md"))
            self.source_md_fname = (markdown_suffix_list + md_suffix_list)[0]
        # get the working dir
        self.working_folder = Path(self.source_md_fname).parent
        # read the source markdown in
        with open(self.source_md_fname) as f:
            self.md_content = f.read()
        # dir the download images
        self.download_dir = self.working_folder / 'downloaded_images'
        

        try:
            # receive the specified output filename
            self.output_md = kwargs["out_fname"]
        except:
            md_output_dir = Path(self.config["markdown_export_dir"]).expanduser().absolute()
            if md_output_dir.exists():
                shutil.rmtree(md_output_dir)
                md_output_dir.mkdir()
            self.output_md = f"{str(md_output_dir)}/output.md"
            self.md_output_dir = md_output_dir


    def load_json_config(self, json_path):
        with open(json_path) as f:
            self.config = json.load(f)

    def textbundle_tmp_create(self):
        temp_dir = Path(self.config["temp_dir"]).expanduser().absolute() / "textbundle_temp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        # create output folder
        temp_dir.mkdir()
        shutil.copytree(self.source_md_fname, temp_dir/"temp.textbundle")
        self.source_md_fname = temp_dir/"temp.textbundle"


    def show_md(self, md_fname = None):
        # open md in editor, normally vscode
        if not(md_fname):
            md_fname = self.output_md
        cmd = "open '{}'".format(md_fname)
        os.system(cmd)

    def convert_image_link_to_absolute_ones(self):
        # relative image links to absolute ones
        data = self.md_content
        relative_links = self.get_image_links(data)
        # no need to handle duplicate ones
        relative_links = self.remove_duplicate_element_in_list(relative_links)
        for rel_link in relative_links:
            abs_link = self.get_absolute_path(rel_link)
            data = data.replace(str(rel_link), str(abs_link))
        self.md_content = data

    def get_absolute_path(self, link):
        # image helper of markdown preview plus for vscode bug:
        if str(link).startswith('/assets/'):
            link = Path(str(link)[1:])
        # convert a arbitary path to absolute ones
        if not Path(link).is_absolute():
            link_path = f"{self.working_folder}/{link}"
        else:
            link_path = link
        link_path = Path(link_path)

        try:
            # quoted form normally starts with percent characters
            link_path = Path(urllib.parse.unquote_plus(str(link_path))).resolve()
        except:
            pass
        return link_path

    def remove_duplicate_element_in_list(self, lista):
        listb=[]
        for item in lista:
            if not item in listb:
                listb.append(item)
        return listb

    def get_file_mtime(self, link):
        return self.get_absolute_path(link).stat().st_mtime

    def get_formated_mtime_filename(self, link):
        # use date and time info to generate new filename for images
        my_mtime = self.get_file_mtime(link)
        d = datetime.datetime.fromtimestamp(my_mtime)
        date_format = '%Y-%m-%d-%H-%M-%S-%f'
        timestr = d.strftime(date_format)
        suffix = self.get_absolute_path(link).suffix
        new_filename = f"assets/{timestr}{suffix}"
        return new_filename

    def get_formatted_current_time_filename(self):
        # get the current date and time for the name of new image download
        current_time = datetime.datetime.now()
        date_format = '%Y-%m-%d-%H-%M-%S-%f'
        timestr = current_time.strftime(date_format)
        return timestr

    def download_links(self):
        # download image from web
        self.original_image_links = self.get_image_links(self.md_content)
        # prepare for the temp image download dir
        if self.download_dir.exists():
            shutil.rmtree(self.download_dir)
        self.download_dir.mkdir()
        self.localized_image_links = []
        web_link_pattern = re.compile(r'(ht|f)tps?://')

        for link in self.original_image_links:
            if web_link_pattern.search(link): # is a web link
                if link.find("jianshu.io") > 0: #jianshu link
                    link = link.split('?')[0]
                    download_image_filename = link.split('/')[-1]
                else:
                    ext_patt = r"\.(jpg|png|bmp|gif|svg|jpeg)"
                    try:
                        suffix = re.search(ext_patt, link, re.MULTILINE | re.IGNORECASE).group(1)
                    except:
                        suffix = 'jpg'
                    download_image_filename = f"{self.get_formatted_current_time_filename()}.{suffix}"
                # requests is used to get the content of image
                r = requests.get(link, stream=True)
                new_link = self.download_dir/download_image_filename
                with open(new_link, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
                self.localized_image_links.append(new_link)
            else:
                self.localized_image_links.append(link)

        self.replace_image_links(self.original_image_links, self.localized_image_links)


    def clean_up_download_images(self):
        # remove the temp image download dir
        if self.download_dir.exists():
            shutil.rmtree(self.download_dir)
                

    def get_image_links(self, md_content):
        # regex to get image links ![]()
        return re.findall(r'\!\[.*?\]\((.*?)\)', md_content)

    def normalize_links(self):
        # if new download file or name too short to introduce conflict, rename it.
        self.fixed_image_links = []
        regex = r"assets/\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{6}"

        for link in self.localized_image_links:
            if self.get_absolute_path(self.working_folder/link).exists(): # relative link exists
                link = self.get_absolute_path(self.working_folder/link)
            else:
                link = self.get_absolute_path(link)
            
            if link.exists(): # link exists
                if re.match(regex, str(link)):
                    # link is already assets local and well formated, no need to convert at all
                    pass
                elif len(link.stem) < 19 or link.stem.find(" ")>=0: 
                    # very short form easy to conflict or with space in name
                    # link needs to convert to date format
                    link = self.get_formated_mtime_filename(link)
                else:
                    # no need to rename, only need to move
                    link = Path(f"assets/{Path(link).name}")
                self.fixed_image_links.append(link)

            else: # no such link, ignore the error 
                pass


        self.replace_image_links(self.localized_image_links, self.fixed_image_links)

    def copy_image_files(self):
        for link, new_link in zip(self.localized_image_links, self.fixed_image_links):
             if link != new_link:
                # need to move
                source = self.get_absolute_path(link)
                target = self.get_absolute_path(new_link)
                if not target.parent.exists():
                    target.parent.mkdir(parents=True)
                try:
                    shutil.copy2(source, target)
                except:
                    pass

    def make_output_md(self, output_md, mycontent=None, localize_images=True):
        # make a dir, put md and assets (containig images)
        try:
            output_md = Path(output_md)
        except:
            pass
        if not output_md.parent.exists():
            output_md.parent.mkdir(parents=True)
        if mycontent==None: # not specifying mycontent, by default
            mycontent=self.md_content
        with open(output_md, 'w') as f:
            f.write(mycontent)
        if not (output_md.parent/"assets").exists():
            (output_md.parent/"assets").mkdir()
        if localize_images:
            for img in self.fixed_image_links:
                source = self.get_absolute_path(img)
                target = output_md.parent/"assets"/source.name
                if not target.exists():
                    try:
                        shutil.copy2(source, target)
                    except:
                        pass


    def replace_image_links(self, source_list, target_list):
        # replace image links in the md
        content = self.md_content
        for link, new_link in zip(source_list, target_list):
            content = content.replace(f']({str(link)})', f']({str(new_link)})')
        self.md_content = content

    def convert(self, localize_images=True, make_output_md=True):
              
        if localize_images:
            # do not download roam images, using the backup local ones
            self.download_links()
            self.normalize_links()
            self.copy_image_files()
            self.clean_up_download_images()
        
        if make_output_md:
            self.make_output_md(self.output_md, localize_images=localize_images)
