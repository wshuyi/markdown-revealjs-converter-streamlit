from converter import MarkdownConverter
import os
import re
from pathlib import Path

class RoamMDConverter(MarkdownConverter):
    # handle research roam exported markdown

    def convert(self, roam_doc_mode="document", roam_to_normal_md=True):
        self.convert_roam_list_to_normal_md(roam_doc_mode, roam_to_normal_md)
        self.make_output_md(self.output_md, localize_images=False)
    
    def convert_roam_list_to_normal_md(self, roam_doc_mode, roam_to_normal_md):
        # roam list md
        data = self.md_content
        if roam_doc_mode=="document": # turn roam md to document, default mode
            regex = r"^(\s*)-\s+?"
            subst = "\\n"
            data = re.sub(regex, subst, data, 0, re.MULTILINE)
            #remove unnecessary [*](...)
            regex = r"\s\[\*\]\((.*\n)*.+?\)"
            subst = ""
            data = re.sub(regex, subst, data, 0, re.MULTILINE)
            # add newline before ending code block sign
            regex = r"(```)$"
            subst = "\\n\\1"
            data = re.sub(regex, subst, data, 0, re.MULTILINE)
            # special handling the ones with text and block ref
            regex = r"(```)\s\[\*\]\(.+$"
            subst = "\\n\\1"
            data = re.sub(regex, subst, data, 0, re.MULTILINE)
            # special handling the ones with text and block ref
            regex = r"(```)\s\^.+$"
            subst = "\\n\\1"
            data = re.sub(regex, subst, data, 0, re.MULTILINE)
        elif roam_doc_mode=="slide": # turn roam md to slide mode
 
            # remove list sign before title
            regex = r"^-\s"
            subst = "# "
            data = re.sub(regex, subst, data, 0, re.MULTILINE)

            # remove list sign before sec
            regex = r"^\s{4}-\s"
            subst = "\\n## "
            data = re.sub(regex, subst, data, 0, re.MULTILINE)

            # remove list sign before slide page title and add level 3 sec sign
            regex = r"^\s{8}-\s"
            subst = "\\n### "
            data = re.sub(regex, subst, data, 0, re.MULTILINE)

            # remove list sign before full window image
            regex = r"^### !\["
            subst = "!["
            data = re.sub(regex, subst, data, 0, re.MULTILINE)

            # move items back 4 spaces
            regex = r"\s{12}-\s"
            subst = "- "
            data = re.sub(regex, subst, data, 0, re.MULTILINE)

            # remove list sign before videos
            regex = r".*\[video\]\("
            subst = "[video]("
            data = re.sub(regex, subst, data, 0, re.MULTILINE)

            # remove list sign before the code block
            regex = r"^-\s```"
            subst = "```"
            data = re.sub(regex, subst, data, 0, re.MULTILINE)

            # table sign: remove the list sign in front
            regex = r"^-\s\|"
            subst = "|"
            data = re.sub(regex, subst, data, 0, re.MULTILINE)

            # add blank line between the table and the list item
            regex = r"(\|\n)(-\s\S)"
            subst = "\\1\\n\\2"
            data = re.sub(regex, subst, data, 0, re.MULTILINE)

        else: # reserved
            regex = r"^(\s*)-\s+?"
            subst = "\\n\\1"
            data = re.sub(regex, subst, data, 0, re.MULTILINE)
        
        if roam_to_normal_md:
            # remove todo 
            regex = r"{{\[\[TODO\]\]}}\s"
            subst = ""
            data = re.sub(regex, subst, data, 0, re.MULTILINE)

            # remove single tags
            regex = r"\#\w+(\s|\n)"
            subst = ""
            data = re.sub(regex, subst, data, 0, re.MULTILINE)

            # remove squared tags
            regex = r"\#\[\[.+?\]\]"
            subst = ""
            data = re.sub(regex, subst, data, 0, re.MULTILINE)

            # remove other page ref (starting without `@` sign)
            regex = r"\[\[([^@]+?)\]\]"
            subst = "\\1"
            data = re.sub(regex, subst, data, 0, re.MULTILINE)
        
        self.md_content = data