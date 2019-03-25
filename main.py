#!/usr/bin/emv python3
import requests
from bs4 import BeautifulSoup
import json
import os
import os.path
import pickle
import time
import tempfile
import logging
from progress.bar import Bar

undelete_url="https://vj5pbopejlhcbz4n.onion.link/fa/%s"
user = None
#domain="http://127.0.0.1:9292"
domain="https://faexport.boothale.net"
postdir="posts"
hydrus_key=None
debug = True
IMAGE_FILE_REGEX=r"(\d*)\.([^_]+)_(.+)\.(\w+)"
deepscan=False
logging.basicConfig(filename='error.log',level=logging.ERROR)
# Grabs you FA watchlist and stuffs it into hydrus
# Copyright (C) 2019, Thatguy from the discord

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

def throttle():
    return 0

class UserData:
    def __init__(self):
        self.last_pulled=0
        #self.dead=False


class PersistantData:

    def __init__(self,path):
        self.user_data={}
        self.path=path
        self.hydrus_key=None
        self.max_time= time.time()

    def set_time(self,t=None):
        if t is None:
            self.max_time = time.time()-10
        else:
            self.max_time = t-10
    
    def override_time(self,t):
        for u in self.user_data.values():
            u.last_pulled=t
        self.write()
            

    def checkpoint_user(self,username):
        if username not in self.user_data:
            self.user_data[username]=UserData()
        self.user_data[username].last_pulled = self.max_time
        self.write()
    
    def set_hydrus_key(self,key):
        self.hydrus_key=key
        self.write()

    def write(self):
        #recoverabl safe write
        backup=self.path+".bak"
        fd,fname=tempfile.mkstemp()
        with open(fname,"wb+") as f:
            pickle.dump(self,f)

        if os.path.exists(self.path):
            os.rename(self.path,backup)
        os.rename(fname,self.path)
        os.close(fd)
    
    def last_pulled(self,username):
        try:
            return self.user_data[username].last_pulled
        except:
            return 0


def send_to_hydrus(url):
    d={"url":url}
    headers={"Hydrus-Client-API-Access-Key":hydrus_key}
    
    tarpit=2
    retry=False
    r=None
    try:
        r=r = requests.post("http://127.0.0.1:45869/add_urls/add_url", json=d, headers=headers,timeout=5)
        retry=False
    except (requests.exceptions.Timeout,requests.exceptions.ConnectionError):
        retry=True

    while r is None or r.status_code !=200 or retry:
        if r is not None and r.status_code == 500:
            print ("Hydrus screwed up on\n\t%s"%(url,))
            return True
        time.sleep(tarpit)
        tarpit *=2
        try:
            r = requests.post("http://127.0.0.1:45869/add_urls/add_url", json=d, headers=headers,timeout=5)
            retry=False
            continue
        except (requests.exceptions.Timeout,requests.exceptions.ConnectionError):
            retry=True

    if r.status_code != 200:
         raise NotImplementedError("Hydrus refused us and we don't know how to finish")

def timestamp_to_python_time(faexport_timestamp):
    return time.mktime(time.strptime(faexport_timestamp,"%Y-%m-%dT%H:%M:%SZ"))

def robust_get(post):
    r=None
    tarpit=2
    retry=5
    try:
        r= requests.get(post,timeout=5)
        if r is not None and r.status_code == 200:
            retry=0
    except (requests.exceptions.Timeout,requests.exceptions.ConnectionError):
        retry-=1

    while r is None or ( r.status_code !=200 and retry >0):
        
        if r is not None and r.status_code == 500:
            if "sinatra" in r.text:
                logging.error("\nFAexport screwed up on "+post)
                return True
            else:
                logging.error("furaffinity error\n"+r.text)
            r=True
            # if not r.json()["error"].startswith("FA re"):
                #not "error": "FA returned a system error page when trying to access 
            #print ("FAExport screwed up on\n\t%s"%(post,))
            #Faexport doesn't have goo enough error detection to distinguish a server error from a forwarded error
            retry-=1
        if r is not None and r.status_code == 404:
            return r
        time.sleep(tarpit)
        tarpit *=2
        if tarpit>400:
            return True
        try:
            r= requests.get(post,timeout=5)
            continue
        except (requests.exceptions.Timeout,requests.exceptions.ConnectionError) as e:
            retry-=1
    
    return r

