/**
 * HTML Pages for Defense Responses
 * ⛨ Challenge and block pages with Spatium branding
 */

/**
 * Generate a challenge page for suspicious visitors
 */
export function generateChallengePage(rayId: string): Response {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Verification - Spatium Computationis</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #e8e8e8;
        }
        .container {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 48px;
            text-align: center;
            max-width: 420px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        .glyph {
            font-size: 72px;
            margin-bottom: 24px;
            animation: pulse 2s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(1.05); }
        }
        h1 {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 12px;
        }
        .subtitle {
            color: #a0a0a0;
            margin-bottom: 32px;
            font-size: 14px;
        }
        .spinner-container {
            margin: 24px 0;
        }
        .spinner {
            width: 48px;
            height: 48px;
            border: 3px solid rgba(255, 255, 255, 0.1);
            border-top: 3px solid #4a9eff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .status {
            font-size: 14px;
            color: #888;
            margin-top: 16px;
        }
        .progress-bar {
            width: 100%;
            height: 4px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 2px;
            margin-top: 24px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4a9eff, #00d4aa);
            width: 0%;
            animation: progress 3s ease-out forwards;
        }
        @keyframes progress {
            0% { width: 0%; }
            100% { width: 100%; }
        }
        .ray-id {
            font-size: 11px;
            color: #555;
            margin-top: 24px;
            font-family: 'Monaco', 'Menlo', monospace;
        }
        .brand {
            margin-top: 32px;
            font-size: 12px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="glyph">⛨</div>
        <h1>Security Verification</h1>
        <p class="subtitle">Checking your browser before accessing the site</p>
        
        <div class="spinner-container">
            <div class="spinner"></div>
        </div>
        
        <p class="status">Verifying you're not a bot...</p>
        
        <div class="progress-bar">
            <div class="progress-fill"></div>
        </div>
        
        <p class="ray-id">Ray ID: ${rayId}</p>
        
        <p class="brand">Protected by Spatium Computationis ⌬</p>
    </div>
    
    <script>
        // Simulate challenge completion
        setTimeout(() => {
            document.querySelector('.status').textContent = 'Verification complete!';
            setTimeout(() => {
                window.location.reload();
            }, 500);
        }, 3000);
    </script>
</body>
</html>`;

  return new Response(html, {
    status: 403,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store',
      'X-Robots-Tag': 'noindex',
    },
  });
}

/**
 * Generate a block page for threats
 */
export function generateBlockPage(rayId: string, reason: string): Response {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Access Denied - Spatium Computationis</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #2d132c 50%, #4a0e0e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #e8e8e8;
        }
        .container {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 100, 100, 0.2);
            border-radius: 16px;
            padding: 48px;
            text-align: center;
            max-width: 420px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }
        .glyph {
            font-size: 72px;
            margin-bottom: 24px;
        }
        h1 {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 12px;
            color: #ff6b6b;
        }
        .message {
            color: #a0a0a0;
            margin-bottom: 24px;
            font-size: 14px;
            line-height: 1.6;
        }
        .reason {
            background: rgba(255, 100, 100, 0.1);
            border: 1px solid rgba(255, 100, 100, 0.2);
            border-radius: 8px;
            padding: 12px 16px;
            font-size: 12px;
            color: #ff9999;
            margin-bottom: 24px;
        }
        .ray-id {
            font-size: 11px;
            color: #555;
            font-family: 'Monaco', 'Menlo', monospace;
        }
        .brand {
            margin-top: 32px;
            font-size: 12px;
            color: #666;
        }
        .contact {
            margin-top: 16px;
            font-size: 12px;
            color: #888;
        }
        .contact a {
            color: #4a9eff;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="glyph">⚠</div>
        <h1>Access Denied</h1>
        <p class="message">
            Your request has been blocked due to suspicious activity.
            If you believe this is an error, please contact the site administrator.
        </p>
        
        <div class="reason">
            Reason: ${reason.replace(/_/g, ' ')}
        </div>
        
        <p class="ray-id">Ray ID: ${rayId}</p>
        
        <p class="contact">
            Need help? Contact <a href="mailto:support@example.com">support</a>
        </p>
        
        <p class="brand">Protected by Spatium Computationis ⌬</p>
    </div>
</body>
</html>`;

  return new Response(html, {
    status: 403,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store',
      'X-Robots-Tag': 'noindex',
    },
  });
}

/**
 * Generate an error page
 */
export function generateErrorPage(rayId: string, message: string): Response {
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error - Spatium Computationis</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1a1a2e;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #e8e8e8;
        }
        .container {
            text-align: center;
            padding: 40px;
        }
        .glyph { font-size: 48px; margin-bottom: 16px; }
        h1 { margin-bottom: 8px; }
        p { color: #888; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="glyph">⌬</div>
        <h1>Something went wrong</h1>
        <p>${message}</p>
        <p style="margin-top: 16px; font-size: 11px; color: #555;">Ray ID: ${rayId}</p>
    </div>
</body>
</html>`;

  return new Response(html, {
    status: 500,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
    },
  });
}
