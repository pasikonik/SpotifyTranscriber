/**
 * Spotify Transcription Extractor - Main JavaScript
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

/**
 * Copy transcription content to clipboard
 */
function copyTranscription() {
    const transcriptionElem = document.getElementById('transcriptionContent');
    const copyBtn = document.getElementById('copyBtn');
    
    if (!transcriptionElem) return;
    
    // Get the text content
    const text = transcriptionElem.innerText;
    
    // Create a temporary textarea element to copy from
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'absolute';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    
    // Select and copy the text
    textarea.select();
    document.execCommand('copy');
    
    // Remove the temporary element
    document.body.removeChild(textarea);
    
    // Update button text temporarily
    const originalHtml = copyBtn.innerHTML;
    copyBtn.innerHTML = '<i class="fas fa-check me-1"></i> Copied!';
    copyBtn.classList.remove('btn-outline-light');
    copyBtn.classList.add('btn-success');
    
    // Show notification
    showCopyNotification();
    
    // Reset button after 2 seconds
    setTimeout(() => {
        copyBtn.innerHTML = originalHtml;
        copyBtn.classList.remove('btn-success');
        copyBtn.classList.add('btn-outline-light');
    }, 2000);
}

/**
 * Show a copy notification
 */
function showCopyNotification() {
    // Look for existing notification
    let notification = document.querySelector('.copy-notification');
    
    // Create if it doesn't exist
    if (!notification) {
        notification = document.createElement('div');
        notification.className = 'copy-notification';
        notification.innerHTML = '<i class="fas fa-check-circle me-2"></i> Transcription copied to clipboard!';
        document.body.appendChild(notification);
    }
    
    // Show the notification
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Hide after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

/**
 * Handle form validation
 */
document.addEventListener('DOMContentLoaded', function() {
    const episodeUrlField = document.getElementById('episode_url');
    
    if (episodeUrlField) {
        episodeUrlField.addEventListener('input', function() {
            validateSpotifyUrl(this);
        });
    }
});

/**
 * Validate Spotify episode URL
 */
function validateSpotifyUrl(input) {
    const url = input.value.trim();
    const isValid = url.startsWith('https://open.spotify.com/episode/');
    
    if (url && !isValid) {
        input.classList.add('is-invalid');
        
        // Create or update feedback message
        let feedback = input.nextElementSibling;
        if (!feedback || !feedback.classList.contains('invalid-feedback')) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            input.parentNode.insertBefore(feedback, input.nextSibling);
        }
        feedback.textContent = 'Please enter a valid Spotify episode URL (should start with https://open.spotify.com/episode/)';
    } else {
        input.classList.remove('is-invalid');
        
        // Remove any existing feedback
        const feedback = input.nextElementSibling;
        if (feedback && feedback.classList.contains('invalid-feedback')) {
            feedback.remove();
        }
    }
}