def paginated_json_array_to_generator(url,start_page=1,max=10000,skip_on_max=10000):
    l=[]

    r=robust_get( url %(skip_on_max,) )
    if r is not True and r.status_code == 200 and len(r.json()) !=0:
            return [] #reject because of page max
    
    

    for i in range(start_page,max):
        r = robust_get( url %(i,) )
        if  r is True or r.status_code != 200:
            return [] #If there was a screw up assume dead list
        d =r.json()
        if len(d) ==0:
            return []
        l=d
        for j in range(len(l)):
            yield l[j]

def process_post(pid):
    
    try:
        
        
        #send_to_hydrus("http://www.furaffinity.net/view/%s"%(pid,))
        path = postdir+"/"+pid+".json"
        if os.path.exists(path) and not deepscan:
            return False
        post=domain + "/submission/%s.json" %(pid,)
        time.sleep(throttle())
        r=robust_get(post)
        if r == True: return True    
        txt=r.text
        r= json.loads(txt)
        timestamp=r["posted_at"]
        poster=r["name"]
        if not deepscan and(timestamp_to_python_time(timestamp) < persist.last_pulled(poster)):
            return False
        
        #if requested path isn't there create it
        if not os.path.exists(postdir):
            os.makedirs(postdir)

        path = postdir+"/"+pid+".json"
        if not os.path.exists(path):
            with open("posttmp","w+") as f:
                f.write(txt)
            os.rename("posttmp",path)
        # img_url=r["download"]
        
        # send_to_hydrus(img_url)
        #stuff hydrus doesn't understand yet
        # post_url=r["link"]
        # send_to_hydrus(post_url)
        #contributors=analyze_description_for_other_names(r["description"])
        #title=r["title"]
        #tags=r["keywords"]
    except KeyError:
        pass
        #I have no idea how to treat text or non img/swf work so just chug along

    return True


def process_user_pages(username,include_scraps,display_progress=False):
    
    #Uses generator semantics, it is necessary to retrieve all pages for progress
    #If you don't need progress we can skip a lot of requests once we find a duplicate
    if display_progress:
        gallery="%s/user/%s/" %(domain,username) + "gallery.json?page=%s"
        l=list(paginated_json_array_to_generator(gallery))
        
        bar = Bar("%s - %s" %(username,"gallery"), max=len(l))
        for pid in l:     
            #time.sleep(0.333)
            if not process_post(pid):
                break
            bar.next()
        bar.finish()
        
        if include_scraps:
            scraps="%s/user/%s/" %(domain,username) + "scraps.json?page=%s"
            l=list(paginated_json_array_to_generator(scraps))
            bar = Bar("%s - %s" %(username,"scraps"), max=len(l))
            for pid in l:
                if not process_post(pid):
                    break
                bar.next()
            bar.finish()
    else:
        
        gallery="%s/user/%s/" %(domain,username) + "gallery.json?page=%s"
        l=paginated_json_array_to_generator(gallery)
        
        for pid in l:     
            #time.sleep(0.333)
            if not process_post(pid):
                break

        if include_scraps:
            scraps="%s/user/%s/" %(domain,username) + "scraps.json?page=%s"
            l=paginated_json_array_to_generator(scraps)
            for pid in l:
                if not process_post(pid):
                    break
    
    

