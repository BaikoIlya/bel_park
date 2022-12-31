import asyncio
from pyppeteer import launch
from requests_html import AsyncHTMLSession
from functools import wraps

asession = AsyncHTMLSession()


def request_limit(limit=3):
    sem = asyncio.Semaphore(limit)

    def executor(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with sem:
                return await func(*args, **kwargs)
        return wrapper
    return executor


async def auto_scroll(page):
    scroll = 400
    scroll_progress = await page.evaluate('document.scrollingElement.scrollTop') + await page.evaluate("window.innerHeight")
    page_height = await page.evaluate('document.body.scrollHeight')
    while scroll_progress < page_height:
        print('Scrolling..')
        await page.evaluate(f"window.scrollBy(0, {scroll})")
        scroll_progress += scroll
        await page.waitFor(2000)
        page_height = await page.evaluate('document.body.scrollHeight')
    return page


@request_limit(limit=5)
async def get_links(sign):
    result = []
    browser = await launch({"headless": False, "args": ["--start-maximized"]})
    page = await browser.newPage()
    await page.setViewport({"width": 1600, "height": 900})
    await page.goto(f'https://park.by/residents/?first={sign}')
    await auto_scroll(page)
    companies = await page.querySelectorAll(".news-item > a")
    for company in companies:
        cmp_data = await company.getProperty('href')
        result.append(await cmp_data.jsonValue())
    await page.close()
    await browser.close()
    return result


async def get_email(url):
    r = await asession.get(url)
    try:
        email = r.html.search(r'Адрес электронной почты: {}<')
        return email[0].strip()
    except Exception as ex:
        print(f'{ex} у сайта {url}')


async def main():
    variations = [
        'A', 'Б', 'В', 'Г', 'Д', 'Е', 'Ж', 'З', 'И', 'К', 'Л', 'М', 'Н', 'О',
        'П', 'Р', 'С', 'Т', 'У', 'Ф', 'Х', 'Ц', 'Ч', 'Ш', 'Э', 'Ю', 'Я'
    ]
    pyppeteer_tasks = []
    for sign in variations:
        p_t = asyncio.create_task(get_links(sign))
        pyppeteer_tasks.append(p_t)
    results = await asyncio.gather(*pyppeteer_tasks)
    tasks = []
    for letter_links in results:
        for url in letter_links:
            print(url)
            t = asyncio.create_task(get_email(url))
            tasks.append(t)
    res = await asyncio.gather(*tasks)
    result = [el for el in res if el is not None]
    with open('email.txt', 'w', encoding="utf-8") as file:
        for el in result:
            file.write(el + '\n')


asyncio.get_event_loop().run_until_complete(main())
