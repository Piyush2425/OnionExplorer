"""
HTML Exporter Utility
"""
import os
import base64
from datetime import datetime
from typing import List, Dict, Any

def export_to_html(rows: List[Dict[str, Any]], scope_label: str, status_filter: str, source_filter: str) -> str:
    # Compile HTML Rows
    table_rows_html = []
    for r in rows:
        badge_class = "online" if r["status"] == "Online" else "offline"
        
        # Screen capture column cell
        if r["screenshot_b64"]:
            screenshot_cell = f"""
            <div class="thumbnail-container" onclick="openModal('{r['screenshot_b64']}')">
                <img class="thumbnail" src="{r['screenshot_b64']}" alt="Scan Preview">
            </div>
            """
        else:
            screenshot_cell = '<span class="no-preview">No Preview Available</span>'

        table_rows_html.append(f"""
        <tr>
            <td><strong>{r['entity_name']}</strong></td>
            <td>{r['sector']}</td>
            <td><a href="{r['url']}" target="_blank" style="color: #0284c7; text-decoration: none; font-family: monospace;">{r['url']}</a></td>
            <td><span class="status-badge {badge_class}">{r['status']}</span></td>
            <td><span style="background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem;">{r['source']}</span></td>
            <td>{r['last_visit']}</td>
            <td>{screenshot_cell}</td>
        </tr>
        """)

    # Complete HTML report body template
    timestamp_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Calculate stats
    total_entities = len(set(r["entity_name"] for r in rows))
    total_urls = len(rows)
    online_count = sum(1 for r in rows if r["status"] == "Online")
    offline_count = total_urls - online_count

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OnionExplorer CTI Threat Intelligence Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f8fafc;
            color: #0f172a;
            margin: 0;
            padding: 30px 15px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: #ffffff;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.02);
            border: 1px solid #e2e8f0;
        }}
        .header {{
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 20px;
            margin-bottom: 25px;
        }}
        .header h1 {{
            margin: 0 0 5px 0;
            font-size: 1.8rem;
            font-weight: 850;
            color: #0f172a;
        }}
        .header .meta-info {{
            color: #64748b;
            font-size: 0.88rem;
            font-family: monospace;
        }}
        .stats-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 35px;
        }}
        .stat-card {{
            background: #f8fafc;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            box-sizing: border-box;
        }}
        .stat-card h3 {{
            margin: 0;
            font-size: 0.8rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .stat-card p {{
            margin: 10px 0 0 0;
            font-size: 2rem;
            font-weight: 800;
            color: #0f172a;
        }}
        .stat-card.online p {{ color: #10b981; }}
        .stat-card.offline p {{ color: #ef4444; }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 14px 16px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
            font-size: 0.9rem;
        }}
        th {{
            background: #f1f5f9;
            color: #475569;
            font-weight: 750;
        }}
        tr:hover {{ background: #f8fafc; }}
        
        .status-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.76rem;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .status-badge.online {{
            background: rgba(16, 185, 129, 0.1);
            color: #065f46;
        }}
        .status-badge.offline {{
            background: rgba(239, 68, 68, 0.1);
            color: #991b1b;
        }}
        
        .thumbnail-container {{
            position: relative;
            width: 90px;
            height: 55px;
            overflow: hidden;
            border-radius: 6px;
            border: 1px solid #cbd5e1;
            cursor: pointer;
            transition: transform 150ms ease;
        }}
        .thumbnail-container:hover {{
            transform: scale(1.05);
            border-color: #0284c7;
        }}
        .thumbnail {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .no-preview {{
            font-size: 0.78rem;
            color: #94a3b8;
            font-style: italic;
        }}
        
        .modal {{
            display: none;
            position: fixed;
            z-index: 9999;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(15, 23, 42, 0.9);
            align-items: center;
            justify-content: center;
        }}
        .modal-content {{
            max-width: 92%;
            max-height: 92%;
            border-radius: 8px;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
            border: 2px solid rgba(255,255,255,0.1);
        }}
        .close {{
            position: absolute;
            top: 20px;
            right: 35px;
            color: #ffffff;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
        }}
        .close:hover {{
            color: #cbd5e1;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>OnionExplorer CTI Threat Intelligence Report</h1>
            <div class="meta-info">
                Generated: {timestamp_str} | Scope: {scope_label} | Status Filter: {status_filter.upper()} | Source Filter: {source_filter.upper()}
            </div>
        </div>
        
        <div class="stats-row">
            <div class="stat-card">
                <h3>Total Entities</h3>
                <p>{total_entities}</p>
            </div>
            <div class="stat-card">
                <h3>Total Link Locations</h3>
                <p>{total_urls}</p>
            </div>
            <div class="stat-card online">
                <h3>Active (Online)</h3>
                <p>{online_count}</p>
            </div>
            <div class="stat-card offline">
                <h3>Inactive (Offline)</h3>
                <p>{offline_count}</p>
            </div>
        </div>
        
        <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Threat Actor / Entity</th>
                        <th>Sector</th>
                        <th>Onion URL / Link</th>
                        <th>Status</th>
                        <th>Source Feed</th>
                        <th>Last Checked</th>
                        <th>Screenshot Capture</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(table_rows_html)}
                </tbody>
            </table>
        </div>
    </div>
    
    <div id="imageModal" class="modal" onclick="closeModal()">
        <span class="close" onclick="closeModal()">&times;</span>
        <img class="modal-content" id="modalImg" alt="Enlarged Preview">
    </div>
    
    <script>
        function openModal(imgSrc) {{
            document.getElementById('modalImg').src = imgSrc;
            document.getElementById('imageModal').style.display = 'flex';
        }}
        function closeModal() {{
            document.getElementById('imageModal').style.display = 'none';
        }}
    </script>
</body>
</html>
"""
    return html_content
