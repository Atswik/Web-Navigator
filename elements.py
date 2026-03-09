import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import re
import time

async def run_js(page, script_file):
    script = Path(script_file).read_text()
    return await page.evaluate(script)

class Navigator:
    def __init__(self, user_prompt, base_url):
        self.user_prompt = user_prompt
        self.base_url = base_url
        self.current_url = base_url
        self.previous_urls = []

        self.playwright = None
        self.browser = None
        self.page = None

    async def benchmark(self):
        runs = 10
        old_times = []
        new_times = []

        for _ in range(runs):
            start = time.perf_counter()
            await self.extract_links()
            old_times.append(time.perf_counter() - start)

        for _ in range(runs):
            start = time.perf_counter()
            await self.extract_links_javascript()
            new_times.append(time.perf_counter() - start)

        print(f"Average of extract_links: {sum(old_times) / runs:.4f}")
        print(f"Average of extract_links_javascript: {sum(new_times) / runs:.4f}")


    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.webkit.launch(headless=False)
        self.page = await self.browser.new_page()
        print("\nUser prompt:", self.user_prompt)
        print(f"\nNavigating to base URL: {self.base_url}")
        await self.page.goto(self.base_url, wait_until="networkidle")

    async def get_labels(self, el, default_value="[No Label]"):

        js_script = """
        el => {
            return {
                innerText: el.innerText,
                placeholder: el.getAttribute('placeholder'),
                ariaLabel: el.getAttribute('aria-label'),
                alt: el.getAttribute('alt'),
                name: el.getAttribute('name') || el.getAttribute('data-label'),
                title: el.getAttribute('title') || el.getAttribute('data-analytics-title'),
                value: el.getAttribute('value'),
            };
        }
        """

        attrs = await el.evaluate(js_script)
        priority_order = [
            attrs.get("ariaLabel"),
            attrs.get("innerText"),
            attrs.get("alt"),
            attrs.get("placeholder"),
            attrs.get("title"),
            attrs.get("name"),
            attrs.get("value"),
        ]

        for label in priority_order:
            if label and label.strip():
                return re.sub(r"\s+", " ", label).strip()

        return default_value

    async def get_label(self, el):
        text = (await el.inner_text()).strip() or None
        placeholder = await el.get_attribute("placeholder") or None
        aria_label = await el.get_attribute("aria-label") or None
        alt = await el.get_attribute("alt") or None
        role = await el.get_attribute("role") or None
        name = await el.get_attribute("name") or await el.get_attribute("data-label")
        title = await el.get_attribute("title") or await el.get_attribute(
            "data-analytics-title"
        )
        value = await el.get_attribute("value") or None

        parts = [text, placeholder, aria_label, alt, role, name, title, value]
        parts = [p for p in parts if p is not None]

        label = " ".join(parts)

        return label
        return (
            text
            or placeholder
            or aria_label
            or alt
            or role
            or name
            or title
            or value
            or "[No Label]"
        )

    async def extract_links(self):
        actions = []
        seen_href = set()
        selectors = [
            "a",
            "[role=link]",
            "button",
            "[onclick]",
            "[role=button]",
            "[role=radiogroup]",
            "input",
            "textarea",
            "select",
        ]

        for selector in selectors:
            elements = await self.page.query_selector_all(selector)
            for el in elements:
                tag = (await el.evaluate("el => el.tagName")).lower()
                label = await self.get_labels(el)
                href = await el.get_attribute("href")
                onclick = await el.get_attribute("onclick")
                input_type = await el.get_attribute("type") if tag == "input" else None

                if tag == "a":
                    element_type = "link"
                elif tag == "button" or selector == "[role=button]":
                    element_type = "button"
                elif tag == "input":
                    element_type = f"input ({input_type})"
                elif onclick is not None:
                    element_type = "clickable element"
                else:
                    element_type = label

                if href not in seen_href:
                    actions.append(
                        {
                            "type": element_type,
                            "label": label,
                            "href": href,
                        }
                    )
                    seen_href.add(href)

        return actions

    async def extract_links_javascript(self):
        elements = await run_js(self.page, "js/extract_elements.js")
        actions = []
        seen_href = set()

        for el in elements:
            href = el["href"]
            if href and href in seen_href:
                continue

            actions.append(el)
            if href:
                seen_href.add(href)

        return actions


baseURL = "https://www.apple.com/shop/buy-airpods/airpods-pro-3"
prompt = "Give me links"
nav = Navigator(prompt, baseURL)
nav.start()

async def main(prompt=None, url=None):
    nav = Navigator(prompt, url)
    await nav.start()

    await nav.benchmark()

    # links = await nav.extract_links_javascript()
    # for link in links:
    #     print(f"{link['type']}: {link['label']} -> {link['href']}\n")


asyncio.run(main(prompt, baseURL))
