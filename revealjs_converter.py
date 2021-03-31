from converter import MarkdownConverter
import os
import re
import datetime
from PIL import Image
from pathlib import Path
import shutil

class MarkdownRevealjsConverter(MarkdownConverter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output_folder = self.config["revealjs_export_dir"]
        self.output_folder = Path(self.output_folder).expanduser()
        self.output_html = self.output_folder/"slide.html"
        self.revealjs_folder = self.code_dir/"reveal.js"

    def move_video_files_to_local_assets(self):
        regex = r"\[video\]\((.*?)\)"
        source_video_list = re.findall(regex, self.md_content, re.MULTILINE)
        for video in source_video_list:
            source_path = Path(video)
            dest_path = self.working_folder / f"assets/{str(source_path.name)}"
            if not dest_path.parent.exists():
                dest_path.parent.mkdir(parents=True)
            if source_path != dest_path:
                # if source path is not equal to target path
                self.md_content = self.md_content.replace(str(source_path), str(dest_path))
                shutil.copy2(source_path, dest_path)

    
    
    def convert(self, *args, **kwargs):
        # first, convert the self.md_content links to local
        super().convert(*args, **kwargs)
        # change working folder
        self.working_folder = self.md_output_dir
        self.temp_html = self.working_folder / "temp.html"
        # move all the video files to local assets
        self.move_video_files_to_local_assets()
        # convert markdown to slide markdown
        self.change_md_to_slide_md()
        # convert slide markdown to html with pandoc
        self.pandoc_slide_md_to_revealjs()
        # adjust several things in the html
        self.html_adjust()
        # output the html, along with revealjs and assets files
        self.make_output()

    def pandoc_slide_md_to_revealjs(self):
        # generate the temp md to run pandoc
        with open(self.output_md, 'w') as f:
            f.write(self.md_content)
        cmd = f"""
        pandoc -t revealjs \
        --standalone -i\
    --variable theme={self.config["revealjs_theme"]} \
    --variable transition={self.config["revealjs_transition"]} \
    {self.output_md} \
    -o {self.temp_html}
        """
        os.system(cmd)
        with open(self.temp_html) as f:
            self.html_content = f.read()

    def make_output(self):
        # prepare output dir
        # if folder exists, delete it.
        if self.output_folder.exists():
            shutil.rmtree(self.output_folder)
        # create output folder
        self.output_folder.mkdir()
        # create assets folder inside output folder 
        (self.output_folder/"assets").mkdir()
        # sync reveal.js runtime
        shutil.copytree(self.revealjs_folder, self.output_folder/"reveal.js")
        # sync media
        print(self.media_links)
        for link in self.media_links:
            shutil.copy2(self.working_folder/link, self.output_folder/"assets")
        # write output html slide file
        with open(self.output_html, 'w') as f:
            f.write(self.html_content)



    def html_adjust(self):
        data = self.html_content

        # make linear the legacy way for old pandoc

        keyboard_string = """
                keyboard: {
                39: 'next',
                37: 'prev'
            },
        """

        # make linear
        linear_control = "\n\nnavigationMode: 'linear', \n"

        regex = r"(Reveal\.initialize\({)"
        subst = "\\1" + linear_control
        data = re.sub(regex, subst, data, 0, re.MULTILINE)

        # change background video to lazy loading controls stretch video element

        regex = r"<section id=\"(.*?)\".*?class=\"(.*?)\".*?data-background-video=\"(.*?)\"(.*\n)*?</section>"
        subst = "<section id=\"\\1\" class=\"\\2\"><video class=\"stretch\" data-autoplay controls>  <source data-src=\"\\3\" type=\"video/mp4\" /></video></section>"
        data = re.sub(regex, subst, data, 0)

        # convert media links to export assets

        regex = r"<video\s.*src=\"(.*)\""
        background_video_links = re.findall(regex, data)

        self.media_links = self.fixed_image_links + background_video_links

        # inline image path convert:
        regex = r"(img src=\")(.*)/(.*?)\""
        subst = "\\1assets/\\3\""
        data = re.sub(regex, subst, data, 0, re.MULTILINE)
        # background image path convert:
        regex = r"(data-background-image=\")(.*)/(.*?)\""
        subst = "\\1assets/\\3\""
        data = re.sub(regex, subst, data, 0, re.MULTILINE)
        # background video path convert:
        regex = r"(<video\s.*src=\")(.*)/(.*?)\""
        subst = "\\1assets/\\3\""
        data = re.sub(regex, subst, data, 0, re.MULTILINE)

        # remove all the section id in Chinese slides:
        if self.is_chinese_slide:
            regex = r"(<section\s+)id=\".*?\"\s"
            subst = "\\1"
            data = re.sub(regex, subst, data, 0, re.MULTILINE)

        # use local revealjs package
        regex = r"https://unpkg\.com/reveal\.js@\^4//"
        subst = "reveal.js/"
        data = re.sub(regex, subst, data, 0, re.MULTILINE)

        self.html_content = data
    
    def check_contain_chinese(self, check_str):
        # for ch in check_str.decode('utf-8'):
        for ch in check_str:
            if '\u4e00' <= ch <= '\u9fff':
                return True
        return False

    def change_md_to_slide_md(self):

        

        data = self.md_content

        # handle blank lines between list items

        regex = r"^$\n(^\s*[-\*])"
        subst = "\\1"
        data = re.sub(regex, subst, data, 0, re.MULTILINE)

        # change title line from h1 to title
        regex = r"^# (.*)"
        title = re.match(regex, data, flags=re.MULTILINE).group(1)

        now = datetime.datetime.now()

        self.is_chinese_slide = self.check_contain_chinese(title)

        if self.is_chinese_slide: #contains chinese characters in title:
            # author = self.config["author_name_chinese"]
            date = "{}年{}月".format(now.year, now.month)
            end_string = "\n\n## {}\n\n{}".format("放映结束", "谢谢观赏！")

        else: # English title
            # author = self.config["author_name_english"]
            date = now.strftime("%b %Y")
            end_string = "\n\n## {}\n\n{}".format("The End", "Thanks for your time!")

        subst = "% \\1\\n% {}\\n% {}".format(self.author, date)
        data = re.sub(regex, subst, data, 0, re.MULTILINE)
        

        # change h2 title to h1 title
        regex = r"^## (.*)"
        subst = "# \\1"
        data = re.sub(regex, subst, data, 0, re.MULTILINE)

        # change h3 title to h2 title
        regex = r"^### (.*)"
        subst = "## \\1"
        data = re.sub(regex, subst, data, 0, re.MULTILINE)

        # change separated inline image to one line
        regex = r"^\s*[-\*]\s+\n+!\["
        subst = "* !["
        data = re.sub(regex, subst, data, 0, re.MULTILINE)

        # make background images to separate slide
        regex = r"^ *!\[.*\]\((.*)\)"
        subst = "\n\n##  {data-background-image=\"\\1\" data-background-size=\"contain\"}"
        data = re.sub(regex, subst, data, 0, re.MULTILINE)

        # make video links to separate video slide
        regex = r"^ *\[video\]\((.*)\)"
        subst = "\n\n## {} \n\n<video class=\"stretch\" src=\"\\1\" data-autoplay controls></video>"
        data = re.sub(regex, subst, data, 0, re.MULTILINE)


        # change inline images to html link
        regex = r"^ *([-\*])\s+!\[(.*)\]\((.*)\)"
        subst = "\\1 <img src=\"\\3\" style=\"border-style: none\" alt=\"\\2\">"
        data = re.sub(regex, subst, data, 0, re.MULTILINE)

        # resize inline images
        regex = r"^[\*-] +<img src=\"(.*?)\".*"
        links = re.findall(regex, data, re.MULTILINE)
        
        for link in links:
            with Image.open(self.working_folder / link) as im:
                width, height = im.size
            if height>width and height>400:
                regex = r"^(.*" + link + r".*?alt=\".*?\").*?>"
                subst = "\\1 height=\"400\">"
                data = re.sub(regex, subst, data, 0, re.MULTILINE)

        data = data + end_string
        
        self.md_content = data