def load_cookies():
    raise NotImplementedError()
    # ar = requests.cookies.RequestsCookieJar()
    # jar.set('tasty_cookie', 'yum', domain='httpbin.org', path='/cookies')
    # jar.set('gross_cookie', 'blech', domain='httpbin.org', path='/elsewhere')
    # url = 'https://httpbin.org/cookies'
    # r = requests.get(url, cookies=jar)

def get_watchers(of_user,max_page=20):
    url = "%s/user/%s/" %(domain,of_user) + "watchers.json?page=%s"
    return ( x.replace("_","") for x in paginated_json_array_to_generator(url,max=max_page) )

def get_watchlist(of_user,max_page=20):
    url = "%s/user/%s/" %(domain,of_user) + "watching.json?page=%s"
    return ( x.replace("_","") for x in paginated_json_array_to_generator(url,max=max_page) )

def find_rescue_seed(username):
    raise NotImplementedError()
    for w in get_watchers(username):
        for f in get_favourites(w):
            if f["user"] == username:
                return f["url"]


def rescue_user_post_urls(seed_url,scrap_seed_url=None,memoize=set()):
    raise NotImplementedError
    if seed_url is None:
        return memoize
    memoize.add(seed_url)
    navbar=[]
    for nav_item in navbar:
        if nav_item not in memoize:
            rescue_user_post_urls(seed_url)
    return memoize

class UserDiscover:

    def __init__(self):
        self.path="discover.pkl"
        self.expanded=set()
        self.refcounts={}

    def write(self):
        #recoverabl safe write
        backup=self.path+".bak"
        fd,fname=tempfile.mkstemp()
        with open(fname,"wb+") as f:
            pickle.dump(self,f)

        if os.path.exists(self.path):
            os.rename(self.path,backup)
        os.rename(fname,self.path)
        os.close(fd)

    def discover(self,seed):
        url = "%s/user/%s/" %(domain,seed) + "watching.json?page=%s"
        ul= set(paginated_json_array_to_generator(url))
        n=len(ul)
        i=0
        
        # This part assumes that artists have an interst in the same kinds of artists as the art they draw.

        # bar= Bar("discovering root",max=n)
        # for u in ul:
        #     if u in self.expanded:
        #         continue
        #     url = "%s/user/%s/" %(domain,u) + "watching.json?page=%s"
        #     #Assume artists/watchers like the kind of art they generate, so expand them and give them much higher weight
        #     wl=paginated_json_array_to_generator(url,max=36,skip_on_max=100) 
        #     for ww in wl:
        #         if ww not in self.refcounts:
        #             if ww not in ul:
        #                 self.refcounts[ww]=10
        #         else:
        #             if ww not in ul:#shouldn't happen but will because legacy
        #                 self.refcounts[ww]+=10
        #             else:
        #                 del self.refcounts[ww]
        #     self.expanded.add(u)
        #     self.write()
        #     bar.next()
        # bar.finish()

        for u in ul:
            #artists could have several thousands of people watching them, o get an alphabetically biased subset
            #this should be random enough if the sample is big, because we don't want to be here all month
            url = "%s/user/%s/" %(domain,u) + "watchers.json?page=%s"
            watchers= list(paginated_json_array_to_generator(url,max=20))

            
            #grab people with similar taste to the root user
            i+=1
            bar= Bar("discovering %d/%d"%(i,n),max=len(watchers))
            for w in watchers:
                if w not in self.expanded:
                    url = "%s/user/%s/" %(domain,w) + "watching.json?page=%s"
                    wl=paginated_json_array_to_generator(url,max=13,skip_on_max=50) #20*13=2600 if people are watchig more than this they're usually robots
                    for ww in wl:
                        if ww not in self.refcounts:
                            if ww not in ul:
                                self.refcounts[ww]=1
                        else:
                            if ww not in ul:#shouldn't happen but will because legacy
                                self.refcounts[ww]+=1
                            else:
                                del self.refcounts[ww]
                    self.expanded.add(w)
                    self.write()
                bar.next()
            bar.finish()
    
    def print_top(self,n=30):
        i=0
        for key, value in sorted(self.refcounts.items(), key= lambda t: t[1],reverse=True):
            print ("%s: %s" % (key, value))
            i+=1
            if i >= n:
                break

