// background.js

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "saveToBrain",
    title: "Save to Knowledge Base",
    contexts: ["all"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "saveToBrain") {

    // 1. Send message to content script to scrape data
    chrome.tabs.sendMessage(tab.id, { action: "scrapePost" }, async (response) => {

      // Handle connection errors (e.g., content script not loaded)
      if (chrome.runtime.lastError) {
        console.error("Communication error:", chrome.runtime.lastError.message);
        alertUser(tab.id, "Error: Reload the page and try again.");
        return;
      }

      if (response && response.data) {
        // 2. Send data to Python Backend
        try {
          // Notify user process started
          // alertUser(tab.id, "Processing..."); 

          const res = await fetch("http://localhost:8000/process", {
            method: "POST",
            headers: {
              "Content-Type": "application/json"
            },
            body: JSON.stringify(response.data)
          });

          if (res.ok) {
            const result = await res.json();
            alertUser(tab.id, `Success! Saved to tab: ${result.tab}\nCategory: ${result.category}`);
          } else {
            const errText = await res.text();
            console.error("Backend failed:", errText);
            alertUser(tab.id, "Error: Backend processing failed.");
          }
        } catch (error) {
          console.error("Network error:", error);
          alertUser(tab.id, "Error: Cannot connect to localhost:8000.");
        }
      } else {
        alertUser(tab.id, "Error: Could not find valid post data. Ensure you right-clicked on a post.");
      }
    });
  }
});

function alertUser(tabId, message) {
  chrome.scripting.executeScript({
    target: { tabId: tabId },
    func: (msg) => {
      alert(msg);
    },
    args: [message]
  });
}
