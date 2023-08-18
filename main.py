
from multiprocessing import Process
from sys import argv
from rich.status import Status
from rich.panel import Panel
import requests
from requests import Response
import time
from bs4 import BeautifulSoup, Tag
import os
import re
import shutil 
import datetime
from urllib.parse import urlparse

localfile = re.compile(r'^(?:[a-zA-Z]:)?[\\/]?[\w\s\-.]+(?:[\\/][\w\s\-.]+)*$')


def is_website_address(s):
    parsed = urlparse(s)
    return parsed.scheme in ('http', 'https') and parsed.netloc


def readhtml(filename):
    with open(filename, 'r', encoding='utf-8', errors="ignore") as html_file:
        return html_file.read()


class Resources:
    HasLinks = [
        "a", "link","img","script","iframe","audio","video","source","track","area","form","meta","object","embed","style",
    ]
    HasParams = ["href", "src", "data", "action"]

html_tags_with_links = [
        ("a", "href"),
        ("link", "href"),
        ("img", "src"),
        ("script", "src"),
        ("iframe", "src"),
        ("audio", "src"),
        ("video", "src"),
        ("source", "src"),     # Within audio and video tags
        ("track", "src"),      # Within video tag
        ("area", "href"),
        ("form", "action"),
        ("meta", "href"),  # For refresh redirects
        ("object", "data"),
        ("embed", "src"),
        ("style", ""),  # For embedded scripts
    ]

class TagResource(object):
    
    def __init__(self, tag: Tag) -> None:
        self.queries = []
        self.resources = []
        self.name = tag.name
        self.attributes = [(name, value) for name, value in tag.attrs.items()]
        for attr, value in self.attributes:
            if attr.strip() in Resources.HasParams:
                if isinstance(value, list):
                    for val in value:
                        if val.startswith("?"):
                            self.queries.append(val)
                        else:
                            self.resources.append(val)
                elif isinstance(value, str):
                    if value.startswith("?"):
                        self.queries.append(value)
                    else:
                        self.resources.append(value)
        self.subtags = [x for x in tag.children if isinstance(x, Tag) if x.name in Resources.HasLinks]
        self.more_tags = []
        for stag in self.subtags:
            try:
                for child in stag.children:
                    if isinstance(child, Tag):
                        self.more_tags.append(child)
                        for chil in child.children:
                            if isinstance(chil, Tag):
                                self.more_tags.append(chil)
                                for chi in chil.children:
                                    if isinstance(chi, Tag):
                                        self.more_tags.append(chi)
            except:
                continue        
        for tag in self.more_tags:
            try:
                if tag.name in Resources.HasLinks:
                    self.subtags.append(tag)
            except:
                continue
        for stag in self.subtags:
            namevals = [(name, value) for name, value in stag.attrs.items()]
            for attr, val in namevals:
                if attr.strip() in Resources.HasParams:
                    if isinstance(val, list):
                        for v in val:
                            if v.startswith("?"):
                                self.queries.append(v)
                            else:
                                self.resources.append(v)
                    elif isinstance(val, str):
                        if val.startswith("?"):
                            self.queries.append(val)
                        else:
                            self.resources.append(val)

    def show(self):
        print(f"\033[44m {self.name} \033[0m")
        if self.queries != []:
            print(" ║╙─────queries   \033[32m+\033[0m", end="")
            mq = len(self.queries)
            for index, query in enumerate(self.queries):
                if mq == 1:
                    print("\n ║            └─", query)
                else:
                    add = mq-index
                    pad = (mq-index)*"│"
                    rightpad = (mq-index)*"─" if (mq-index) > 0 else ""
                    print(f"\n ║      {pad}└{rightpad}", query)
        else:
            print(" ║╙─────queries   \033[31mX\033[0m")
        if self.resources != []:
            print(" ╙──────resources \033[32m+\033[0m  ")
            rq = len(self.resources)
            for index, resource in enumerate(self.resources):
                if rq == 1:
                    print("                └────", resource)
                else:
                    pad = (rq-index-1)*"│" if rq > 1 else " "*(rq-index)
                    rightpad = (rq-index)*"─" if (rq-index) > 0 else ""
                    print(f"           {pad}└{rightpad}", resource)
        else:
            print(" ╙─────resources  \033[31mX\033[0m  ", "\n")
    
    def getQueries(self):
        return self.queries
    def getResources(self):
        return self.resources
    


def htmllinks(filename):

    html_tags_with_links = [
        ("a", "href"),
        ("link", "href"),
        ("img", "src"),
        ("script", "src"),
        ("iframe", "src"),
        ("audio", "src"),
        ("video", "src"),
        ("source", "src"),     # Within audio and video tags
        ("track", "src"),      # Within video tag
        ("area", "href"),
        ("form", "action"),
        ("meta", "href"),  # For refresh redirects
        ("object", "data"),
        ("embed", "src"),
        ("style", ""),  # For embedded scripts
    ]
    with Status("parsing links....") as status:
        soup = BeautifulSoup(readhtml(filename), "html.parser")
        resources = []
        for tag, param in html_tags_with_links:
            status.update(f"parsing links - {tag}")
            items = [x for x in soup.find_all(tag) if isinstance(x, Tag)]
            Resources = [TagResource(x) for x in items]
            for r in Resources:
                resources.append(r)        
        for resource in resources:
            resource.show()
    return resources


