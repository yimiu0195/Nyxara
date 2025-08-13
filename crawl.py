from bs4 import BeautifulSoup, Tag, NavigableString
import requests
import os
import regex as re
from Models import News
from Database.Database import session, Base, engine
from markdownify import markdownify as md
import time


def getAllNewsLink(url, headers):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    base = "https://en.toram.jp"
    news_links = []
    for li in soup.select("ul > li.news_border a[href]"):
        relative_url = li['href']
        full_url = base + relative_url
        news_links.append(full_url)
    return news_links

def extract_maintenance_schedule(box: Tag) -> str | None:
    """
    Extracts maintenance schedule text from the article box if found.
    Returns a markdown-formatted string or None.
    """
    raw = box.get_text("\n", strip=True)
    m = re.search(r'From:[^\n]+\n+Until:[^\n]+', raw, flags=re.I)
    if not m:
        return None
    return re.sub(r'\n+', '\n\n', m.group(0).strip())

def crawlNewsArticle(url, headers=None):
    r = requests.get(url, headers or {})
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    box  = soup.select_one("div.useBox.newsBox")

    title = box.select_one("h1.news_title").text.strip()
    date  = box.select_one("p.news_date time").text.strip()

    cat_tag  = box.select_one("div.infoDetailBox img[alt]")
    category = cat_tag["alt"].strip() if cat_tag else "en.toram.jp"

    # Remove <details> and irrelevant subtitles
    for d in box.select("details"):
        d.decompose()

    for subtitle in box.find_all("div", class_="subtitle"):
        if "item details" in subtitle.get_text(strip=True).lower():
            siblings_to_remove = []
            for sib in subtitle.next_siblings:
                if isinstance(sib, Tag):
                    if (sib.name == "div" and "subtitle" in sib.get("class", [])) or \
                       (sib.name == "h2" and "deluxetitle" in sib.get("class", [])):
                        break
                    siblings_to_remove.append(sib)
                elif isinstance(sib, NavigableString):
                    siblings_to_remove.append(sib)

            subtitle.decompose()
            for sib in siblings_to_remove:
                sib.decompose() if isinstance(sib, Tag) else sib.extract()

    # ---------- SECTION SPLITTING ---------- #

    

    sections = []
    for h2 in box.find_all("h2", class_="deluxetitle"):
        section_nodes = [h2]
        for sib in h2.next_siblings:
            if isinstance(sib, Tag) and sib.name == "h2" and "deluxetitle" in sib.get("class", []):
                break
            if isinstance(sib, Tag) and sib.name == "table":
                continue
            section_nodes.append(sib)

        section_html = "".join(str(n) for n in section_nodes)
        # section_html = re.sub(
        #     r'(<table[\s\S]*?</table>)',
        #     lambda m: f"<pre>{html_table_to_ascii(m.group(1))}</pre>",
        #     section_html
        # )
        section_md = md(section_html, heading_style="ATX")

        section_md = re.sub(r'[ \t]*\n[ \t]*', '\n', section_md)  
        section_md = re.sub(r'\n{2,}', '\n', section_md)
        section_md = re.sub(r'\[?Back to Top\]?\(?#top\)?', '', section_md, flags=re.IGNORECASE)
        section_md = re.sub(r'(?i)^back to top\s*$', '', section_md, flags=re.MULTILINE)
        section_md = section_md.strip()

        imgs = [
            img["src"]
            for img in BeautifulSoup(section_html, "html.parser").select("img[src]")
        ]

        sections.append({
            "title": h2.get_text(strip=True),
            "markdown": section_md,
            "images": imgs
        })
    if "maintenance notice" in title.lower():
        sched_md = extract_maintenance_schedule(box)
        if sched_md:
            sections.append({
                "title": "Maintenance Schedule",
                "markdown": sched_md,
                "images": []
            })

    seen, images = set(), []
    for img in box.select("img[src]"):
        src = img["src"]
        if src not in seen:
            images.append(src)
            seen.add(src)

    return {
        "url": url,
        "title": title,
        "date": date,
        "category": category,
        "images": images,
        "sections": sections
    }

# def crawlNewsArticle(url, headers=None):
#     r = requests.get(url, headers or {})
#     r.raise_for_status()

#     soup = BeautifulSoup(r.text, "html.parser")
#     box  = soup.select_one("div.useBox.newsBox")

#     title = box.select_one("h1.news_title").text.strip()
#     date  = box.select_one("p.news_date time").text.strip()

#     cat_tag  = box.select_one("div.infoDetailBox img[alt]")
#     category = cat_tag["alt"].strip() if cat_tag else "en.toram.jp"


#     for d in box.select("details"):
#         d.decompose()

