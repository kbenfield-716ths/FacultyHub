# backend/notion_integration.py
"""
Notion API integration for Faculty Knowledge Base
Requires: pip install notion-client
"""

from typing import List, Dict, Optional
import os
from datetime import datetime

try:
    from notion_client import Client
    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False
    print("Warning: notion-client not installed. Run: pip install notion-client")


class NotionKnowledgeBase:
    def __init__(self, notion_token: Optional[str] = None, database_id: Optional[str] = None):
        """
        Initialize Notion API client
        
        Args:
            notion_token: Notion integration token (or set NOTION_TOKEN env var)
            database_id: Notion database ID (or set NOTION_DATABASE_ID env var)
        """
        self.token = notion_token or os.getenv('NOTION_TOKEN')
        self.database_id = database_id or os.getenv('NOTION_DATABASE_ID')
        
        if not NOTION_AVAILABLE:
            self.client = None
            return
            
        if self.token:
            self.client = Client(auth=self.token)
        else:
            self.client = None
            print("Warning: NOTION_TOKEN not set. Notion integration disabled.")

    def get_all_articles(self) -> Dict:
        """
        Fetch all articles from Notion database
        
        Returns:
            Dict with articles and categories
        """
        if not self.client or not self.database_id:
            return self._get_fallback_data()

        try:
            # Query the Notion database
            response = self.client.databases.query(
                database_id=self.database_id,
                sorts=[
                    {
                        "property": "Title",
                        "direction": "ascending"
                    }
                ]
            )

            articles = []
            categories = set()

            for page in response.get('results', []):
                article = self._parse_notion_page(page)
                if article:
                    articles.append(article)
                    categories.add(article['category'])

            return {
                'articles': articles,
                'categories': sorted(list(categories))
            }

        except Exception as e:
            print(f"Error fetching from Notion: {e}")
            return self._get_fallback_data()

    def get_article_by_id(self, article_id: str) -> Optional[Dict]:
        """Get a single article with full content"""
        if not self.client:
            return None

        try:
            page = self.client.pages.retrieve(page_id=article_id)
            return self._parse_notion_page(page, include_content=True)
        except Exception as e:
            print(f"Error fetching article {article_id}: {e}")
            return None

    def search_articles(self, query: str) -> List[Dict]:
        """Search articles by query"""
        if not self.client or not self.database_id:
            return []

        try:
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "or": [
                        {
                            "property": "Title",
                            "title": {
                                "contains": query
                            }
                        },
                        {
                            "property": "Summary",
                            "rich_text": {
                                "contains": query
                            }
                        }
                    ]
                }
            )

            articles = []
            for page in response.get('results', []):
                article = self._parse_notion_page(page)
                if article:
                    articles.append(article)

            return articles

        except Exception as e:
            print(f"Error searching articles: {e}")
            return []

    def _parse_notion_page(self, page: Dict, include_content: bool = False) -> Optional[Dict]:
        """Parse a Notion page into our article format"""
        try:
            properties = page.get('properties', {})
            
            # Extract title
            title_prop = properties.get('Title', {}) or properties.get('Name', {})
            title = self._extract_text(title_prop)
            
            # Extract category
            category_prop = properties.get('Category', {})
            category = self._extract_select(category_prop) or 'General'
            
            # Extract summary
            summary_prop = properties.get('Summary', {})
            summary = self._extract_text(summary_prop) or 'No summary available'
            
            article = {
                'id': page['id'],
                'title': title,
                'category': category,
                'summary': summary,
                'last_edited': page.get('last_edited_time', '')
            }

            # Optionally fetch full content
            if include_content:
                content = self._get_page_content(page['id'])
                article['content'] = content

            return article

        except Exception as e:
            print(f"Error parsing page: {e}")
            return None

    def _get_page_content(self, page_id: str) -> str:
        """Fetch and convert page content to HTML"""
        if not self.client:
            return ""

        try:
            blocks = self.client.blocks.children.list(block_id=page_id)
            html = self._blocks_to_html(blocks.get('results', []))
            return html
        except Exception as e:
            print(f"Error fetching page content: {e}")
            return ""

    def _blocks_to_html(self, blocks: List[Dict]) -> str:
        """Convert Notion blocks to HTML"""
        html = []
        
        for block in blocks:
            block_type = block.get('type')
            
            if block_type == 'paragraph':
                text = self._extract_rich_text(block['paragraph']['rich_text'])
                html.append(f'<p>{text}</p>')
            
            elif block_type == 'heading_1':
                text = self._extract_rich_text(block['heading_1']['rich_text'])
                html.append(f'<h3>{text}</h3>')
            
            elif block_type == 'heading_2':
                text = self._extract_rich_text(block['heading_2']['rich_text'])
                html.append(f'<h4>{text}</h4>')
            
            elif block_type == 'heading_3':
                text = self._extract_rich_text(block['heading_3']['rich_text'])
                html.append(f'<h5>{text}</h5>')
            
            elif block_type == 'bulleted_list_item':
                text = self._extract_rich_text(block['bulleted_list_item']['rich_text'])
                html.append(f'<ul><li>{text}</li></ul>')
            
            elif block_type == 'numbered_list_item':
                text = self._extract_rich_text(block['numbered_list_item']['rich_text'])
                html.append(f'<ol><li>{text}</li></ol>')
            
            elif block_type == 'code':
                text = self._extract_rich_text(block['code']['rich_text'])
                html.append(f'<pre><code>{text}</code></pre>')
            
            elif block_type == 'quote':
                text = self._extract_rich_text(block['quote']['rich_text'])
                html.append(f'<blockquote>{text}</blockquote>')

        return '\n'.join(html)

    def _extract_text(self, prop: Dict) -> str:
        """Extract plain text from a Notion property"""
        if not prop:
            return ""
        
        prop_type = prop.get('type')
        
        if prop_type == 'title':
            return ''.join([t.get('plain_text', '') for t in prop.get('title', [])])
        elif prop_type == 'rich_text':
            return ''.join([t.get('plain_text', '') for t in prop.get('rich_text', [])])
        
        return ""

    def _extract_rich_text(self, rich_text: List[Dict]) -> str:
        """Extract and format rich text with HTML"""
        html = []
        for text in rich_text:
            content = text.get('plain_text', '')
            annotations = text.get('annotations', {})
            
            if annotations.get('bold'):
                content = f'<strong>{content}</strong>'
            if annotations.get('italic'):
                content = f'<em>{content}</em>'
            if annotations.get('code'):
                content = f'<code>{content}</code>'
            
            if text.get('href'):
                content = f'<a href="{text["href"]}">{content}</a>'
            
            html.append(content)
        
        return ''.join(html)

    def _extract_select(self, prop: Dict) -> Optional[str]:
        """Extract select/dropdown value"""
        if prop.get('type') == 'select' and prop.get('select'):
            return prop['select'].get('name')
        return None

    def _get_fallback_data(self) -> Dict:
        """Return fallback data when Notion is not available"""
        return {
            'articles': [],
            'categories': []
        }


# Singleton instance
_notion_kb = None

def get_notion_kb() -> NotionKnowledgeBase:
    """Get or create NotionKnowledgeBase instance"""
    global _notion_kb
    if _notion_kb is None:
        _notion_kb = NotionKnowledgeBase()
    return _notion_kb
