import pandas as pd
import os, re

"""scraper"""
import requests as req
from bs4 import BeautifulSoup, element

"""type"""
from typing import Literal, List, Union
from dataclasses import dataclass, field

def read_boards_literal() -> List[str]:
    return pd.read_csv('boards.txt', header=None)[0].to_list()

@dataclass
class Setting:
    """
    一些設定
    """
    board_samples = Literal[tuple(read_boards_literal())]
    header = {
        'user-agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) Gecko/20100101 Firefox/101.0'
            }

@dataclass
class article:
    """
    一篇文章的內容
    """
    title: str = ''
    score: int = 0 # 推數
    author: str = ''
    date: str = '' # 只有日期
    href:str = ''
    img: List[str] = field(default_factory=list) # 圖片抓的是cache (文章中顯示的圖片，不是圖片連結)


def create_session(board:Setting.board_samples = 'Beauty') -> req.sessions.Session:
    """
    因為要認證18+，要開啟一個session
    """
    payload = {
        'from': f'/bbs/{board}/index.html',
        'yes': 'yes'
    }
    rs = req.session()
    res = rs.post('https://www.ptt.cc/ask/over18',data=payload)
    if res.status_code != 200:
        raise ValueError(f'Page Lost, status: {res.status_code}')
    return rs

def get_content(soup_find:element.Tag, return_type:Literal['int', 'float', 'str', 'date']) -> Union[str, int, None]:
    """
    擷取一篇文章中的某個element，然後轉成需要的格式(return_type)
    """
    try:
        if return_type == 'int':
            return 0 if soup_find is None else int(soup_find.text.strip())
        if return_type == 'float':
            return 0.0 if soup_find is None else float(soup_find.text.strip())
        if return_type == 'str':
            return '' if soup_find is None else soup_find.text.strip()
    except:
        # e.g. 處理score時，return_type='int'，但有時會出現'爆'
        return get_content(soup_find, return_type='str')

# page_url = page
def get_articles_inPage(session:req.sessions.Session, page_url:str) -> List[article]:
    """
    某頁當中的所有文章
    """
    res = session.get(page_url, headers=Setting.header)
    if res.status_code != 200:
        return []

    soup = BeautifulSoup(res.text)
    arts = []
    for ele in soup.find_all('div', {'class':'r-ent'}):
        one_art = article()

        mat_title = ele.find('div', {'class':'title'})
        one_art.title = get_content(mat_title, return_type='str')

        mat_score = ele.find('div', {'class':'nrec'}).span
        one_art.score = get_content(mat_score, return_type='int')

        mat_author = ele.find('div', {'class':'author'})
        one_art.author = get_content(mat_author, return_type='str')

        mat_date = ele.find('div', {'class':'date'})
        one_art.date = get_content(mat_date, return_type='str')

        if (mat := ele.a) is not None:
            one_art.href = ele.a.get('href', '')
        arts.append(one_art)
    return arts

def update_imgs_inArticle(art: article) -> None:
    """
    update "img" attribute of a article object
    """
    art_href = art.href
    res = session.get(f'https://www.ptt.cc{art_href}', headers=Setting.header)
    if res.status_code != 200:
        pass

    soup = BeautifulSoup(res.text)
    imgs = []
    for i in soup.find_all('div', {'class':'richcontent'}):

        if (mat := i.find('img')) is not None:
            imgs.append( mat.get('src', '') )
    art.img = imgs

def download_img_inArticle(art:article, dst_by:Literal['date', 'author']='date'):
    """
    下載每篇文章當中的圖片 (還沒確定推文中的會不會抓)
    """
    imgs = art.img
    title = re.sub('[^\w]', '_', art.title)
    date = re.sub("[^\d]", "", art.date)
    author = re.sub('[^\w]', '_', art.author)
    dir = date if dst_by == 'date' else author # 準備路徑
    if dir not in os.listdir('./saved'):
        os.mkdir(f'./saved/{dir}')

    for cn, i in enumerate(imgs): # 一張一張圖片儲存
        img_req = req.get(i, headers=Setting.header)
        dst = f'./saved/{dir}/{title}_{cn}.png'
        if img_req.status_code == 200:
            with open(dst, 'wb') as f:
                f.write(img_req.content)


if __name__ == '__main__':
    """
    流程:
    1. 啟動session
    2. 鎖定頁面，取得該頁中所有文章的以下屬性:
            title: str = ''
            score: int = 0 # 推數
            author: str = ''
            date: str = '' # 只有日期

    3. 進入每篇文章找到圖片連結
    4. 下載圖片
    """
    session = create_session()
    page = 'https://www.ptt.cc/bbs/Beauty/index3984.html' # 指定頁面
    page = 'https://www.ptt.cc/bbs/sex/index3984.html' #也可以爬其他版

    for p in range(3995, 3900, -1):
        page = f'https://www.ptt.cc/bbs/Beauty/index{p}.html'
        arts = get_articles_inPage(session, page)
        for art in arts:
            update_imgs_inArticle(art)
            download_img_inArticle(art, dst_by='date')