#     for subtitle in box.find_all("div", class_="subtitle"):
#         if "item details" in subtitle.get_text(strip=True).lower():
#             siblings_to_remove = []
#             for sib in subtitle.next_siblings:
#                 if isinstance(sib, Tag):
#                     if (sib.name == "div" and "subtitle" in sib.get("class", [])) or \
#                     (sib.name == "h2" and "deluxetitle" in sib.get("class", [])):
#                         break
#                     siblings_to_remove.append(sib)
#                 elif isinstance(sib, NavigableString):
#                     siblings_to_remove.append(sib)

#             # cuối cùng xoá
#             subtitle.decompose()
#             for sib in siblings_to_remove:
#                 sib.decompose() if isinstance(sib, Tag) else sib.extract()

#     # ---------- SECTION SPLITTING ---------- #
#     sections = []
#     for h2 in box.find_all("h2", class_="deluxetitle"):
#         section_nodes = [h2]
#         for sib in h2.next_siblings:
#             if isinstance(sib, Tag) and sib.name == "h2" and "deluxetitle" in sib.get("class", []):
#                 break
#             section_nodes.append(sib)

#         section_html = "".join(str(n) for n in section_nodes)
#         section_md = md(section_html, heading_style="ATX")

#         section_md = re.sub(r'[ \t]*\n[ \t]*', '\n', section_md)  
#         section_md = re.sub(r'\n{2,}', '\n', section_md)

#         section_md = re.sub(r'\[?Back to Top\]?\(?#top\)?', '', section_md, flags=re.IGNORECASE)
#         section_md = re.sub(r'(?i)^back to top\s*$', '', section_md, flags=re.MULTILINE)

#         section_md = section_md.strip()


#         # Extract images for this section
#         imgs = [
#             img["src"]
#             for img in BeautifulSoup(section_html, "html.parser").select("img[src]")
#         ]

#         sections.append({
#             "title": h2.get_text(strip=True),
#             "markdown": section_md,
#             "images": imgs
#         })

#     # ---------- All images (entire article) ----------
#     seen, images = set(), []
#     for img in box.select("img[src]"):
#         src = img["src"]
#         if src not in seen:
#             images.append(src)
#             seen.add(src)

#     return {
#         "url": url,
#         "title": title,
#         "date": date,
#         "category": category,
#         "images": images,
#         "sections": sections
#     }



def crawlNewsAsJson(): ##doi thanh database roi
    db_file = "news_links.txt" ## se crawl nhung link khong co trong file nay
    seen_urls = set()
    if os.path.exists(db_file):
        with open(db_file, "r", encoding="utf-8") as f:
            seen_urls = set(line.strip() for line in f)
    new_links = []
    stop_flag = False

    newsHeader = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 OPR/119.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    links = []
    pages = 999
    for page in range(1, pages, 1):
        if stop_flag:
            break
        urlNews = f"https://en.toram.jp/information/?type_code=all&page={page}"
        links = getAllNewsLink(urlNews, newsHeader)
        for link in links:
            if link in seen_urls:
                stop_flag = True
            else:
                stop_flag = False
                print(f"[+] New: {link}")
                new_links.append(link)
                seen_urls.add(link)
        if new_links == []:
            break

    if new_links:
        with open(db_file, "a", encoding="utf-8") as f:
            for link in new_links:
                f.write(link + "\n")
        links = new_links
        for url in links:

            data = crawlNewsArticle(url, newsHeader)
            print(f"[+] Crawled: {data['title']}")
            info_id = url.split("information_id=")[-1]
            insert_news_article(data, info_id)

def insert_news_article(item, id):
    try:
        if session.query(News.NewsArticle).filter_by(url=item["url"]).first():
            print(f"Already exists: {item['url']}")
            return

        article = News.NewsArticle(
            id=id,
            url=item["url"],
            title=item["title"],
            date=item["date"],
            category=item["category"]
        )

        # Add article-level images
        for img_url in item.get("images", []):
            image = News.NewsImage(
                url=img_url,
                article=article
            )
            article.images.append(image)

        # Add sections with section-level images
        for section_item in item.get("sections", []):
            section = News.NewsSection(
                title=section_item["title"],
                markdown=section_item["markdown"],
                article=article
            )

            for section_img_url in section_item.get("images", []):
                section_image = News.NewsImage(
                    url=section_img_url,
                    article=article,
                    section=section
                )
                section.images.append(section_image)

            article.sections.append(section)

        session.add(article)
        session.commit()
        print(f"__________ SAVED: {item['title']} __________")
    except Exception as e:
        print("_____EXCEPTION_____")
        print(e)
        session.rollback()
        pass 
        ##skip duplicate

def main():
    Base.metadata.create_all(engine)
    doEveryXSec = 60
    schedule.every(doEveryXSec).seconds.do(crawlNewsAsJson)
    while True:
        schedule.run_pending()
        time.sleep(10)


import schedule
if __name__ == "__main__":
    main()
    
    
