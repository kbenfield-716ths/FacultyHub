// Feedback Button - Inject feedback UI into any page
(function() {
  'use strict';

  // Check if already loaded
  if (window.feedbackButtonLoaded) return;
  window.feedbackButtonLoaded = true;

  // Inject CSS
  const style = document.createElement('style');
  style.textContent = `
    #feedback-btn {
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: #E57200;
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 25px;
      cursor: pointer;
      font-size: 14px;
      font-weight: bold;
      box-shadow: 0 4px 6px rgba(0,0,0,0.2);
      z-index: 1000;
      transition: all 0.2s;
    }
    #feedback-btn:hover {
      background: #C66100;
      transform: scale(1.05);
    }
    #feedback-modal {
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.5);
      z-index: 1001;
      animation: fadeIn 0.2s;
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    #feedback-content {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: white;
      padding: 30px;
      border-radius: 10px;
      width: 90%;
      max-width: 500px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    }
    .feedback-field { 
      margin: 15px 0; 
    }
    .feedback-field label { 
      display: block; 
      margin-bottom: 5px; 
      font-weight: bold;
      color: #333;
    }
    .feedback-field select, 
    .feedback-field textarea { 
      width: 100%; 
      padding: 10px; 
      border: 2px solid #ddd; 
      border-radius: 5px;
      font-family: inherit;
      font-size: 14px;
    }
    .feedback-field select:focus,
    .feedback-field textarea:focus {
      outline: none;
      border-color: #E57200;
    }
    .feedback-field textarea { 
      min-height: 120px; 
      resize: vertical; 
    }
    .feedback-buttons { 
      display: flex; 
      gap: 10px; 
      margin-top: 20px; 
    }
    .feedback-buttons button {
      flex: 1; 
      padding: 12px; 
      border: none; 
      border-radius: 5px; 
      cursor: pointer; 
      font-weight: bold;
      font-size: 14px;
      transition: all 0.2s;
    }
    .btn-submit { 
      background: #E57200; 
      color: white; 
    }
    .btn-submit:hover {
      background: #C66100;
    }
    .btn-cancel { 
      background: #ddd; 
    }
    .btn-cancel:hover {
      background: #ccc;
    }
    #feedback-status {
      padding: 10px;
      border-radius: 5px;
      margin-top: 10px;
      text-align: center;
      font-weight: 500;
    }
    #feedback-status.success {
      background: #e8f5e9;
      color: #2e7d32;
    }
    #feedback-status.error {
      background: #ffebee;
      color: #c62828;
    }
  `;
  document.head.appendChild(style);

  // Inject HTML
  const html = `
    <button id="feedback-btn">📝 Feedback</button>
    
    <div id="feedback-modal">
      <div id="feedback-content">
        <h2 style="margin-top: 0; color: #232D4B;">Send Feedback</h2>
        <p style="color: #666; font-size: 14px; margin-bottom: 20px;">
          Help us improve the Faculty Hub! Your feedback goes directly to the development team.
        </p>
        
        <div class="feedback-field">
          <label for="feedback-type">Type:</label>
          <select id="feedback-type">
            <option value="bug">🐛 Bug Report</option>
            <option value="feature">💡 Feature Request</option>
            <option value="general">💬 General Feedback</option>
          </select>
        </div>
        
        <div class="feedback-field">
          <label for="feedback-message">Message:</label>
          <textarea 
            id="feedback-message" 
            placeholder="Describe your feedback in detail..."
          ></textarea>
        </div>
        
        <div id="feedback-status" style="display: none;"></div>
        
        <div class="feedback-buttons">
          <button class="btn-cancel" id="feedback-cancel">Cancel</button>
          <button class="btn-submit" id="feedback-submit">Send Feedback</button>
        </div>
      </div>
    </div>
  `;
  
  // Wait for DOM to be ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  function init() {
    // Insert HTML at end of body
    const container = document.createElement('div');
    container.innerHTML = html;
    document.body.appendChild(container);

    // Get elements
    const btn = document.getElementById('feedback-btn');
    const modal = document.getElementById('feedback-modal');
    const content = document.getElementById('feedback-content');
    const cancelBtn = document.getElementById('feedback-cancel');
    const submitBtn = document.getElementById('feedback-submit');
    const messageInput = document.getElementById('feedback-message');
    const typeSelect = document.getElementById('feedback-type');
    const status = document.getElementById('feedback-status');

    // Open modal
    btn.addEventListener('click', () => {
      modal.style.display = 'block';
      messageInput.value = '';
      status.style.display = 'none';
      messageInput.focus();
    });

    // Close modal
    function closeModal() {
      modal.style.display = 'none';
    }

    cancelBtn.addEventListener('click', closeModal);
    
    // Close on backdrop click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeModal();
      }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal.style.display === 'block') {
        closeModal();
      }
    });

    // Submit feedback
    submitBtn.addEventListener('click', async () => {
      const type = typeSelect.value;
      const message = messageInput.value.trim();
      
      if (!message) {
        showStatus('Please enter a message', 'error');
        return;
      }

      // Disable submit button
      submitBtn.disabled = true;
      submitBtn.textContent = 'Sending...';

      try {
        const response = await fetch('/api/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({
            feedback_type: type,
            message: message,
            page_url: window.location.href
          })
        });

        if (response.ok) {
          showStatus('✓ Feedback sent! Thank you!', 'success');
          messageInput.value = '';
          setTimeout(() => {
            closeModal();
          }, 2000);
        } else {
          const error = await response.json().catch(() => ({}));
          throw new Error(error.detail || 'Failed to send feedback');
        }
      } catch (error) {
        console.error('Feedback error:', error);
        showStatus('Error sending feedback. Please try again.', 'error');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Send Feedback';
      }
    });

    function showStatus(message, type) {
      status.textContent = message;
      status.className = type;
      status.style.display = 'block';
    }
  }
})();
