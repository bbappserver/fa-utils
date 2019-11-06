import requests,re,dateparser,json
from bs4 import BeautifulSoup as bs4
try:
    from urlparse import urljoin  # Python2
except ImportError:
    from urllib.parse import urljoin  # Python3

GALLERY_URL="http://www.furaffinity.net/gallery/{}"
USER_URL="http://www.furaffinity.net/user/{}"
s = requests.Session() 
def load_cookies_file(path="cookies.json"):
    with open(path) as f:
        s.cookies.update(json.load(f))

class ScrapeObj:
    
    def __init__(self):
        self._body=None
        self.soup=None
    
    @property
    def url(self):
        raise NotImplementedError()
    @property
    def body(self):
        if self._body is None:
            response=s.get(self.url)
            if response.status_code == 200:
                self._body = response.content
            else:
                raise FileNotFoundError()
        return self._body
    
    def parse(self):
        if self.soup is None:
            self.soup=bs4(self.body,'html.parser')
        return self.soup
    
    
    def rel_url_to_abs_url(self,rel):
        return urljoin(self.url,rel)


class Post(ScrapeObj):
    POST_URL="http://www.furaffinity.net/view/{}"
    bottom_bar_title_class=".minigallery-title"
    minigallery_link_selector="u > s > a"
    description_box_selector="td.alt1"
    meta_box_selector="#page-submission > table > tbody > tr:nth-child(1) > td > table > tbody > tr:nth-child(2) > td > table > tbody > tr:nth-child(1) > td.alt1 > table > tbody > tr > td"
    timestamp_selector="#page-submission > table > tbody > tr:nth-child(1) > td > table > tbody > tr:nth-child(2) > td > table > tbody > tr:nth-child(1) > td.alt1 > table > tbody > tr > td > span"
    tag_selector="#keywords"
    classic_title_selector=".classic-submission-title.information >h2"
    
    def __init__(self,id):
        self.id=id
        self._body=None
        self.soup=None

    @property
    def url(self):
        return self.POST_URL.format(self.id)
    
    @property
    def next(self):
        try:
            next_link=self.parse().select_one('a.next.button-link')
            next_id=next_link.attrs['href'].split("/")[-2]
            return Post(next_id)
        except:
            return None

    @property
    def prev(self):
        try:
            next_link=self.parse().select_one('a.prev.button-link')
            next_id=next_link.attrs['href'].split("/")[-2]
            return Post(next_id)
        except:
            return None
    
    @property
    def title(self):
        return self.parse().select_one(self.classic_title_selector).text

    @property
    def _description_element(self):
        #Magic offsets because the selectors aren't working
        #Maybe use named memebers if it breaks
        e=self.parse().find('table',class_="maintable").contents[3].contents
        e=e[1].contents[29].contents[3].contents[1]
        return e
    @property
    def description(self):
        e=self._description_element
        s=""
        for ee in e.contents:
            s+=str(ee)
        return s.replace("<br/>","\n").strip()

    @property
    def download_link(self):
        return "http:"+self.parse().find("a",text="Download").attrs["href"]
    

    @property
    def timestamp(self):
        try:
            e=self.parse().select_one(".popup_date")
            return dateparser.parse(e.text)
        except:
            return None
    
    @property
    def tags(self):
        taglinks=self.parse().select(self.tag_selector+"> a")
        tags = (x.text.strip() for x in taglinks)
        return tags
    
    @property
    def is_favourite(self):
        raise NotImplementedError()
    def add_to_favourites(self):
        raise NotImplementedError()
    
    def remove_from_favourites(self):
        raise NotImplementedError()
    
    def rescue(self,seed_post_id):
        seed_post=Post(seed_post_id)

        posts=[seed_post]

        print("------------")
        print(seed_post.title)
        print("------------")
        print(seed_post.description)
        print("------------")
        print(seed_post.download_link)
        print("------------")
        print(list(seed_post.tags))
        print("------------")
        print("------------")
        nextp = seed_post.next
        prevp = seed_post.prev

        while nextp is not None:
            posts.append(nextp)
            nextp=nextp.next

        while prevp is not None:
            posts.append(prevp)
            prevp=prevp.prev

        print(posts)
    


class User(ScrapeObj):
    USER_URL="http://www.furaffinity.net/user/{}"
    WATCHING_URL="http://www.furaffinity.net/watchlist/by/{}}/"
    WATCHED_BY_URL="http://www.furaffinity.net/watchlist/to/{}}/"
    USER_INFO_CLASS="user-info"
    USER_CONTACT_CLASS="user-contacts"
    CONTACT_ITEM_CLASS="classic-contact-info-item"
    def __init__(self,username):
        self.username=username
        self._body=None
        self.soup=None
    
    def contact_urls(self):
        e=self.parse().find(class_=self.USER_CONTACT_CLASS)
        l=e.find_all('a')
        return (x.attrs['href'] for x in l)
    
    @property
    def watchlist(self):
        raise NotImplementedError()
    @property
    def is_dead(self):
        try:
            self.body
        except FileNotFoundError as e:
            return True
        return False

    @property
    def is_watched_by_session_user(self):
        raise NotImplementedError()
    
    @property
    def is_watching_session_user(self):
        raise NotImplementedError()
    def start_watching(self):
        raise NotImplementedError()
    def stop_watching(self):
        raise NotImplementedError()
        

    
class Gallery(ScrapeObj):
    POST_URL_REL_PATTERN=re.compile(r'/view/\d+/?')
    FAVOURITE_GALLER_NEXT=re.compile(r'/favourites/[^/]+/[^/]/next')
    @property
    def posts(self):
        self.soup.find_all('a',href=self.POST_URL_REL_PATTERN)

load_cookies_file()
