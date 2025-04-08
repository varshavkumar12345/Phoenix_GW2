const API_BASE_URL = "https://phoenix-gw2.onrender.com"; // Your Render service URL

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "analyzePage") {
    analyzePage(request.url)
      .then(result => sendResponse(result))
      .catch(error => sendResponse({ error: error.message }));
    
    // Return true to indicate we want to send a response asynchronously
    return true;
  }
});

async function analyzePage(url) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/check`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ url })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.message || "Failed to analyze page");
    }
    
    return {
      score: data.score,
      reason: data.reason
    };
  } catch (error) {
    throw new Error(`Analysis failed: ${error.message}`);
  }
}