document.addEventListener('DOMContentLoaded', function() {
    const checkButton = document.getElementById('checkCurrentPage');
    const loadingDiv = document.getElementById('loading');
    const resultDiv = document.getElementById('result');
    const errorDiv = document.getElementById('error');
    
    checkButton.addEventListener('click', async function() {
      // Show loading, hide other elements
      loadingDiv.classList.remove('hidden');
      resultDiv.classList.add('hidden');
      errorDiv.classList.add('hidden');
      
      try {
        // Get the current active tab
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        // Send message to background script to analyze the page
        const response = await chrome.runtime.sendMessage({
          action: "analyzePage",
          url: tab.url
        });
        
        if (response.error) {
          throw new Error(response.error);
        }
        
        // Display results
        document.getElementById('score').textContent = response.score;
        document.getElementById('reason').textContent = response.reason;
        resultDiv.classList.remove('hidden');
      } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
      } finally {
        loadingDiv.classList.add('hidden');
      }
    });
  });

  