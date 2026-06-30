import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

DIFY_API_KEY = os.getenv("DIFY_API_KEY")
DIFY_API_URL = os.getenv("DIFY_API_URL")

def call_job_copilot_api(resume_text: str, jd_text: str, red_lines: list = None):
    """
    流式（Streaming）请求网关，保持管道持续活跃，彻底解决网关及操作系统超时断开问题
    """
    if not DIFY_API_KEY or not DIFY_API_URL:
        return {"error_details": "未能在 .env 文件中找到有效的 DIFY_API_KEY 或 DIFY_API_URL"}

    base_url = DIFY_API_URL.strip().rstrip('/')
    url = f"{base_url}/workflows/run"
    
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY.strip()}",
        "Content-Type": "application/json"
    }
    
    data = {
        "inputs": {
            "resume_text": resume_text, 
            "jd_text": jd_text,
            "red_lines": "、".join(red_lines) if red_lines else "无" 
        },
        "response_mode": "streaming",
        "user": "job_copilot_shared_user"
    }
    
    session = requests.Session()
    session.trust_env = False  # 穿透系统一切代理
    
    try:
        # 以 stream=True 方式发起持久化连接
        response = session.post(url, headers=headers, json=data, proxies={"http": None, "https": None}, timeout=600, stream=True)
        response.raise_for_status()
        
        final_outputs = {}
        # 持续捕获流式事件块
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8').strip()
                if line_str.startswith("data:"):
                    try:
                        event_data = json.loads(line_str[5:])
                        event_type = event_data.get("event")
                        
                        # 当工作流正常结束时，抓取最终挂载的 outputs 变量
                        if event_type == "workflow_finished":
                            data_layer = event_data.get("data", {})
                            final_outputs = {
                                "status": data_layer.get("status"),
                                "outputs": data_layer.get("outputs", {}),
                                "error": data_layer.get("error")
                            }
                            return {"data": final_outputs}
                    except Exception:
                        continue
                        
        if final_outputs:
            return {"data": final_outputs}
        return {"error_details": "工作流已执行，但流式传输结束时未能捕获到 workflow_finished 最终输出。"}
        
    except requests.exceptions.RequestException as req_err:
        return {"error_details": f"【物理网络/超时阻断】: {str(req_err)}"}