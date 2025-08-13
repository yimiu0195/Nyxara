import os, json, asyncio, re, discord
from discord.ext import commands
from discord.ui import View, Button
from dotenv import load_dotenv

from Models import News 
from Database.Database import *


load_dotenv()

TOKEN       = os.environ["TOKEN"]
SERVER_ID   = int(os.environ["SERVER_ID"])
CHANNEL_ID  = int(os.environ["CHANNEL_ID"])


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

def remove_anchor_toc_block(md: str) -> str:
    lines, out, skipping = md.splitlines(), [], False
    for line in lines:
        strip = line.strip()
        if not skipping and "tap here to check" in strip.lower():
            skipping = True
            continue
        if skipping:
            if strip.startswith("##") or strip.startswith("!") or (
                strip and not re.match(r"\[?.+?\]?\(?#.+?\)?", strip)
            ):
                skipping = False
            else:
                continue
        out.append(line)
    return "\n".join(out)

def remove_all_internal_links(md: str) -> str:
    md = re.sub(r'\[([^\]]+)\]\(#[^)]+\)', r'\1', md)
    md = re.sub(r'^\s*\[.*?\]\(#[^)]+\)\s*$', '', md, flags=re.MULTILINE)
    return md

def remove_all_image_markdown(md_text: str) -> str:
    return re.sub(r'!\[.*?\]\(.*?\)', '', md_text)

def strip_title_from_md(md_text: str) -> str:
    return re.sub(r'^#{1,6}\s+.*\n', '', md_text, count=1).lstrip()

async def send_article_embed(channel, article_id: int):
    try:
        # with open(path, encoding="utf-8") as f:
        #     article = json.load(f)
        article = get_article_from_db(article_id)
    except FileNotFoundError:
        await channel.send(f"❌ Article `{article_id}` not found.")
        return


    if "sections" not in article:
        article["sections"] = [{
            "title":    article["title"],
            "markdown": article["markdown"],
            "images":   article.get("images", [])
        }]
    

    for i, sec in enumerate(article["sections"], start=1):
        md_text = sec["markdown"]
        md_text = remove_anchor_toc_block(md_text)
        md_text = remove_all_internal_links(md_text)
        md_text = remove_all_image_markdown(md_text)
        md_text = strip_title_from_md(md_text).strip()

        embed = discord.Embed(
            title=sec["title"],
            url=article["url"],
            description=md_text[:4096],
            color=discord.Color.dark_gold()
        )


        if sec["images"]:
            embed.set_image(url=sec["images"][0])

        embed.set_footer(
            text=f"📅 {article['date']} • 🏷️ {article['category']} • Part {i}/{len(article['sections'])}"
        )

        await channel.send(embed=embed)
        await asyncio.sleep(1)

# === Commands ===
@bot.command(aliases=["news"])
async def doNews(ctx, article_id: int):
    await send_article_embed(ctx.channel, article_id)

def get_article_from_db(article_id: int):
    try:
        article = session.query(News.NewsArticle).filter_by(id=article_id).first()
        if not article:
            return None

        section_images = {}
        article_images = []

        for image in article.images:
            print(image.section_id)
            if image.section_id == '':
                article_images.append(image.url)  # article-level images
            elif image.section_id != None:
                
                section_images.setdefault(image.section_id, []).append(image.url)

        with open("test.json", "w", encoding="utf-8") as file:
            json.dump(section_images, file, ensure_ascii=False, indent=2)
            

        sections_data = []
        for section in article.sections:
            sections_data.append({
                "title": section.title,
                "markdown": section.markdown,
                "images": section_images.get(section.id, [])
            })

        with open("test2.json", "w", encoding="utf-8") as file:
            json.dump(sections_data, file, ensure_ascii=False, indent=2)

        return {
            "title": article.title,
            "url": article.url,
            "date": article.date,
            "category": article.category,
            "images": article_images,
            "sections": sections_data
        }
    finally:
        session.close()

def get_last_article_id_from_db():
    try:
        last_article = session.query(News.NewsArticle).order_by(News.NewsArticle.id.desc()).first()
        return last_article.id if last_article else 0
    finally:
        session.close()

last_sent_article_id = get_last_article_id_from_db()

async def watch_new_articles(channel):
    global last_sent_article_id
    await asyncio.sleep(2)  # small delay to wait for bot ready

    while True:
        try:
            # Fetch articles newer than the last sent one
            new_articles = (
                session.query(News.NewsArticle)
                .filter(News.NewsArticle.id > last_sent_article_id)
                .order_by(News.NewsArticle.id)
                .all()
            )

            for article in new_articles:
                print(f"[DEBUG] Sending new article from DB: {article.id}")
                await send_article_embed(channel, article.id)
                last_sent_article_id = article.id
                await asyncio.sleep(1)  # prevent Discord rate limits

            session.close()
        except Exception as e:
            print(f"Polling error: {type(e).__name__}: {e}")
        await asyncio.sleep(5) 

# === Ready Event ===
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    channel = await bot.fetch_channel(CHANNEL_ID)
    # if channel:
    #     watcher = ArticleWatcher(bot, channel, ARTICLE_DIR, send_article_embed)
    #     from watchdog.observers import Observer
    #     observer = Observer()
    #     observer.schedule(watcher, path=ARTICLE_DIR, recursive=False)
    #     observer.start()
    #     print("🟢 Watching for new articles...")
    # else:
    #     print("❌ Cannot find channel to send article notifications.")
    if channel:
        bot.loop.create_task(watch_new_articles(channel))
        print("🟢 Watching for new DB articles...")
    else:
        print("❌ Cannot find channel to send article notifications.")

# === Run ===
if __name__ == "__main__":
    bot.run(TOKEN)