def print_watchlist(user,prefix=""):
    ul = get_watchlist(user)
    for u in ul:
        print(prefix+u)           
                

def replace_dump(id):
    pass

def open_by_id(id):
    pass

def list_dumps():
    pass

def verify_dumps(on_fail=replace_dump):
    for dump in list_dumps():
        with open_by_id(dump) as f:
            try:
                json.load(f)
            except json.JSONDecodeError:
                on_fail(dump)


def load_persistant(persist_path):
    backup=persist_path+".bak"
    persist=None
    if os.path.exists(persist_path):
        try:
            with open(persist_path,"rb") as f:
                persist = pickle.load(f)
        except:
            #The checkpoint was corrupt so roll back
            try:
                with open(backup,"rb") as f:
                    persist = pickle.load(f)
            except:
                raise IOError("Checkpoint corrupt, if you see this something is very wrong")
                #print("Checkpoint corrupt, if you see this something is very wrong")
    elif os.path.exists(backup):
        #Edge case wjere the checkpoint as removed but before the backup was renamed
        os.rename(backup,persist_path)
        with open(persist_path,"rb") as f:
            persist = pickle.load(f)
    return persist

# import argparse
# parser = argparse.ArgumentParser()
# network_group = parser.add_argument_group('network')
# network_group.add_argument("-h","--host", type=str,help="URL of")

# output_group = parser.add_argument_group('output')
# output_group = parser.add_argument_group('config')
# # parser.add_argument("command", type=str,
# #                     help="commands see -h <subcommand >for details",
# #                     choices=["export-watchlist","get"])
# # parser.add_argument("argument", type=str,)
# parser.add_argument("-i", "--interactive", action="store_true",
#                     help="Run in interactive mode")
# parser.parse_args()

#load resume data
persist = load_persistant("checkpoint.pkl")
if persist is None:
    persist=PersistantData("checkpoint.pkl")

if persist.hydrus_key is None:
    print("Please provide hydrus key or hardcode it.")
    hydrus_key = input("key:")
    persist.set_hydrus_key(hydrus_key)
else:
    hydrus_key=persist.hydrus_key

#input_check_hydrus_key


url = "%s/user/%s/" %(domain,user) + "watching.json?page=%s"
# s1= set(paginated_json_array_to_generator(url))


# url = "%s/user/%s/" %(domain,user) + "watching.json?page=%s"
# s2= set(paginated_json_array_to_generator(url))

# s3= s1.union(s2)

# for u in s3:
#     print("%s" %(u,))

# exit(0)

if user is None:
    print("Who's watchlist should I read?")
    user = input("username:")

# print_watchlist(user)
# exit(0)
d=load_persistant("discover.pkl")
if d is None:
    d=UserDiscover()
d.discover(user)
d.print_top()
exit(0)

skip_until=None
if skip_until is None:
    print("Who should I start at?")
    skip_until = input("starting user (alphabetical):")
persist.set_time()
#are you being naughty?
if "boothale" in domain:
    print("\033[1;31;40m You are using the demo service for exporting ")
    print("\033[1;31;40m Please consider running faexport on your local machine to avoid pissing off its developer.")
    print("\033[1;31;40m Set the domain variable at the top of this file to fix it.")
    print("\u001b[0m")
    if not debug:
        print("I'm going to wait 30 seconds while you think about what you've done.")
        time.sleep(30)




pages=[]
skipping=True
i=0
ul = list(get_watchlist(user))
for u in ul:
    i+=1
    u=u.replace("_","")
    if not u.startswith(skip_until) and skipping:
        continue
    skipping = False
    print("Processing %d / %d %s"%(i,len(ul),u))
    process_user_pages(u,True)
    persist.checkpoint_user(u)
    #time.sleep(10)

