#!/usr/bin/env python3
"""
Capture and save webhook data for debugging
This creates a temporary endpoint to capture raw webhook payloads
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
from datetime import datetime

class WebhookCaptureHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            webhook_data = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            webhook_data = {"raw_data": post_data.decode('utf-8')}
        
        timestamp = datetime.now().isoformat()
        
        print(f"\n🔍 WEBHOOK CAPTURED at {timestamp}")
        print("=" * 60)
        print(f"Headers: {dict(self.headers)}")
        print(f"Data Type: {type(webhook_data)}")
        print(f"Data: {json.dumps(webhook_data, indent=2)}")
        print("=" * 60)
        
        # Save to file
        filename = f"webhook_capture_{int(time.time())}.json"
        with open(filename, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'headers': dict(self.headers),
                'data': webhook_data
            }, f, indent=2)
        
        print(f"💾 Saved to {filename}")
        
        # Send success response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "captured"}')

if __name__ == "__main__":
    print("🎯 WEBHOOK DATA CAPTURE SERVER")
    print("Starting server on port 9000...")
    print("Configure UniPile webhook URL to: https://webhooks.oneocrm.com:9000/capture")
    print("Press Ctrl+C to stop")
    
    server = HTTPServer(('localhost', 9000), WebhookCaptureHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n📄 Capture server stopped")
        server.shutdown()