// content.js - Robust LinkedIn Scraper

let lastRightClickedElement = null;

// Track the element that was right-clicked
document.addEventListener("contextmenu", (event) => {
    lastRightClickedElement = event.target;
}, true);

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "scrapePost") {
        try {
            const data = extractPostData(lastRightClickedElement);
            sendResponse({ data: data });
        } catch (e) {
            console.error("Scraping error:", e);
            sendResponse({ data: null, error: e.toString() });
        }
    }
    return true;
});

function extractPostData(target) {
    if (!target) return null;

    // 1. Locate the Post Container
    // LinkedIn DOM uses 'feed-shared-update-v2' widely.
    // We also check for 'occludable-update' (virtualized list item).
    // We explicitly look for a container that has a 'data-urn' because that gives us the ID.
    const postContainer = target.closest('.feed-shared-update-v2, .occludable-update, [data-urn]');

    if (!postContainer) {
        console.warn("Could not find post container. User might have clicked outside a post.");
        return null;
    }

    // 2. Extract Author
    // Strategy A: 'update-components-actor__name' (Standard feed)
    // Strategy B: 'update-components-actor__title' (Sometimes used)
    // Strategy C: Aria label or Alt text of the avatar
    let authorName = "Unknown Author";

    const authorSelectors = [
        '.update-components-actor__name',
        '.update-components-actor__title span[dir="ltr"]',
        '.feed-shared-actor__name'
    ];

    for (let sel of authorSelectors) {
        const el = postContainer.querySelector(sel);
        if (el) {
            authorName = el.innerText.split('\n')[0].trim(); // Split to remove 'View profile' hidden text
            if (authorName) break;
        }
    }

    // 3. Extract Post URL
    // Strategy A: 'data-urn' attribute on the container (Most reliable)
    // Strategy B: Link in the timestamp
    let postUrl = "Unknown URL";
    const urn = postContainer.getAttribute('data-urn');
    if (urn) {
        // urn format: urn:li:activity:712345... or urn:li:share:71234...
        // LinkedIn allows accessing via /feed/update/{urn}
        postUrl = `https://www.linkedin.com/feed/update/${urn}`;
    } else {
        // Try finding the timestamp link
        const timeLink = postContainer.querySelector('a.update-components-actor__sub-description, a.feed-shared-actor__sub-description');
        if (timeLink && timeLink.href) {
            postUrl = timeLink.href.split('?')[0]; // Remove tracking params
        }
    }

    // 4. Extract Text Content
    // Strategy A: '.feed-shared-update-v2__description'
    // Strategy B: '.update-components-text'
    let postText = "";
    const textContainer = postContainer.querySelector('.feed-shared-update-v2__description, .update-components-text, .feed-shared-text');

    if (textContainer) {
        // LinkedIn hides text behind "...more". 
        // We grab what is visible. 
        // NOTE: We do NOT programmatically click "more" to avoid race conditions or page jumps, 
        // unless specifically requested. For now, innerText is the safest non-intrusive approach.
        postText = textContainer.innerText.trim();
    } else {
        // Fallback: Use the whole container text if description is missing (e.g. image only post?)
        // But we risk getting comments. Better to return empty than junk.
        postText = "[Image/Video Post or Text not found]";
    }

    return {
        text: postText,
        author: authorName,
        url: postUrl
    };
}
