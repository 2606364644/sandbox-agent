"""
Web工具模块
"""
import requests
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from src.tools.base_tools import BaseCustomTool, register_tool
from urllib.parse import urlparse, urljoin
import logging

logger = logging.getLogger(__name__)


class WebSearchInput(BaseModel):
    """Web搜索输入模型"""
    query: str = Field(description="搜索查询关键词")
    max_results: int = Field(default=5, description="最大结果数量")
    engine: str = Field(default="duckduckgo", description="搜索引擎")


class HttpRequestInput(BaseModel):
    """HTTP请求输入模型"""
    url: str = Field(description="请求的URL")
    method: str = Field(default="GET", description="HTTP方法")
    headers: Optional[Dict[str, str]] = Field(default=None, description="请求头")
    params: Optional[Dict[str, str]] = Field(default=None, description="查询参数")
    data: Optional[str] = Field(default=None, description="请求体数据")
    timeout: int = Field(default=10, description="请求超时时间（秒）")


class WikipediaSearchInput(BaseModel):
    """维基百科搜索输入模型"""
    query: str = Field(description="搜索关键词")
    lang: str = Field(default="zh", description="语言代码")
    max_results: int = Field(default=3, description="最大结果数量")


class WebSearchTool(BaseCustomTool):
    """Web搜索工具"""

    name: str = "web_search"
    description: str = "在互联网上搜索信息"
    args_schema = WebSearchInput

    def _setup(self):
        """工具初始化设置"""
        pass

    def _execute(self, query: str, max_results: int = 5, engine: str = "duckduckgo") -> str:
        """执行Web搜索"""
        try:
            if engine.lower() == "duckduckgo":
                return self._duckduckgo_search(query, max_results)
            else:
                return f"不支持的搜索引擎：{engine}"

        except Exception as e:
            return f"Web搜索时发生错误：{str(e)}"

    def _duckduckgo_search(self, query: str, max_results: int) -> str:
        """使用DuckDuckGo进行搜索"""
        try:
            # 使用DuckDuckGo的HTML版本
            url = "https://duckduckgo.com/html/"
            params = {
                'q': query,
                'kl': 'cn-zh'
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            results = []
            result_divs = soup.find_all('div', class_='result')[:max_results]

            for result_div in result_divs:
                title_tag = result_div.find('a', class_='result__a')
                snippet_tag = result_div.find('a', class_='result__snippet')

                if title_tag:
                    title = title_tag.get_text().strip()
                    url = title_tag.get('href', '')
                    snippet = snippet_tag.get_text().strip() if snippet_tag else ""

                    if url and title:
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet
                        })

            if not results:
                return f"未找到关于 '{query}' 的搜索结果"

            result_text = f"关于 '{query}' 的搜索结果（前{len(results)}条）：\n\n"
            for i, result in enumerate(results, 1):
                result_text += f"{i}. {result['title']}\n"
                result_text += f"   链接: {result['url']}\n"
                if result['snippet']:
                    result_text += f"   摘要: {result['snippet']}\n"
                result_text += "\n"

            return result_text

        except Exception as e:
            return f"搜索时发生错误：{str(e)}"


