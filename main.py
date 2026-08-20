import re
import os
import argparse
from downloader.anime1 import Anime1
from downloader.gimy import Gimy
from downloader.baha import Baha
from downloader.meiju import Meiju
from downloader.hanju import Hanju
from downloader.dramasq import Dramasq
from downloader.movieffm import MovieFFM
from downloader.yanetflix import Yanetflix
from downloader.any import *
from downloader.animeOne import AnimeOne
from downloader.anime1in import Anime1in
from downloader.mmov import Mmov
from downloader.tv777 import TV777

def Get_Link_Type(link):
    if link.find("anime1.me")!=-1: #anime1 0(bad) 3(sn) 4(full)
        return Anime1.Link_Validate(link)
    elif any(d in link for d in ["gimytw.cc", "gimyai.tw", "gimy.com.tw", "gimytv.io"]): #gimy 0(bad) 5(sn) 6(full)
        return Gimy.Link_Validate(link)
    elif link.find("anime1.one")!=-1:
        return AnimeOne.Link_Validate(link) #animeOne 0(bad) 7(sn) 8(full)
    elif link.find("anime1.in")!=-1:
        return Anime1in.Link_Validate(link) #anime1in 0(bad) 21(sn) 22(full)
    elif link.find("meiju")!=-1:
        return Meiju.Link_Validate(link) #meiju 0(bad) 10(full)
    elif link.find("mmov")!=-1:
        return Mmov.Link_Validate(link) #mmov 0(bad) 11(sn) 12(full)
    elif link.find("321tw.com")!=-1: #hanju 0(bad) 14(full)
        return Hanju.Link_Validate(link)
    elif "dramasq.io" in link: #dramasq 0(bad) 15(sn) 16(full)
        return Dramasq.Link_Validate(link)
    elif "movieffm.net" in link: #movieffm 0(bad) 18(full)
        return MovieFFM.Link_Validate(link)
    elif "yanetflix.com" in link: #yanetflix 0(bad) 19(sn) 20(full)
        return Yanetflix.Link_Validate(link)
    elif "777tv." in link: #777tv 0(bad) 23(sn) 24(full)
        return TV777.Link_Validate(link)
    elif link.find("ani.gamer"):
        return Baha.Link_Validate(link) #baha 0(bad) 2(full)
    else:
        return 0 #any

def Multiple_Download_Select(eps, arg_start=None, arg_end=None, arg_all=False):
    """Select episode range interactively, or use CLI args when provided."""
    try:
        print(f"總共有{len(eps)}集")
        # Non-interactive mode: use CLI-supplied values
        if arg_all or (arg_start is None and arg_end is None and not arg_all):
            if arg_all:
                st, ed = 0, len(eps)
            else:
                # Interactive fallback
                getall = input("全部下載(y/n): ")
                if getall == 'n' or getall == 'N':
                    st = int(input(f"從第幾集開始?(1~{len(eps)}): "))
                    ed = int(input(f"下載到第幾集?({st}~{len(eps)}): "))
                    st -= 1
                else:
                    st, ed = 0, len(eps)
        else:
            # Use provided start/end (1-based, inclusive on both ends)
            st = (arg_start - 1) if arg_start is not None else 0
            ed = arg_end if arg_end is not None else len(eps)
            ed = min(ed, len(eps))

        if not st > ed:
            return st, ed
        else:
            print("Bad range")
            return None, None

    except Exception as e:
        print("Error:", str(e))
        return None, None


