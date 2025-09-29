
from playwright.async_api import async_playwright
from similarity_local import compute_similarity
from similarity_OpenAI import compute_similarity_open
import asyncio
import re

class Navigator:
    def __init__(self, user_prompt, base_url):
        self.user_prompt = user_prompt
        self.base_url = base_url
        self.current_url = base_url
        self.previous_urls = []

        self.playwright = None
        self.browser = None
        self.page = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.webkit.launch(headless=False)
        self.page = await self.browser.new_page()
        print("\nUser prompt:", self.user_prompt)
        print(f"\nNavigating to base URL: {self.base_url}")
        await self.page.goto(self.base_url, wait_until="networkidle")

    async def link_deconstruct(self, link):
        # print(link)
        return None
        
    async def navigate_to_url(self, url):
        await self.page.goto(url, wait_until="networkidle")
        self.current_url = url
        # self.previous_urls.append(url)
        print(f"Page title: {await self.page.title()}")

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
            attrs.get('ariaLabel'),
            attrs.get('innerText'),
            attrs.get('alt'),
            attrs.get('placeholder'),
            attrs.get('title'),
            attrs.get('name'),
            attrs.get('value'),
        ]

        await self.link_deconstruct(el.get_attribute("href"))

        for label in priority_order:
            if label and label.strip():
                return re.sub(r'\s+', ' ', label).strip()
            
        return default_value

    async def get_label(self, el):
        text = (await el.inner_text()).strip() or None
        placeholder = await el.get_attribute("placeholder") or None
        aria_label = await el.get_attribute("aria-label") or None
        alt = await el.get_attribute("alt") or None
        role = await el.get_attribute("role") or None
        name = await el.get_attribute("name") or await el.get_attribute("data-label")
        title = await el.get_attribute("title") or await el.get_attribute("data-analytics-title")
        value = await el.get_attribute("value") or None

        parts = [text, placeholder, aria_label, alt, role, name, title, value]
        parts = [p for p in parts if p is not None]

        label = " ".join(parts)

        return label
        return text or placeholder or aria_label or alt or role or name or title or value or "[No Label]"
    
    async def extract_links(self):
        actions = []
        seen_href = set()
        selectors = ["a", "[role=link]", "button", "[onclick]", "[role=button]", "[role=radiogroup]", "input", "textarea", "select"]

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
                    actions.append({
                        "type": element_type,
                        "label": label,
                        "href": href,
                    })
                    seen_href.add(href)
        
        return actions
  

async def main(prompt=None, url=None):
    nav = Navigator(prompt, url)
    await nav.start()
    navigate = True
    while navigate:
        next_url = None
        links = await nav.extract_links()
        print(f"\nAnalysing {len(links)} links...")

        similarities_local = compute_similarity(nav.user_prompt, links)
        scored = list(zip(links, similarities_local))
        scored.sort(key=lambda x: x[1], reverse=True)        

        print("\nTop 10 navigation candidates based on local embeddings:")
        for link, sim in scored[:10]:
            print(f"Similarity: {sim:.4f} - Element: {link}")

        break

        filtered_scored = [(link, score) for link, score in scored[:10] if link['href'] not in nav.previous_urls]
        
        similarities_OpenAI = compute_similarity_open(nav.user_prompt, filtered_scored)
        new_scored = list(zip([link for link, old_score in scored[:10]], similarities_OpenAI))
        new_scored.sort(key=lambda x: x[1], reverse=True)

        print("\nAfter re-ranking with OpenAI embeddings:")
        for link, sim in new_scored[:10]:
            print(f"Similarity: {sim:.4f} - Element: {link}")

        next_step = new_scored[0][0]
        
        match next_step['type']:
            case "link":
                if next_step['href'] is None:
                    print("No href found, stopping navigation.")
                    break
                if next_step['href'].startswith("#"):
                    next_url = nav.current_url + next_step['href']
                elif next_step['href'].startswith("//"):
                    next_url = "https:" + next_step['href']
                elif next_step['href'].startswith("/"):
                    next_url = nav.base_url + next_step['href']
                elif next_step['href'].startswith("http"):
                    next_url = next_step['href']

                
        
                if next_url in nav.previous_urls:
                    print("Already visited this URL, stopping navigation.") # Avoiding loops
                    break

                nav.previous_urls.append(next_step['href'])
                print(f"\nNavigating to: {next_url} with similarity score: {new_scored[0][1]}")
               
                await nav.navigate_to_url(next_url)
            
            case "button":
                print("Next best element is a button. Limited support for button navigation, stopping.")
                break
            case _:
                print("No suitable navigation element found, stopping.")
                break
        
    print("Navigation complete.")


if __name__ == "__main__":
    base_url = "https://www.apple.com"
    base_url = "https://www.apple.com/shop/buy-airpods/airpods-pro-3"
    while True:
        user_prompt = input("Enter your navigation prompt (or 'exit' to quit): ")
        if user_prompt.lower() == 'exit':
            break
    
        asyncio.run(main(user_prompt, base_url))