class HttpRequestTool(BaseCustomTool):
    """HTTP请求工具"""

    name: str = "http_request"
    description: str = "发送HTTP请求获取网页内容或API数据"
    args_schema = HttpRequestInput

    def _setup(self):
        """工具初始化设置"""
        pass

    def _execute(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        timeout: int = 10
    ) -> str:
        """执行HTTP请求"""
        try:
            # 验证URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return f"错误：无效的URL格式 - {url}"

            # 设置默认请求头
            default_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            if headers:
                default_headers.update(headers)

            # 准备请求参数
            request_kwargs = {
                'url': url,
                'method': method.upper(),
                'headers': default_headers,
                'timeout': timeout
            }

            if params:
                request_kwargs['params'] = params

            if data:
                request_kwargs['data'] = data

            # 发送请求
            response = requests.request(**request_kwargs)

            result = f"HTTP请求结果：\n"
            result += f"URL: {url}\n"
            result += f"方法: {method.upper()}\n"
            result += f"状态码: {response.status_code}\n"

            # 添加响应头信息
            result += f"响应大小: {len(response.content)} bytes\n"
            content_type = response.headers.get('Content-Type', 'unknown')
            result += f"内容类型: {content_type}\n\n"

            # 处理响应内容
            if response.status_code == 200:
                content_type = content_type.lower()

                if 'text' in content_type or 'json' in content_type:
                    # 文本内容，限制长度
                    content = response.text
                    if len(content) > 5000:
                        content = content[:5000] + "\n...（内容已截断）"
                    result += f"响应内容：\n{content}"
                else:
                    result += f"二进制内容（大小: {len(response.content)} bytes）"
            else:
                result += f"响应内容：{response.text}"

            return result

        except requests.exceptions.Timeout:
            return f"错误：请求超时（{timeout}秒）"
        except requests.exceptions.ConnectionError:
            return f"错误：无法连接到 {url}"
        except requests.exceptions.RequestException as e:
            return f"HTTP请求错误：{str(e)}"
        except Exception as e:
            return f"请求时发生未知错误：{str(e)}"


class WikipediaSearchTool(BaseCustomTool):
    """维基百科搜索工具"""

    name: str = "wikipedia_search"
    description: str = "在维基百科中搜索信息"
    args_schema = WikipediaSearchInput

    def _setup(self):
        """工具初始化设置"""
        try:
            import wikipedia
            self.wikipedia = wikipedia
            # 设置语言
            self.wikipedia.set_lang("zh")
        except ImportError:
            logger.warning("wikipedia库未安装，维基百科搜索功能不可用")
            self.wikipedia = None

    def _execute(self, query: str, lang: str = "zh", max_results: int = 3) -> str:
        """执行维基百科搜索"""
        if not self.wikipedia:
            return "错误：wikipedia库未安装，无法使用维基百科搜索功能"

        try:
            # 设置语言
            self.wikipedia.set_lang(lang)

            # 搜索页面
            search_results = self.wikipedia.search(query, results=max_results)

            if not search_results:
                return f"在维基百科中未找到关于 '{query}' 的相关页面"

            result_text = f"维基百科搜索结果（关键词：{query}）：\n\n"

            for i, page_title in enumerate(search_results, 1):
                try:
                    # 获取页面摘要
                    summary = self.wikipedia.summary(page_title, sentences=3)
                    page_url = self.wikipedia.page(page_title).url

                    result_text += f"{i}. {page_title}\n"
                    result_text += f"   摘要: {summary}\n"
                    result_text += f"   链接: {page_url}\n\n"

                except Exception as e:
                    result_text += f"{i}. {page_title}\n"
                    result_text += f"   无法获取页面详情: {str(e)}\n\n"

            return result_text

        except Exception as e:
            return f"维基百科搜索时发生错误：{str(e)}"


class UrlExtractorTool(BaseCustomTool):
    """URL提取工具"""

    name: str = "extract_urls"
    description: str = "从文本中提取URL链接"

    class UrlExtractorInput(BaseModel):
        text: str = Field(description="要提取URL的文本")

    args_schema = UrlExtractorInput

    def _setup(self):
        """工具初始化设置"""
        pass

    def _execute(self, text: str) -> str:
        """执行URL提取"""
        try:
            import re

            # URL正则表达式
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'

            urls = re.findall(url_pattern, text)

            if not urls:
                return "文本中未找到URL链接"

            # 去重
            unique_urls = list(set(urls))

            result = f"从文本中提取到 {len(unique_urls)} 个URL：\n\n"
            for i, url in enumerate(unique_urls, 1):
                result += f"{i}. {url}\n"

            return result

        except Exception as e:
            return f"URL提取时发生错误：{str(e)}"


# 注册所有Web工具
register_tool(WebSearchTool(), category="web")
register_tool(HttpRequestTool(), category="web")
register_tool(WikipediaSearchTool(), category="web")
register_tool(UrlExtractorTool(), category="web")