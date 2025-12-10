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

    // 3. Extract Post URL (Logic: Body External Link > First Comment Link > Permalink)
    let postUrl = "Unknown URL";
    let externalLinkFound = false;

    // Helper to finding valid external link in a container
    // Helper to finding valid external link in a container
    const findExternalLink = (container) => {
        if (!container) return null;
        // Select all anchor tags
        const links = container.querySelectorAll('a');
        for (let link of links) {
            const href = link.href;

            // --- New Condition ---
            // Skip internal LinkedIn links (profiles, company pages, hashtags)
            if (href.includes("linkedin.com") || href.includes("hashtag")) {
                continue;
            }

            // If we are here, it's likely an external link!
            return href;
        }

        // If no external link found, we return null to let the next strategy take over (e.g. comments or permalink)
        // NOTE: The user requested "return window.location.href" as default, but in this specific helper function context, 
        // returning 'null' is better because we have fallback strategies (Strategy B, Strategy C). 
        // Strategy C eventually sets the URL to the permalink. 
        // HOWEVER, to strictly follow the user request for *this specific function* logic:
        return window.location.href;
    };

    // Strategy A: Check Post Body for External Link
    const descriptionBox = postContainer.querySelector('.feed-shared-update-v2__description, .update-components-text, .feed-shared-text');
    if (descriptionBox) {
        const bodyLink = findExternalLink(descriptionBox);
        if (bodyLink) {
            postUrl = bodyLink;
            externalLinkFound = true;
        }
    }

    // Strategy B: Check First Comment for External Link (if Strategy A failed)
    if (!externalLinkFound) {
        try {
            // Attempt to find the comments section. 
            // Note: This relies on comments being loaded in the DOM.
            // We search for the comments list container.
            const commentsList = postContainer.querySelector('.comments-comment-list, .feed-shared-update-v2__comments-list');

            if (commentsList) {
                // Get ALL comments, not just the first one
                const allComments = commentsList.querySelectorAll('.comments-comment-item, article.comments-comment-item');

                for (let comment of allComments) {
                    // Check Author Match
                    let commentAuthorName = "";
                    const commentAuthorEl = comment.querySelector('.comments-post-meta__name-text, .comments-comment-meta__description-title');

                    if (commentAuthorEl) {
                        commentAuthorName = commentAuthorEl.innerText.trim().split('\n')[0];
                    }

                    // Exact match or normalize and compare
                    const normalizedCommentAuthor = commentAuthorName.toLowerCase().trim();
                    const normalizedPostAuthor = authorName.toLowerCase().trim();

                    // We check if comment author INCLUDES post author (or vice versa) to be robust
                    if (normalizedCommentAuthor && normalizedPostAuthor && (normalizedCommentAuthor.includes(normalizedPostAuthor) || normalizedPostAuthor.includes(normalizedCommentAuthor))) {

                        // Look for link in comment body
                        const commentBody = comment.querySelector('.comments-comment-item__main-content, .feed-shared-main-content--comment');
                        const commentLink = findExternalLink(commentBody);

                        if (commentLink) {
                            postUrl = commentLink;
                            externalLinkFound = true;
                            break; // Stop after finding the first valid link from the author
                        }
                    }
                }
            }
        } catch (err) {
            console.warn("Error checking comments:", err);
        }
    }
    // Strategy C: Fallback to LinkedIn Permalink (URN)
    if (!externalLinkFound) {
        const urn = postContainer.getAttribute('data-urn');
        if (urn) {
            postUrl = `https://www.linkedin.com/feed/update/${urn}`;
        } else {
            // Last resort: timestamp link
            const timeLink = postContainer.querySelector('a.update-components-actor__sub-description, a.feed-shared-actor__sub-description');
            if (timeLink && timeLink.href) {
                postUrl = timeLink.href.split('?')[0];
            }
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