def run_download(link, TMP, downloadPath0, Quality, arg_start=None, arg_end=None, arg_all=False):
    """Run a single download for the given link."""
    linktype = Get_Link_Type(link)

    def ep_select(eps):
        return Multiple_Download_Select(eps, arg_start, arg_end, arg_all)

    if linktype == 0:
        TryGetAnyVideo(link, TMP, downloadPath0)
    if linktype == 1:
        Baha.Download_Request(link, TMP, downloadPath0, Quality)
    elif linktype == 2:
        title = Baha.Get_Title(link, False)
        downloadPath = downloadPath0 + '/' + title
        eps = Baha.Parse_Episodes(link)
        try:
            st, ed = ep_select(eps)
            for i in range(st, ed):
                Baha.Download_Request(eps[i], TMP, downloadPath, Quality)
        except Exception as e:
            print("Error:", str(e))
    elif linktype == 3:
        Anime1.Download_Request(link, downloadPath0)
    elif linktype == 4:
        title, eps = Anime1.Get_Title_Link(link)
        downloadPath = downloadPath0 + '/' + title + '/'
        try:
            st, ed = ep_select(eps)
            for i in range(st, ed):
                Anime1.Download_Request(eps[i], downloadPath)
        except Exception as e:
            print("Error:", str(e))
    elif linktype == 5:
        Gimy.Download_Request(link, TMP, downloadPath0)
    elif linktype == 6:
        title, eps = Gimy.Get_Title_Link(link)
        if title is None or eps is None:
            return
        downloadPath = downloadPath0 + '/' + title + '/'
        try:
            st, ed = ep_select(eps)
            for i in range(st, ed):
                Gimy.Download_Request(eps[i], TMP, downloadPath)
        except Exception as e:
            print("Error:", str(e))
    elif linktype == 7:
        AnimeOne.Download_Request(link, TMP, downloadPath0)
    elif linktype == 8:
        title, eps = AnimeOne.Get_Title_Link(link)
        downloadPath = downloadPath0 + '/' + title + '/'
        try:
            st, ed = ep_select(eps)
            for i in range(st, ed):
                AnimeOne.Download_Request(eps[i], TMP, downloadPath)
        except Exception as e:
            print("Error:", str(e))
    elif linktype == 10:
        try:
            title, eps = Meiju.Get_Title_Link(link)
            downloadPath = downloadPath0 + '/' + title + '/'
            st, ed = ep_select(eps)
            for i in range(st, ed):
                Meiju.Download_Request(eps[i], title + f" 第{i+1}集", TMP, downloadPath)
        except Exception as e:
            print("Error:", str(e))
    elif linktype == 11:
        Mmov.Download_Request(link, TMP, downloadPath0)
    elif linktype == 12:
        title, eps = Mmov.Get_Title_Link(link)
        downloadPath = downloadPath0 + '/' + title + '/'
        try:
            st, ed = ep_select(eps)
            for i in range(st, ed):
                Mmov.Download_Request(eps[i], TMP, downloadPath)
        except Exception as e:
            print("Error:", str(e))
    elif linktype == 14:
        try:
            title, eps = Hanju.Get_Title_Link(link)
            if title is None or eps is None:
                return
            downloadPath = downloadPath0 + '/' + title + '/'
            st, ed = ep_select(eps)
            for i in range(st, ed):
                Hanju.Download_Request(eps[i], title + f" 第{i+1}集", TMP, downloadPath)
        except Exception as e:
            print("Error:", str(e))
    elif linktype == 15:
        Dramasq.Download_Request(link, TMP, downloadPath0)
    elif linktype == 16:
        try:
            title, eps = Dramasq.Get_Title_Link(link)
            if title is None or eps is None:
                return
            downloadPath = downloadPath0 + '/' + title + '/'
            st, ed = ep_select(eps)
            for i in range(st, ed):
                Dramasq.Download_Request(eps[i], TMP, downloadPath)
        except Exception as e:
            print("Error:", str(e))
    elif linktype == 18:
        try:
            title, eps = MovieFFM.Get_Title_Link(link)
            if title is None or eps is None:
                return
            downloadPath = downloadPath0 + '/' + title + '/'
            st, ed = ep_select(eps)
            for i in range(st, ed):
                MovieFFM.Download_Request(eps[i], title + f" EP{i+1}", TMP, downloadPath)
        except Exception as e:
            print("Error:", str(e))
    elif linktype == 21:
        Anime1in.Download_Request(link, TMP, downloadPath0)
    elif linktype == 22:
        title, eps = Anime1in.Get_Title_Link(link)
        downloadPath = downloadPath0 + '/' + title + '/'
        try:
            st, ed = ep_select(eps)
            for i in range(st, ed):
                Anime1in.Download_Request(eps[i], TMP, downloadPath)
        except Exception as e:
            print("Error:", str(e))
    elif linktype == 23:
        TV777.Download_Request(link, TMP, downloadPath0)
    elif linktype == 24:
        try:
            title, eps = TV777.Get_Title_Link(link)
            if title is None or eps is None:
                return
            downloadPath = downloadPath0 + '/' + title + '/'
            st, ed = ep_select(eps)
            for i in range(st, ed):
                TV777.Download_Request(eps[i], TMP, downloadPath)
        except Exception as e:
            print("Error:", str(e))
    elif linktype == 19:
        Yanetflix.Download_Request(link, TMP, downloadPath0)
    elif linktype == 20:
        try:
            title, eps = Yanetflix.Get_Title_Link(link)
            if title is None or eps is None:
                return
            downloadPath = downloadPath0 + '/' + title + '/'
            st, ed = ep_select(eps)
            for i in range(st, ed):
                Yanetflix.Download_Request(eps[i], TMP, downloadPath)
        except Exception as e:
            print("Error:", str(e))

if __name__ == '__main__':

    # config
    TMP = (os.getcwd() + "/Tmp").replace('\\', '/')
    downloadPath0 = (os.getcwd() + "/Video").replace('\\', '/')
    Quality = "720"

    parser = argparse.ArgumentParser(
        description="Video downloader — pass a URL to download once, or run with no arguments for interactive mode."
    )
    parser.add_argument("url", nargs="?", default=None, help="直接輸入網址 (可選)")
    parser.add_argument("--all", dest="all", action="store_true", help="下載全部集數")
    parser.add_argument("--start", dest="start", type=int, default=None, metavar="N", help="從第 N 集開始 (1-based)")
    parser.add_argument("--end",   dest="end",   type=int, default=None, metavar="N", help="下載到第 N 集 (inclusive)")
    parser.add_argument("--source", dest="source", type=int, default=None, metavar="N", help="指定來源序號 (1-based)；未指定時列出可用來源後停止")
    args = parser.parse_args()

    if args.url:
        # One-shot mode: pre-set source selection on all modules that prompt for it
        cli_src = (args.source - 1) if args.source is not None else -1
        for M in [Dramasq, Gimy, Yanetflix, MovieFFM, Hanju, TV777]:
            M._cli_source_idx = cli_src
        run_download(args.url, TMP, downloadPath0, Quality,
                     arg_start=args.start, arg_end=args.end, arg_all=args.all)
    else:
        # Interactive loop (original behaviour)
        while True:
            link = input("網址:")
            if link == 'exit':
                break
            run_download(link, TMP, downloadPath0, Quality)
