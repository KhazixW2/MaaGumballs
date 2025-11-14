from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.error import HTTPError, URLError
import json


def get_request(url, params=None, headers=None, timeout=10):
    """
    封装 GET 请求，类似 requests.get()
    参数：
        url: 请求地址
        params: 字典类型，URL 查询参数
        headers: 字典类型，请求头
        timeout: 超时时间（秒）
    返回：
        字典包含 {status, url, content, text, json, headers, error}
    """
    # 构建完整 URL（含查询参数）
    if params:
        scheme, netloc, path, query, fragment = urlsplit(url)
        query = "&".join(filter(None, [query, urlencode(params)]))
        url = urlunsplit((scheme, netloc, path, query, fragment))

    # 创建请求对象
    req = Request(url, method="GET")
    return _send_request(req, headers, timeout)


def post_request(url, data=None, headers=None, timeout=10):
    """
    封装 POST 请求，类似 requests.post()
    参数：
        url: 请求地址
        data: 字典类型，表单数据（或字节流）
        headers: 字典类型，请求头
        timeout: 超时时间（秒）
    返回：
        字典包含 {status, url, content, text, json, headers, error}
    """
    # 处理请求体数据
    post_data = None
    if data is not None:
        if isinstance(data, dict):
            post_data = urlencode(data).encode("utf-8")
            # 设置默认 Content-Type
            headers = headers or {}
            if "Content-Type" not in headers:
                headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        elif isinstance(data, bytes):
            post_data = data

    # 创建请求对象
    req = Request(url, data=post_data, method="POST")
    return _send_request(req, headers, timeout)


def _send_request(req, headers, timeout):
    """内部请求处理函数"""
    result = {
        "url": req.full_url,
        "status": None,
        "content": None,
        "text": None,
        "json": None,
        "headers": {},
        "error": None,
    }

    # 添加请求头
    if headers:
        for key, value in headers.items():
            req.add_header(key, value)

    try:
        # 发送请求并获取响应
        with urlopen(req, timeout=timeout) as res:
            result["status"] = res.status
            result["content"] = res.read()
            result["headers"] = dict(res.headers.items())

            # 自动解码文本内容
            charset = _detect_charset(res.headers)
            result["text"] = result["content"].decode(charset or "utf-8")

            # 自动解析 JSON
            if "application/json" in res.headers.get("Content-Type", "").lower():
                try:
                    result["json"] = json.loads(result["text"])
                except json.JSONDecodeError:
                    pass
    except HTTPError as e:
        result["status"] = e.code
        result["error"] = f"HTTP Error: {e.code} {e.reason}"
    except URLError as e:
        result["error"] = f"URL Error: {e.reason}"
    except Exception as e:
        result["error"] = f"Request Failed: {str(e)}"

    return result


def _detect_charset(headers):
    """从 Content-Type 头中检测字符集"""
    content_type = headers.get("Content-Type", "").lower()
    if "charset=" in content_type:
        return content_type.split("charset=")[-1].split(";").strip()
    return None
