
() => {
    const selectors = "a, [role='link'], button, [onclick], [role='button'], [role='radiogroup'], input, textarea, select";
    const elements = Array.from(document.querySelectorAll(selectors));

    return elements.map((el, i) => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);

        const visible =
            rect.width > 0 &&
            rect.height > 0 &&
            style.visibility !== "hidden" &&
            style.display !== "none";


        let type = "element";
        const tag = el.tagName.toLowerCase();

        if (!visible) return null;

        if (tag === "a") type = "link";
        else if (tag === "button" || el.getAttribute("role") === "button") type = "button";
        else if (el.getAttribute("role") === "radiogroup") type = "radiogroup";
        else if (tag === "input" || tag === "textarea" || tag === "select") type = "form";
        else if (el.getAttribute("onclick") || el.onclick) type = "clickable";
        else type = "other";


        const label =
            (el.innerText || el.textContent || "").trim() ||
            el.getAttribute("aria-label") ||
            el.placeholder ||
            el.getAttribute("alt") ||
            el.getAttribute("title") ||
            "";

        return {
            id: i,
            tag,
            type,
            label,
            href: el.href || null,
        };
    })
    .filter(e => e !== null);
}