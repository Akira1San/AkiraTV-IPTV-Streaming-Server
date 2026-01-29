# LIFECYCLE ENDPOINTS (Windows encoding workaround)
import os

# Force UTF-8 encoding for all file operations
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Save original codec functions
original_codecs = {
    'cp1252': codecs.lookup,
    'utf-8': codecs.lookup
}

# Simple cleanup function
def cleanup_unicode(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Simple character replacement - just clean up obvious ones
            content = content.replace('ðŸ\"º Channels', 'AkiraTV Channels')
            content = content.replace('âž• Add Channel', 'Add Channel')
            content = content.replace('âœ… Enable All', 'Enable All')
            content = content.replace('âŒ Disable All', 'Disable All')
            content = content.replace('â€“¶ï¸', 'Start Streaming')
            content = content.replace('â¹ï¸', 'Stop Streaming')
            content = content.replace('âœ"': 'OK')
            content = content.replace('ðŸ"': 'Reload')
            content = content.replace('â€“¶ï¸': 'Restart')
            content = content.replace('â€":'Start Streaming')
            content = content.replace('â–¶ï¸': 'Stop Streaming')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            print(f'✅ Unicode cleanup completed for {file_path}')
        return True
    except Exception as e:
        print(f'❌ Error during cleanup: {e}')
        return False

# Apply the cleanup
if cleanup_unicode('akiratv/api_server.py'):
    print('✅ Applied Unicode cleanup to api_server.py')

if cleanup_unicode('akiratv/web_ui.html'):
    print('✅ Applied Unicode cleanup to web_ui.html')