def recreate_resources_structure(resources: list[TagResource], domain_name: str=None):
    directories = []
    files = []

    for resource in resources:
        for path in resource.resources:
            if path.endswith("/"):
                
                directories.append(path.replace("/", "\\"))
            else:
                files.append(path.replace("/", "\\"))
    
    rootdir = os.getcwd() + os.sep + domain_name.split(".")[1]
    with Status("Setting up structure....") as status:
        if os.path.exists(rootdir):
            shutil.rmtree(rootdir)
        os.makedirs(rootdir, exist_ok=True)
        paths = []
        status.update("creating directories")
        for directory in directories:
            x = rootdir+directory
            status.update(f"creating directory {x}")
            paths.append(x)
        
        file_paths = []
        status.update("Creating files")
        for file in files:
            fi = rootdir + os.sep + file
            try:
                os.makedirs(os.path.dirname(fi), exist_ok=True)
                status.update(f"creating {fi}")
            except:
                status.update(f"bad directory name: {fi}")
                continue
            if file == "" or file is None:
                continue
            try:
                with open(fi, "w") as f:
                    f.close()
                    file_paths.append(fi)
            except:
                pass

        if domain_name is not None:      
            fileresources: list[Content] = []
            website_paths = []
            
            for index, file in enumerate(files):
                f = file.replace("\\", "/").strip("/")
                p = domain_name + "/" + f
                website_paths.append(p)
                status.update(f"Requesting - {p}")
                try:
                    fileresources.append(Content(p, file_paths[index]))
                except:
                    status.update(f"skipping bad resource: {p}")
                
            for filer in fileresources:
                filer.request()
                status.update(f" Fetching {filer.url}")
            
            done = []
            status.update(f"waiting on server responses")
            while True:
                done = [x.check() for x in fileresources]
                try:
                    done.index("busy")
                except:
                    break
    


def getresource(url, path):
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3 Edge/16.16299'
    }
    response = requests.get(url, headers=headers, timeout=6)
    if response.status_code == 200:
        with open(path, "wb") as wfile:
            wfile.write(response.content)

class Content:
    def __init__(self, url, path) -> None:
        self.path = path
        self.url = url
        self.get_process = Process(target=getresource, args=(self.url,self.path))
    def request(self):
        self.get_process.run()
    
    def check(self):
        if self.get_process.is_alive() == True:
            return "busy"
        else:
            return "done"

def error_message(text, objects: list=None):
    print(f"\033[41m   ERROR    {datetime.datetime.now()}  \033[0m")
    print("\033[31m", text, "\033[0m")
    if objects is not None:
        for object in objects:
            print(object)

def clone_website(domain_name: str):
    with Status("checking domain name") as status:

        if domain_name.startswith("https://www.") == False:
            domain_name = "https://www." + domain_name
        path = "index.html"
        headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3 Edge/16.16299'
        }
        status.update("fetching index...")
        try:
            response = requests.get(domain_name, headers=headers, timeout=6)
        except requests.exceptions.ConnectTimeout:
            error_message("\033[41mThe website took more than six seconds to respond... Giving up.")
            exit()
        except requests.exceptions.ConnectionError:
            error_message("This website actively refused to respond to the request. giving up...")
            exit()
        status.update("response recieved!")
        if response.status_code == 200:
            status.update("index recieved!")
            with open("index.html", "wb") as f:
                f.write(bytes(response.text, encoding="utf-8"))
    
    links = htmllinks("index.html")
    recreate_resources_structure(links, domain_name)


def inappropriate_behavior():
    def print_help():
        wb = "\033[37;44m"
        rs = "\033[0m"
        br = "\033[41m"
        bw = "\033[47m"
        print(f"""
Website Cloner
  Usage:
    clone <domain name>
""")
    
    if argv[1] in ["help", "--help", "-h"]:
        print_help()


def to_basename(domain):
    if domain.startswith("https://www."):
        dotcount = 0
        dotswitch = False
    else:
        dotswitch = True
        dotcount = 1
    base = ""
    for char in domain:
        if char == ".":
            dotswitch = not dotswitch
            dotcount+=1
        if dotcount == 2:
            break
        if dotswitch:
            base += char
    return base

def main():
    try:
        domain_name = argv[1]   
    except IndexError:
        print("Domain name not specified")
        exit()
    total_time = time.time()
    clone_website(domain_name)
    total_delta_time = time.time() - total_time
    print(f"Total time : {total_delta_time}")
    print("index.html  v")
    for root, dirs, files in os.walk(to_basename(domain_name)):
        for file in files:
            print("| ", os.path.join(root, file))
    

if __name__ == "__main__":
    main()


    
