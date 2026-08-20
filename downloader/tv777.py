from utils import *
from urllib.parse import urlparse, unquote
import base64

class TV777:
    _selected_source_idx = None  # None = single-ep mode (prompt), int = batch mode (skip prompt)
    _cli_source_idx = None  # -1=list+stop, >=0=pre-selected (set by CLI before download)

    def Link_Validate(site):
        TV777._selected_source_idx = None
        if '/vod/play/' in site:
            return 23  # single episode
        if '/vod/detail/' in site:
            return 24  # series detail
        return 0

    def _abs_url(href):
        """Site hrefs are protocol-relative (//play.777tv.ai/...)."""
        if href.startswith('//'):
            return 'https:' + href
        if href.startswith('/'):
            return 'https://play.777tv.ai' + href
        return href

    def _Extract_Sources(soup):
        """Parse play/detail page → list of (source_name, [(label, url), ...]).
        Structure: div.stui-pannel > div.stui-pannel__head > h4.title
                                   > ul.stui-content__playlist > li > a
        Non-playlist panels (描述/猜你喜歡) use other ul classes and are skipped.

        The entry label is 第NN集 for series but a quality/language variant for
        movies (HD中字 / HD / 高清), and the entry count differs per 線路, so the
        label is kept for display rather than assuming positional episodes.
        """
        sources = []
        for panel in soup.select('div.stui-pannel'):
            h4 = panel.select_one('h4.title')
            ul = panel.select_one('ul.stui-content__playlist')
            if not h4 or not ul:
                continue
            name = h4.get_text(strip=True)
            entries = [(a.get_text(strip=True), TV777._abs_url(a['href']))
                       for a in ul.find_all('a', href=True) if '/vod/play/' in a['href']]
            if entries:
                sources.append((name, entries))
        return sources

    def _Clean_Title(raw):
        """'祕密關係臺版第03集線上看 - 小鴨影音' → '祕密關係臺版第03集'"""
        title = raw.split(' - ')[0].strip()
        return re.sub(r'線上看$', '', title).strip()

    def _Get_Player_Data(html):
        """Extract the inline `var player_data={...}` object from a play page."""
        m = re.search(r'var\s+player_data\s*=\s*(\{.*?\})\s*</script>', html, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(1).replace('\\/', '/'))
        except json.JSONDecodeError:
            return None

    def _Decode_Url(url, encrypt):
        """MacCMS encrypt modes: 0=plain, 1=urldecode, 2=base64 then urldecode."""
        try:
            if encrypt == 1:
                return unquote(url)
            if encrypt == 2:
                return unquote(base64.b64decode(url).decode('utf-8'))
            return url
        except Exception:
            return None

    def _Get_M3u8_Url(html):
        """Return the m3u8 URL carried by player_data on a play page."""
        data = TV777._Get_Player_Data(html)
        if not data:
            return None
        url = TV777._Decode_Url(data.get('url', ''), data.get('encrypt', 0))
        if not url or not url.startswith('http'):
            return None
        return url

    def _Get_M3u8_Url_From_Page(ep_url):
        r = requests.get(ep_url, headers=global_headers, timeout=15)
        return TV777._Get_M3u8_Url(r.content.decode('utf-8'))

    def _resolve_url(base_url, path):
        if path.startswith('http'):
            return path
        if path.startswith('/'):
            p = urlparse(base_url)
            return f"{p.scheme}://{p.netloc}{path}"
        return '/'.join(base_url.split('/')[:-1]) + '/' + path

    def _Resolve_Sub_M3u8(m3u8_url, content=None):
        """Fetch m3u8, return (content, final_url) — resolves master→sub if needed."""
        if content is None:
            r = requests.get(m3u8_url, headers=global_headers, timeout=15)
            content = r.text
        sub_match = re.search(r'^(?!#)([^\s]+\.m3u8)', content, re.MULTILINE)
        if sub_match:
            sub_url = TV777._resolve_url(m3u8_url, sub_match.group(1))
            r2 = requests.get(sub_url, headers=global_headers, timeout=30)
            return r2.text, sub_url
        return content, m3u8_url

    def _Fetch_Chunklist(m3u8_url, TMP):
        """Fetch m3u8, resolve master playlist if needed, return chunklist.
        Several 線路 advertise CDNs that are unreachable — treat that as an
        unusable source rather than letting the connection error propagate."""
        tmpPath = TMP + '/gimy'
        if not os.path.isdir(tmpPath):
            os.makedirs(tmpPath)
        try:
            content, final_url = TV777._Resolve_Sub_M3u8(m3u8_url)
        except requests.RequestException as e:
            print(f"來源無法連線: {e.__class__.__name__}")
            return None
        return Parse_m3u8(TMP, content, final_url)

    def Resolution_Check(sources_with_urls, TMP):
        """Parallel resolution check. sources_with_urls = [(name, ep_url), ...]
        Several 線路 point at dead CDNs, so this doubles as an availability check."""
        preview_path = TMP + '/preview'
        if not os.path.isdir(preview_path):
            os.makedirs(preview_path)

        def check_one(i, ep_url):
            try:
                m3u8_url = TV777._Get_M3u8_Url_From_Page(ep_url)
                if not m3u8_url:
                    return i, '(Invalid)'
                r = requests.get(m3u8_url, headers=global_headers, timeout=10)
                content = r.text
                # Exact resolution from master playlist when advertised
                res_match = re.search(r'RESOLUTION=(\d+x\d+)', content)
                if res_match:
                    return i, f"({res_match.group(1)})"
                # Otherwise estimate from first chunk size x total chunks
                sub_content, sub_url = TV777._Resolve_Sub_M3u8(m3u8_url, content)
                chunk_lines = [l.strip() for l in sub_content.split('\n')
                               if l.strip() and not l.startswith('#')]
                total_chunks = len(chunk_lines)
                if not chunk_lines:
                    return i, '(Invalid)'
                first_chunk = TV777._resolve_url(sub_url, chunk_lines[0])
                download_chunk(first_chunk, i, preview_path, timeout=10, retry=1)
                ts_path = f"{preview_path}/{i}.ts"
                if not os.path.isfile(ts_path) or os.path.getsize(ts_path) == 0:
                    return i, '(Invalid)'
                quality = Get_Video_Resolution(ts_path, total_chunks)
                return i, f"({quality})"
            except Exception as e:
                if DEBUG: print(f"Debug: Resolution check failed for source {i}: {e}")
                return i, '(Invalid)'

        results = ['(Invalid)'] * len(sources_with_urls)
        with concurrent.futures.ThreadPoolExecutor(len(sources_with_urls)) as ex:
            futures = [ex.submit(check_one, i, u) for i, (n, u) in enumerate(sources_with_urls)]
            for f in concurrent.futures.as_completed(futures):
                i, label = f.result()
                results[i] = label
        return results

    def _Prompt_Source(sources, TMP, labels=None):
        """Show sources with optional resolution check, return selected index.
        sources: list whose first element is the display name.
        labels: [(name, first_ep_url)] used for the resolution probe."""
        if TV777._cli_source_idx == -1:
            print('\n'.join([f"{i+1}.{s[0]}" for i, s in enumerate(sources)]))
            print("請使用 --source N 指定來源")
            return None
        if TV777._cli_source_idx is not None:
            idx = TV777._cli_source_idx
            if idx >= len(sources):
                print(f"來源 {idx+1} 超出範圍 (共 {len(sources)} 個)")
                return None
            print(f"使用來源: {sources[idx][0]}")
            return idx

        res_check = input("檢查畫質(1:是 2:否): ").strip()
        if res_check == '1':
            print("檢查畫質...")
            resolutions = TV777.Resolution_Check(labels, TMP)
            showStr = '\n'
            for i, s in enumerate(sources):
                showStr += f"{i+1}.{s[0]} {resolutions[i]}\n"
            print(showStr)
        else:
            print('\n'.join([f"{i+1}.{s[0]}" for i, s in enumerate(sources)]))
        sel = input(f"選擇來源(1~{len(sources)}): ").strip()
        if not sel:
            print("未選擇來源")
            return None
        return int(sel) - 1

    def Get_Title_Link(site, get_link=True):
        TMP = (os.getcwd() + "/Tmp").replace('\\', '/')
        r = requests.get(site, headers=global_headers, timeout=15)
        html = r.content.decode('utf-8')
        soup = bs(html, 'html.parser')

        title_tag = soup.find('title')
        if not title_tag:
            return None, None

        if '/vod/play/' not in site:
            # Series detail page: /vod/detail/id/{id}.html
            h1 = soup.find('h1')
            title = h1.get_text(strip=True) if h1 else ''
            if not title:
                title = TV777._Clean_Title(title_tag.get_text())
            if not title:
                return None, None
            if not get_link:
                return FileNameClean(title), 2

            sources = TV777._Extract_Sources(soup)
            if not sources:
                print("No sources found")
                return None, None
            # Entry counts differ per 線路, so show them alongside the name
            display = [(f"{name} ({len(entries)}集)", entries) for name, entries in sources]
            # Probe each 線路 with its own first entry
            probes = [(name, entries[0][1]) for name, entries in sources]
            idx = TV777._Prompt_Source(display, TMP, probes)
            if idx is None:
                return None, None
            TV777._selected_source_idx = idx
            return FileNameClean(title), [u for _, u in sources[idx][1]]

        # Episode player page: /vod/play/id/{id}/sid/{sid}/nid/{nid}.html
        title = TV777._Clean_Title(title_tag.get_text())
        if not title:
            data = TV777._Get_Player_Data(html)
            if data:
                title = data.get('vod_data', {}).get('vod_name', '')
        if not title:
            return None, None
        if not get_link:
            return FileNameClean(title), 1

        if TV777._selected_source_idx is None:
            # Single episode mode: the play page carries the full playlist for
            # every 線路, so pick the matching episode from each without refetching.
            nid_m = re.search(r'/nid/(\d+)', site)
            nid = nid_m.group(1) if nid_m else None
            sources = TV777._Extract_Sources(soup)
            if not sources or not nid:
                m3u8_url = TV777._Get_M3u8_Url(html)
            else:
                # Prefer the same nid on every 線路, but entry counts differ
                # (a movie's 2nd entry is a variant some 線路 don't carry), so
                # fall back to the first entry instead of dropping the source.
                choices = []
                for name, entries in sources:
                    match = next((e for e in entries
                                  if re.search(rf'/nid/{nid}\.html$', e[1])), None)
                    if match:
                        label, ep_url = match
                    else:
                        label, ep_url = entries[0]
                        label += ' ※無對應項，改用第1項'
                    choices.append((f"{name} - {label}", ep_url))
                idx = TV777._Prompt_Source(choices, TMP, choices)
                if idx is None:
                    return None, None
                picked_url = choices[idx][1]
                if picked_url == site:
                    m3u8_url = TV777._Get_M3u8_Url(html)
                else:
                    m3u8_url = TV777._Get_M3u8_Url_From_Page(picked_url)
        else:
            # Batch mode: URL already points at the chosen 線路
            m3u8_url = TV777._Get_M3u8_Url(html)

        if not m3u8_url:
            print("player_data url not found")
            return None, None
        return FileNameClean(title), TV777._Fetch_Chunklist(m3u8_url, TMP)

    def Download_Request(site, TMP, downloadPath):
        tmpPath = TMP + '/gimy'
        tmpfile = tmpPath + '/0.m3u8'
        if not os.path.isdir(tmpPath):
            os.makedirs(tmpPath)
        if not os.path.isdir(downloadPath):
            os.makedirs(downloadPath)

        title, chunks = TV777.Get_Title_Link(site)
        if not chunks or not title:
            print("Connection Failed. Source may be invalid!")
            if DEBUG: print(f"Debug: title='{title}', chunks='{chunks}'\n")
            return False
        print(title)

        if Download_Chunks(chunks, TMP):
            return False

        if MP4convert(tmpfile, downloadPath + '/' + title + '.mp4'):
            return False

        shutil.rmtree(tmpPath)
        return True
