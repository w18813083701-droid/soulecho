import random
import os
import time
import threading
import hashlib
import json
import re
from supabase import create_client, Client
from datetime import date, datetime, timedelta
from openai import OpenAI
import streamlit as st

os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

st.set_page_config(
    page_title="Soul Echo",
    page_icon="🪨",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items=None  # 隐藏菜单
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    header {visibility: hidden;} 

    .stApp { 
        background-color: #F4F4F4; 
        background-image: radial-gradient(circle at 50% 0%, #FFFFFF 0%, #EAEAEA 100%); 
        font-family: "Noto Serif SC", "Songti SC", serif; 
    } 

    .block-container { 
        max-width: 600px !important; 
        padding-top: 2rem !important; 
        padding-bottom: 4rem !important; 
    } 

    h1 { 
        font-family: "Noto Serif SC", "Songti SC", serif !important; 
        font-weight: 600 !important; 
        letter-spacing: 0.3em !important; 
        color: #111111 !important; 
    } 

    .stButton > button { 
        font-family: "Noto Serif SC", "Songti SC", serif !important; 
        background: transparent; 
        border: 1px solid rgba(0,0,0,0.1); 
        color: #2D2D2D; 
        border-radius: 4px; 
        font-size: 13px; 
        letter-spacing: 0.1em; 
        padding: 8px 16px; 
        transition: all 0.3s ease; 
    } 
    .stButton > button:hover { 
        background: #7A1F1F; 
        color: #FFFFFF !important; 
        border-color: #7A1F1F; 
        box-shadow: 0 4px 12px rgba(122,31,31,0.2); 
    } 

    [data-testid="stButton"] button[kind="secondary"].amber-card-btn { 
        width: 100%; 
        text-align: left; 
        white-space: normal; 
        height: auto; 
        padding: 24px 22px; 
        border-radius: 6px; 
        background: #101215; 
        border: 1px solid #222; 
        box-shadow: 0 16px 32px rgba(0,0,0,0.15); 
        font-size: 14px; 
        line-height: 1.9; 
        color: #E8E8E8; 
        cursor: pointer; 
        font-family: "Noto Serif SC", "Songti SC", serif !important; 
        transition: transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1); 
    } 
    [data-testid="stButton"] button[kind="secondary"].amber-card-btn:hover { 
        transform: translateY(-2px); 
        border-color: #333; 
        background: #16181C; 
    } 

    /* 输入框极简处理：限制最大宽度防止撑满屏幕 */ 
    .stTextArea textarea, .stTextInput input { 
        font-family: "Noto Serif SC", "Songti SC", serif !important; 
        background: rgba(255,255,255,0.8) !important; 
        border: 1px solid rgba(0,0,0,0.08) !important; 
        border-radius: 4px !important; 
        font-size: 14px; 
        color: #1a1a1a; 
        max-width: 100% !important; 
        box-sizing: border-box !important; 
    } 
    .stTextInput > div { 
        max-width: 480px !important; 
    } 
    .stTextArea textarea:focus, .stTextInput input:focus { 
        border-color: #7A1F1F !important; 
        box-shadow: 0 0 0 1px rgba(122,31,31,0.2) !important; 
    } 

    .stChatMessage p { 
        font-family: "Noto Serif SC", "Songti SC", serif !important; 
        font-size: 15px; 
        line-height: 1.9; 
        color: #1a1a1a; 
    } 

    .block-container { padding-bottom: 80px !important; } 
    .bottom-nav { 
        position: fixed; bottom: 0; left: 0; right: 0; height: 62px; 
        background: rgba(245,245,245,0.9); 
        border-top: 1px solid rgba(0,0,0,0.03); 
        display: flex; align-items: center; justify-content: space-around; 
        z-index: 9999; backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); 
    } 

    @media (max-width: 768px) { 
        .block-container { 
            padding-left: 12px !important; 
            padding-right: 12px !important; 
        } 
    } 

    /* 防止横向溢出 */ 
    .stApp, .block-container { 
        overflow-x: hidden !important; 
        max-width: 100vw !important; 
    } 
</style>""", unsafe_allow_html=True) 

# localStorage 自动登录：页面加载时读取保存的用户名 
import streamlit.components.v1 as components 

if "auto_login_checked" not in st.session_state: 
    st.session_state.auto_login_checked = False 

if not st.session_state.auto_login_checked: 
    auto_login_result = components.html(""" 
    <script> 
        const saved = localStorage.getItem('soul_echo_username'); 
        if (saved) { 
            window.parent.postMessage({type: 'soul_echo_autologin', username: saved}, '*'); 
        } else { 
            window.parent.postMessage({type: 'soul_echo_autologin', username: ''}, '*'); 
        } 
    </script> 
    <div id="auto_login_placeholder"></div> 
    """, height=0) 
    st.session_state.auto_login_checked = True

# ─── 数据库 ───────────────────────────────────────────

DB_PATH = "soul_echo.db"

@st.cache_resource
def get_db():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["service_key"]
    return create_client(url, key)

@st.cache_data(ttl=300)
def get_user_memories(user_id: str) -> str:
    """从 Supabase 读取用户记忆，拼成自然语言注入 prompt"""
    client = get_db()
    result = client.table("user_memories").select("key, content").eq("user_id", user_id).execute()
    if not result.data:
        return "暂无该用户的历史记忆。"
    lines = [f"- {row['content']}" for row in result.data]
    return "\n".join(lines)


def save_memory(user_id: str, key: str, content: str):
    """写入或更新一条用户记忆"""
    client = get_db()
    client.table("user_memories").upsert({
        "user_id": user_id,
        "key": key,
        "content": content,
        "updated_at": "now()"
    }).execute()

def _update_memories_from_conversation(user_id: str, messages: list):
    """每5轮对话后，用快速模型提取关键记忆写入数据库"""
    try:
        history_text = "\n".join([
            f"{'用户' if m['role']=='user' else 'AI'}：{m['content']}"
            for m in messages if m["role"] in ("user", "assistant")
        ])
        extractor = OpenAI(
            api_key=st.secrets["siliconflow"]["api_key"],
            base_url="https://api.siliconflow.cn/v1",
            timeout=30.0,
        )
        result = extractor.chat.completions.create(
            model=FAST_OPENING_MODEL,
            messages=[
                {"role": "system", "content": """从对话里提取用户的关键信息，输出JSON格式，最多3条，每条不超过20字。
格式：{"memories": [{"key": "主题标识", "content": "一句话描述"}]}
key只能是：themes（反复出现的话题）、emotions（情绪模式）、avoidance（回避的话题）
只输出JSON，不要其他任何内容。"""},
                {"role": "user", "content": history_text}
            ],
            max_tokens=200
        )
        raw = result.choices[0].message.content.strip()
        data = json.loads(raw)
        for item in data.get("memories", []):
            save_memory(user_id, item["key"], item["content"])
    except Exception:
        pass  # 记忆更新失败不影响主流程



# ─── 工具函数 ─────────────────────────────────────────

def save_line(user_id, original_text, edited_text, source_amber_id=None):
    client = get_db()
    client.table("saved_lines").insert({
        "user_id": user_id,
        "original_text": original_text,
        "edited_text": edited_text,
        "source_amber_id": source_amber_id
    }).execute()

def get_saved_lines(user_id):
    client = get_db()
    result = client.table("saved_lines").select(
        "id, original_text, edited_text, source_amber_id, created_at"
    ).eq("user_id", user_id).order("created_at", desc=True).execute()
    
    rows = result.data
    if not rows:
        return []
    
    # 获取有来源琥珀的条目的琥珀原文
    amber_ids = [r["source_amber_id"] for r in rows if r["source_amber_id"]]
    amber_dict = {}
    if amber_ids:
        ambers = client.table("ambers").select("id, content").in_("id", amber_ids).execute()
        amber_dict = {a["id"]: a["content"] for a in ambers.data}
    
    for row in rows:
        row["amber_content"] = amber_dict.get(row["source_amber_id"]) if row["source_amber_id"] else None
    
    return rows

def delete_saved_line(line_id):
    client = get_db()
    client.table("saved_lines").delete().eq("id", line_id).execute()

def get_ambers_for_wall(user_id, limit=12):
    client = get_db()
    ambers_result = client.table("ambers").select(
        "id, content, author_id, author_name, is_anonymous, weight, created_at"
    ).order("created_at", desc=True).limit(200).execute()
    ambers = ambers_result.data
    if not ambers:
        return []

    # 计算加权分数：越新权重越高，但保留随机性
    now = datetime.now()
    for a in ambers:
        try:
            created = datetime.fromisoformat(a["created_at"].replace("Z", "+00:00").replace("+00:00", ""))
        except Exception:
            created = now
        age_hours = max((now - created).total_seconds() / 3600, 0.1)
        # 时间衰减：24小时内权重最高，之后逐渐降低，但永远不为0
        time_score = 1 / (1 + age_hours / 24)
        # 加入随机扰动，避免每次结果完全一样
        a["_score"] = time_score * random.uniform(0.5, 1.5)

    # 按分数排序后取前 limit 个
    ambers.sort(key=lambda x: x["_score"], reverse=True)

    # 去重逻辑
    recently_seen: list = st.session_state.get("amber_seen_history", [])
    seen_set = set(recently_seen)

    fresh = [a for a in ambers if a["id"] not in seen_set]
    stale = [a for a in ambers if a["id"] in seen_set]

    selected = fresh[:limit]
    if len(selected) < limit:
        random.shuffle(stale)
        selected += stale[:limit - len(selected)]

    new_seen_ids = [a["id"] for a in selected[:4]]
    combined = recently_seen + new_seen_ids
    st.session_state.amber_seen_history = combined[-(5 * 4):]

    return selected

def prefetch_ambers_background(user_id):
    """后台预取下一批琥珀，存入 session_state"""
    try:
        next_batch = get_ambers_for_wall(user_id, limit=50)
        st.session_state._prefetched_ambers = next_batch[:4]
    except Exception:
        pass

def record_dwell(user_id, amber_id, seconds):
    client = get_db()
    
    # 检查是否已存在记录
    existing = client.table("user_affinity").select("dwell_seconds").eq("user_id", user_id).eq("amber_id", amber_id).execute()
    
    if existing.data:
        # 更新现有记录
        current_seconds = existing.data[0]["dwell_seconds"]
        client.table("user_affinity").update({
            "dwell_seconds": current_seconds + seconds
        }).eq("user_id", user_id).eq("amber_id", amber_id).execute()
    else:
        # 插入新记录
        client.table("user_affinity").insert({
            "user_id": user_id,
            "amber_id": amber_id,
            "dwell_seconds": seconds
        }).execute()

@st.cache_data(ttl=60)
def check_daily_upload(user_id):
    if user_id == "rim":
        return 0
    client = get_db()
    today = date.today().isoformat()
    result = client.table("daily_uploads").select("id").eq("user_id", user_id).eq("upload_date", today).execute()
    return len(result.data)

def get_daily_quota(user_id):
    """获取用户每日免费琥珀额度，订阅用户5颗，普通用户2颗"""
    return 5 if is_subscribed(user_id) else 2

def _open_amber(amber_id, content, author_id, ambers, user_id):
    dwell = time.time() - st.session_state.get("wall_start_time", time.time())
    threading.Thread(target=record_dwell, args=(user_id, amber_id, min(dwell, 120)), daemon=True).start()
    st.session_state.mode = "amber_detail"
    st.session_state.current_amber_id = amber_id
    st.session_state.current_amber_content = content
    st.session_state.current_amber_author = author_id
    st.session_state.wall_ambers = [dict(r) for r in ambers]
    st.session_state.wall_amber_index = [r["id"] for r in ambers].index(amber_id)
    st.session_state.messages = []
    st.session_state.opening_initialized = False

def submit_amber(user_id, content, author_name, is_anonymous, is_extra=False):
    client = get_db()
    today = date.today().isoformat()
    try:
        if is_extra:
                current_points = get_user_points(user_id)
                if current_points < 20:
                    return False
                client.table("users").update({"points": current_points - 20}).eq("username", user_id).execute()
                client.table("point_ledger").insert({"user_id": user_id, "delta": -20, "reason": "extra_amber"}).execute()
                get_user_info.clear()
        amber_result = client.table("ambers").insert({
            "content": content,
            "author_id": user_id,
            "author_name": author_name,
            "is_anonymous": 1 if is_anonymous else 0
        }).execute()
        amber_id = amber_result.data[0]["id"]
        client.table("daily_uploads").insert({
            "user_id": user_id,
            "upload_date": today,
            "amber_id": amber_id
        }).execute()
        st.session_state.all_ambers = get_ambers_for_wall(user_id, limit=50)
        check_daily_upload.clear()
        return True
    except Exception:
        return False

def send_message(amber_id, sender_id, receiver_id, content):
    client = get_db()
    client.table("messages").insert({
        "amber_id": amber_id,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "content": content
    }).execute()

def try_earn_comment_points(user_id, amber_id):
    """用户给琥珀写信时尝试赚积分，同一用户对同一琥珀只能赚一次，每日上限10次"""
    client = get_db()
    # 检查是否已经赚过
    already = client.table("comment_rewards").select("id").eq("user_id", user_id).eq("amber_id", amber_id).execute()
    if already.data:
        return False
    # 检查今日已赚次数
    today = date.today().isoformat()
    today_rewards = client.table("point_ledger").select("id", count="exact").eq("user_id", user_id).eq("reason", "write_comment").gte("created_at", today).execute()
    if today_rewards.count >= 10:
        return False
    # 赚积分
    client.table("comment_rewards").insert({"user_id": user_id, "amber_id": amber_id}).execute()
    client.table("point_ledger").insert({"user_id": user_id, "delta": 10, "reason": "write_comment", "ref_id": amber_id}).execute()
    client.table("users").update({"points": get_user_points(user_id) + 10}).eq("username", user_id).execute()
    get_user_info.clear()
    return True

@st.cache_data(ttl=60)
def get_user_info(user_id):
    """获取用户信息，包括积分和订阅状态"""
    client = get_db()
    result = client.table("users").select("points, is_subscribed").eq("username", user_id).execute()
    if result.data:
        return {
            "points": result.data[0]["points"],
            "is_subscribed": result.data[0].get("is_subscribed", False)
        }
    return {"points": 0, "is_subscribed": False}

def get_user_points(user_id):
    """获取用户当前积分"""
    return get_user_info(user_id)["points"]

def is_subscribed(user_id):
    """判断用户是否订阅"""
    return get_user_info(user_id)["is_subscribed"]

def light_up_comment(message_id, sender_id, amber_id):
    """琥珀主人点亮留言，给留言者额外赚10积分，每条留言只能点亮一次"""
    client = get_db()
    # 检查是否已点亮
    msg = client.table("messages").select("is_lit").eq("id", message_id).execute()
    if not msg.data or msg.data[0].get("is_lit"):
        return False
    # 标记已点亮
    client.table("messages").update({"is_lit": True}).eq("id", message_id).execute()
    # 给留言者加积分
    client.table("point_ledger").insert({"user_id": sender_id, "delta": 10, "reason": "comment_lit", "ref_id": message_id}).execute()
    client.table("users").update({"points": get_user_points(sender_id) + 10}).eq("username", sender_id).execute()
    get_user_info.clear()
    return True

def can_reply_free(user_id, amber_id, other_user_id):
    """判断这对用户在这块琥珀下是否还有免费回信机会。
    规则：同一对用户针对同一块琥珀，来回总次数超过1次后需要花积分。"""
    for attempt in range(3):
        try:
            client = get_db()
            result = client.table("messages").select("id", count="exact").eq("amber_id", amber_id).or_(
                f"and(sender_id.eq.{user_id},receiver_id.eq.{other_user_id}),and(sender_id.eq.{other_user_id},receiver_id.eq.{user_id})"
            ).execute()
            return result.count <= 1
        except Exception:
            if attempt == 2:
                return True
            time.sleep(0.5)

def deduct_stamp(user_id):
    """扣除10积分邮票，订阅用户免费，返回是否成功"""
    if is_subscribed(user_id):
        return True
    client = get_db()
    current = get_user_points(user_id)
    if current < 10:
        return False
    client.table("users").update({"points": current - 10}).eq("username", user_id).execute()
    client.table("point_ledger").insert({"user_id": user_id, "delta": -10, "reason": "stamp"}).execute()
    get_user_info.clear()
    return True

def get_active_users(exclude_user_id):
    client = get_db()
    three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
    result = client.table("users").select("username").neq("username", exclude_user_id).gte("last_active", three_days_ago).execute()
    return [row["username"] for row in result.data]

def send_post(sender_id, content):
    client = get_db()
    current = get_user_points(sender_id)
    if current < 30:
        return False, "积分不足"
    active_users = get_active_users(sender_id)
    if not active_users:
        return False, "暂时没有可以接收帖的用户，请稍后再试"
    receiver_id = random.choice(active_users)
    client.table("users").update({"points": current - 30}).eq("username", sender_id).execute()
    client.table("point_ledger").insert({"user_id": sender_id, "delta": -30, "reason": "post"}).execute()
    client.table("posts").insert({"sender_id": sender_id, "receiver_id": receiver_id, "content": content}).execute()
    get_user_info.clear()
    return True, "已寄出"

def check_post_refunds(user_id):
    client = get_db()
    now = datetime.now().isoformat()
    expired = client.table("posts").select("id").eq("sender_id", user_id).eq("is_replied", False).lt("expires_at", now).execute()
    if not expired.data:
        return
    for post in expired.data:
            current = get_user_points(user_id)
            client.table("users").update({"points": current + 15}).eq("username", user_id).execute()
            client.table("point_ledger").insert({"user_id": user_id, "delta": 15, "reason": "post_refund", "ref_id": str(post["id"])}).execute()
            client.table("posts").delete().eq("id", post["id"]).execute()
            get_user_info.clear()

def get_inbox(user_id):
    client = get_db()
    
    # 获取用户收到的所有消息
    messages_result = client.table("messages").select("id, content, created_at, is_read, amber_id, is_lit, sender_id").eq("receiver_id", user_id).order("created_at", desc=True).execute()
    messages = messages_result.data
    
    # 获取相关的琥珀内容
    amber_ids = [msg["amber_id"] for msg in messages if msg["amber_id"] is not None]
    if amber_ids:
        ambers_result = client.table("ambers").select("id, content, author_id").in_("id", amber_ids).execute()
        amber_dict = {item["id"]: item["content"] for item in ambers_result.data}
        amber_author_dict = {item["id"]: item["author_id"] for item in ambers_result.data}
        
        # 将琥珀内容添加到消息中
        for msg in messages:
            msg["amber_content"] = amber_dict.get(msg["amber_id"], "") if msg["amber_id"] else ""
            msg["amber_author_id"] = amber_author_dict.get(msg["amber_id"], "") if msg["amber_id"] else ""
    
    return messages

def mark_read(message_id):
    client = get_db()
    client.table("messages").update({"is_read": 1}).eq("id", message_id).execute()
    get_unread_count.clear()

@st.cache_data(ttl=30)
def get_unread_count(user_id):
    client = get_db()
    result = client.table("messages").select("id", count="exact").eq("receiver_id", user_id).eq("is_read", 0).execute()
    return result.count



# ─── Prompts（从 Supabase 动态加载） ──────────────────── 

MASTER_MODEL = "deepseek-ai/DeepSeek-V3" 
FAST_OPENING_MODEL = "Qwen/Qwen2.5-7B-Instruct" 

@st.cache_resource 
def load_prompt(path: str) -> str: 
    base_dir = os.path.dirname(os.path.abspath(__file__)) 
    full_path = os.path.join(base_dir, "prompts", path) 
    with open(full_path, "r", encoding="utf-8") as f: 
        return f.read()

# ─── 每日轻问题 ───────────────────────────────────────

@st.cache_data(ttl=3600)
def get_daily_question():
    today = date.today().isoformat()
    client = get_db()
    result = client.table("daily_questions").select("question").eq("question_date", today).execute()
    if result.data:
        return result.data[0]["question"]
    try:
        client = OpenAI(
            api_key=st.secrets["siliconflow"]["api_key"],
            base_url="https://api.siliconflow.cn/v1",
            timeout=30.0,
        )
        result = client.chat.completions.create(
            model=MASTER_MODEL,
            messages=[
                {"role": "system", "content": load_prompt("system/daily_question.md")},
                {"role": "user", "content": f"今天是{today}"}
            ],
            max_tokens=50
        )
        question = result.choices[0].message.content.strip()
        get_db().table("daily_questions").insert({"question_date": today, "question": question}).execute()
        return question
    except Exception:
        return "今天有什么话，还没说出口？"

# ─── Session State 初始化 ─────────────────────────────

if "mode" not in st.session_state:
    st.session_state.mode = "gallery"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_user_prompt" not in st.session_state:
    st.session_state.last_user_prompt = None
if "initial_assistant_message" not in st.session_state:
    st.session_state.initial_assistant_message = None
if "opening_initialized" not in st.session_state:
    st.session_state.opening_initialized = False
if "show_save_panel" not in st.session_state:
    st.session_state.show_save_panel = False
if "selected_line" not in st.session_state:
    st.session_state.selected_line = None

if "amber_seen_history" not in st.session_state:
    st.session_state.amber_seen_history = []

if "wall_refresh_count" not in st.session_state:
    st.session_state.wall_refresh_count = 0
if "wall_display_ambers" not in st.session_state:
    st.session_state.wall_display_ambers = []
if "_prefetched_ambers" not in st.session_state:
    st.session_state._prefetched_ambers = None
if "wall_ambers" not in st.session_state:
    st.session_state.wall_ambers = []
if "wall_amber_index" not in st.session_state:
    st.session_state.wall_amber_index = 0
if "current_amber_id" not in st.session_state:
    st.session_state.current_amber_id = None
if "current_amber_content" not in st.session_state:
    st.session_state.current_amber_content = None
if "current_amber_author" not in st.session_state:
    st.session_state.current_amber_author = None
if "from_amber_redirect" not in st.session_state:
    st.session_state.from_amber_redirect = False
if "entry_path" not in st.session_state:
    st.session_state.entry_path = None
if "show_write_panel" not in st.session_state:
    st.session_state.show_write_panel = False
if "write_panel_mode" not in st.session_state:
    st.session_state.write_panel_mode = None
if "chat_mode" not in st.session_state:
    st.session_state.chat_mode = "letter"  # "letter" 或 "chat"

# ─── 登录/注册逻辑 ────────────────────────────────────

if "username" not in st.session_state:
    st.session_state.username = None

if st.session_state.username is None:
    # 尝试从 URL query param 读取自动登录（由 localStorage JS 写入）
    params = st.query_params
    auto_user = params.get("_u", None)
    if auto_user:
        client = get_db()
        result = client.table("users").select("username").eq("username", auto_user).execute()
        if result.data:
            st.session_state.username = auto_user
            get_db().table("users").update({"last_active": datetime.now().isoformat()}).eq("username", auto_user).execute()
            st.query_params.clear()
            st.rerun()

if st.session_state.username is None:
    st.markdown("""
    <div style="text-align:center; padding:60px 20px 24px 20px;">
        <h1 style="font-size:28px; font-weight:300; letter-spacing:8px;
                   color:#1a1a1a; margin:0 0 40px 0;">Soul Echo</h1>
    </div>
    """, unsafe_allow_html=True)

    auth_mode = st.radio("", ["登录", "注册"], horizontal=True, label_visibility="collapsed")

    if "auth_key_suffix" not in st.session_state:
        st.session_state.auth_key_suffix = str(random.randint(1000, 9999))
    key_suffix = st.session_state.auth_key_suffix
    
    if auth_mode == "登录":
        st.subheader("登录")
        login_username = st.text_input("昵称", key=f"login_username_{key_suffix}")
        login_password = st.text_input("密码", type="password", key=f"login_password_{key_suffix}")
        if st.button("登录", key="btn_login"):
            if login_username and login_password:
                with st.spinner("登录中…"):
                    cleaned_username = login_username.strip().lower()
                    client = get_db()
                    hashed_pw = hashlib.sha256(login_password.encode()).hexdigest()
                    result = client.table("users").select("*").eq("username", cleaned_username).eq("password", hashed_pw).execute()
                    user = result.data[0] if result.data else None
                    if user:
                        st.session_state.username = user["username"]
                        get_db().table("users").update({"last_active": datetime.now().isoformat()}).eq("username", user["username"]).execute()
                        components.html(f"""
                        <script>
                            localStorage.setItem('soul_echo_username', '{user["username"]}');
                            const url = new URL(window.parent.location.href);
                            url.searchParams.set('_u', '{user["username"]}');
                            window.parent.history.replaceState({{}}, '', url.toString());
                        </script>
                        """, height=0)
                        st.rerun()
                    else:
                        st.error("昵称或密码错误")
            else:
                st.warning("请输入昵称和密码")
    else:
        st.subheader("注册")
        reg_username = st.text_input("昵称", key=f"reg_username_{key_suffix}")
        reg_password = st.text_input("密码", type="password", key=f"reg_password_{key_suffix}")
        if st.button("注册", key="btn_register"):
            if reg_username and reg_password:
                with st.spinner("注册中…"):
                    cleaned_username = reg_username.strip().lower()
                    client = get_db()
                    try:
                        hashed_pw = hashlib.sha256(reg_password.encode()).hexdigest()
                        client.table("users").insert({
                            "username": cleaned_username,
                            "password": hashed_pw
                        }).execute()
                        st.session_state.username = cleaned_username
                        components.html(f"""
                        <script>
                            localStorage.setItem('soul_echo_username', '{cleaned_username}');
                            const url = new URL(window.parent.location.href);
                            url.searchParams.set('_u', '{cleaned_username}');
                            window.parent.history.replaceState({{}}, '', url.toString());
                        </script>
                        """, height=0)
                        st.success("注册成功！")
                        st.rerun()
                    except Exception:
                        st.error("这个昵称已经被使用了")
            else:
                st.warning("请输入昵称和密码")

    st.stop()

# ─── 底部导航栏 ────────────────────────────────────────
_mode = st.session_state.get("mode", "gallery")
if _mode not in ("login"):
    st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"]:has(
        button[key="nav_gallery"]
    ) {
        position: fixed !important;
        bottom: 0 !important; left: 0 !important; right: 0 !important;
        z-index: 9999 !important;
        background: rgba(250,250,250,0.97) !important;
        border-top: none !important;
        padding: 0 !important; margin: 0 !important;
        width: 100vw !important;
        max-width: 100vw !important;
        box-sizing: border-box !important;
        display: flex !important;
        flex-wrap: nowrap !important;
        backdrop-filter: blur(12px) !important;
    }
    div[data-testid="stHorizontalBlock"]:has(
        button[key="nav_gallery"]
    ) > div[data-testid="stVerticalBlock"] {
        flex: 1 1 0 !important;
        min-width: 0 !important;
        overflow: hidden !important;
    }
    button[key="nav_gallery"],
    button[key="nav_write"],
    button[key="nav_mine"] {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        height: 62px !important;
        width: 100% !important;
        font-size: 11px !important;
        color: #888888 !important;
        letter-spacing: 0.5px !important;
        padding: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    _c1, _c2, _c3 = st.columns(3)
    with _c1:
        _label = ("·  广 场  ·" if _mode == "gallery" else "广 场")
        if st.button(_label, key="nav_gallery", use_container_width=True):
            st.session_state.mode = "gallery"
            st.rerun()
    with _c2:
        _label = ("·  写 琥 珀  ·" if _mode == "write_amber" else "写 琥 珀")
        if st.button(_label, key="nav_write", use_container_width=True):
            st.session_state.mode = "write_amber"
            st.rerun()
    with _c3:
        _label = ("·  我 的  ·" if _mode == "my_ambers" else "我 的")
        if st.button(_label, key="nav_mine", use_container_width=True):
            st.session_state.mode = "my_ambers"
            st.rerun()
# ──────────────────────────────────────────────────────

# 预热提示词缓存，避免进入聊天时出现 Running 提示
if "prompts_warmed" not in st.session_state:
    # 只加载仍在使用的提示词
    load_prompt("system/daily_question.md")
    load_prompt("core/soul_observer.md")
    st.session_state.prompts_warmed = True

# ─── gallery 模式 ─────────────────────────────────────

if st.session_state.mode == "gallery":
    user_id = st.session_state.username

    unread = get_unread_count(user_id)
    
    # 标题布局
    st.markdown("""
    <div style="padding:48px 0 24px 0;">
        <h1 style="font-size:26px; font-weight:300; letter-spacing:8px;
                   color:#1a1a1a; margin:0;">Soul Echo</h1>
    </div>
    """, unsafe_allow_html=True)

    daily_q = get_daily_question()
    today_upload_count = check_daily_upload(user_id)

    st.markdown(f"""
    <div style="max-width:500px; margin:0 auto 24px auto; padding:8px 0; text-align:center;">
        <p style="font-family:'Songti SC', serif; color:#555; font-size:14px; margin:0; letter-spacing:1px;">{daily_q}</p>
    </div>
    """, unsafe_allow_html=True)

    quota = get_daily_quota(user_id)
    if today_upload_count >= quota:
        user_points = get_user_points(user_id)
        st.markdown(
            f"<p style='text-align:center; color:#94a3b8; font-size:13px;'>"
            f"今天已留下{today_upload_count}块琥珀。再发一块需要消耗20积分（当前积分：{user_points}）。</p>",
            unsafe_allow_html=True)
        if user_points >= 20:
            if st.button("再写一块（-20积分）", key="open_upload"):
                st.session_state.mode = "write_amber"
                st.session_state.extra_amber = True
                st.rerun()
        else:
            st.markdown(
                "<p style='text-align:center; color:#94a3b8; font-size:13px;'>积分不足，无法再发。</p>",
                unsafe_allow_html=True)
    else:
        if st.button("写今天的琥珀", key="open_upload"):
            st.session_state.mode = "write_amber"
            st.session_state.extra_amber = False
            st.rerun()
        st.markdown(
            "<p style='color:#888888; font-size:12px; margin-top:4px; line-height:1.6;'>"
            "每天2次免费额度 · 给人写信 +10积分 · 发帖消耗30积分</p>",
            unsafe_allow_html=True)



    st.markdown(
        "<hr style='border:0; border-top:1px solid rgba(0,0,0,0.06); margin:16px 0 28px 0;'>",
        unsafe_allow_html=True)

    # 每次进入 gallery 都重新从数据库拉取，确保能看到最新琥珀
    if "wall_display_ambers" not in st.session_state or not st.session_state.wall_display_ambers:
        fresh_pool = get_ambers_for_wall(user_id, limit=50)
        st.session_state.all_ambers = fresh_pool
        st.session_state.wall_display_ambers = fresh_pool[:4]
        # 第一次加载完，立刻后台预取下一批
        threading.Thread(target=prefetch_ambers_background, args=(user_id,), daemon=True).start()

    ambers = st.session_state.wall_display_ambers or []
    
    if "wall_start_time" not in st.session_state:
        st.session_state.wall_start_time = time.time()

    if not ambers:
        st.markdown("<p style='text-align:center; color:#94a3b8;'>墙上还没有琥珀。</p>",
            unsafe_allow_html=True)
    else:
        for i, row in enumerate(ambers[:4]):
            amber_id = row["id"]
            content = row["content"]
            if row["is_anonymous"] == 1:
                display_name = "匿名"
            elif row["author_id"] == st.session_state.username:
                display_name = st.session_state.username
            else:
                display_name = row["author_name"] or "匿名"
            
            match = re.search(r'[，。！？、；]', content[4:12])
            if match:
                cut = 4 + match.start() + 1
                preview = content[:cut] + "……"
            else:
                preview = content[:8] + "……"
            st.markdown(f""" 
            <div style="background:#12151A; border-radius:4px; 
                        padding:32px 28px 20px 28px; margin-bottom:4px;"> 
                <p style="color:#EBEBF5; font-size:17px; line-height:1.8; 
                          margin:0 0 20px 0; letter-spacing:0.05em; 
                          font-family:'Noto Serif SC', serif;">{preview}</p> 
                <div style="display:flex; justify-content:space-between; align-items:center;"> 
                    <span style="color:#404050; font-size:11px; letter-spacing:2px;">— {display_name}</span> 
                </div> 
            </div> 
            """, unsafe_allow_html=True) 
            if st.button("打 开", key=f"open_amber_{amber_id}"): 
                _open_amber(amber_id, content, row["author_id"], ambers, user_id) 
                st.rerun()

    # 刷新按钮放中间
    wall_refresh = st.session_state.get("wall_refresh_count", 0)
    st.markdown("<div style='text-align:center; margin-top:24px;'>", unsafe_allow_html=True)
    if st.button("↺  换几块", key="refresh_wall", type="primary"):
        st.session_state.wall_refresh_count = wall_refresh + 1
        st.session_state.wall_start_time = time.time()
        # 优先用预取好的数据，实现秒切
        if st.session_state.get("_prefetched_ambers"):
            st.session_state.wall_display_ambers = st.session_state._prefetched_ambers
            st.session_state._prefetched_ambers = None
            # 点击后立刻在后台取下一批
            threading.Thread(target=prefetch_ambers_background, args=(user_id,), daemon=True).start()
        else:
            # 没有预取数据时降级为直接查询
            fresh_pool = get_ambers_for_wall(user_id, limit=50)
            st.session_state.all_ambers = fresh_pool
            st.session_state.wall_display_ambers = fresh_pool[:4]
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ─── amber_detail 模式 ────────────────────────────────

elif st.session_state.mode == "amber_detail":
    user_id = st.session_state.username
    amber_id = st.session_state.current_amber_id
    content = st.session_state.current_amber_content
    author_id = st.session_state.current_amber_author
    wall_ambers = st.session_state.get("wall_ambers", [])
    idx = st.session_state.get("wall_amber_index", 0)

    if st.session_state.get("last_amber_id") != amber_id:
        st.session_state.amber_open_time = time.time()
        st.session_state.last_amber_id = amber_id

    col_back, col_next = st.columns([1, 1])
    with col_back:
        if st.button("← 返回"):
            dwell = time.time() - st.session_state.get("amber_open_time", time.time())
            threading.Thread(target=record_dwell, args=(user_id, amber_id, min(dwell, 300)), daemon=True).start()
            st.session_state.mode = "gallery"
            st.rerun()
    with col_next:
        if len(wall_ambers) > 1 and st.button("下一块 →"):
            dwell = time.time() - st.session_state.get("amber_open_time", time.time())
            threading.Thread(target=record_dwell, args=(user_id, amber_id, min(dwell, 300)), daemon=True).start()
            next_idx = (idx + 1) % len(wall_ambers)
            next_a = wall_ambers[next_idx]
            st.session_state.current_amber_id = next_a["id"]
            st.session_state.current_amber_content = next_a["content"]
            st.session_state.current_amber_author = next_a["author_id"]
            st.session_state.wall_amber_index = next_idx
            st.session_state.messages = []
            st.session_state.opening_initialized = False
            st.rerun()

    st.markdown(f"""
    <div style="max-width:540px; margin:16px auto 16px auto;
                padding:24px 32px; border-radius:8px;
                background:rgba(0,0,0,0.02);
                border:none;">
        <p style="color:#1a1a1a; font-size:16px; line-height:1.9; margin:0;">
            {content}
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.session_state.setdefault("_btn_feedback", "")

    # 手动切换模式
    col_letter, col_chat = st.columns(2)
    with col_letter:
        if st.button("给ta写封信", use_container_width=True):
            st.session_state.chat_mode = "letter"
            st.rerun()
    with col_chat:
        if st.button("和AI聊这块琥珀", use_container_width=True):
            st.toast("正在唤醒琥珀…")
            st.session_state.chat_mode = "chat"
            st.rerun()

    st.markdown("<hr style='margin: 10px 0 20px 0;'>", unsafe_allow_html=True)

    if st.session_state.chat_mode == "letter":
        # 原有的写信表单代码（完全不变）
        with st.form(key="letter_form", clear_on_submit=True):
            if author_id == user_id:
                st.markdown("<p style='color:#94a3b8; font-size:13px;'>这是你的琥珀。也可以给自己写一封信。</p>", unsafe_allow_html=True)
                letter = st.text_area("", placeholder="写给此刻的自己……", height=120, 
                                   label_visibility="collapsed")
                submit_button = st.form_submit_button("寄给自己")
                if submit_button and letter.strip():
                    send_message(amber_id, user_id, user_id, letter.strip())
                    st.toast("信件已稳妥寄出", icon="🕊️")
            else:
                letter = st.text_area("", placeholder="只有对方能看见……",
                    height=120, label_visibility="collapsed")
                is_free_send = can_reply_free(user_id, amber_id, author_id)
                user_points_now = get_user_points(user_id)
                if not is_free_send:
                    st.markdown(
                        f"<p style='color:#888888; font-size:12px;'>续信需要消耗10积分邮票（当前积分：{user_points_now}）</p>",
                        unsafe_allow_html=True)
                label_send = "寄出去（-10积分）" if not is_free_send else "寄出去"
                submit_button = st.form_submit_button(label_send)
                if submit_button:
                    if letter.strip():
                        if not is_free_send:
                            ok = deduct_stamp(user_id)
                            if not ok:
                                st.warning("积分不足，无法续信。")
                                st.stop()
                        send_message(amber_id, user_id, author_id, letter.strip())
                        earned = try_earn_comment_points(user_id, amber_id) if is_free_send else False
                        if earned:
                            st.toast("信件已稳妥寄出，获得10积分 🪙", icon="🕊️")
                        else:
                            st.toast("信件已稳妥寄出", icon="🕊️")
                    else:
                        st.warning("还没写什么内容。")
    else:
        # 原有的聊天内容（直接放代码，不需要 tab 包裹）
        if not st.session_state.opening_initialized:
            st.session_state.opening_initialized = True
            client_init = OpenAI(
                api_key=st.secrets["siliconflow"]["api_key"],
                base_url="https://api.siliconflow.cn/v1",
                timeout=60.0,
            )
            stream = client_init.chat.completions.create(
                model=MASTER_MODEL,
                messages=[
                    {"role": "system", "content": load_prompt("core/soul_observer.md").replace("{memories}", get_user_memories(st.session_state.username))},
                    {"role": "user", "content": f"琥珀文本：{content}"}
                ],
                stream=True
            )
            opening_chunks = []
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    opening_chunks.append(chunk.choices[0].delta.content)
            opening_text = "".join(opening_chunks)
            st.session_state.messages.append({"role": "assistant", "content": opening_text})
            st.session_state.initial_assistant_message = None

        # 消息循环渲染
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # 存下一句话的入口
        ai_messages = [m["content"] for m in st.session_state.messages if m["role"] == "assistant"]
        if len(ai_messages) >= 1:
            if st.button("存下一句话", key="open_save_panel"):
                st.session_state.show_save_panel = not st.session_state.get("show_save_panel", False)
                st.session_state.selected_line = None
                st.rerun()

        if st.session_state.get("show_save_panel"):
            recent_ai = ai_messages[-3:] if len(ai_messages) >= 3 else ai_messages
            recent_ai = list(reversed(recent_ai))
            
            st.markdown(
                "<p style='color:#888888; font-size:12px; margin:12px 0 8px 0;'>选一句让你停住的话</p>",
                unsafe_allow_html=True)
            
            for i, line in enumerate(recent_ai):
                preview = line[:40] + "…" if len(line) > 40 else line
                if st.button(preview, key=f"select_line_{i}"):
                    st.session_state.selected_line = line
                    st.rerun()
            
            if st.session_state.get("selected_line"):
                st.markdown(
                "<p style='color:#888888; font-size:12px; margin:12px 0 4px 0;'>这句话还差一点像你。</p>",
                unsafe_allow_html=True)
                edited = st.text_area(
                    "", value=st.session_state.selected_line,
                    height=100, label_visibility="collapsed",
                    key="save_line_edit")
                col_confirm, col_cancel = st.columns([1, 1])
                with col_confirm:
                    if st.button("就是这句", key="save_line_confirm"):
                        save_line(
                            user_id=st.session_state.username,
                            original_text=st.session_state.selected_line,
                            edited_text=edited,
                            source_amber_id=st.session_state.current_amber_id
                        )
                        st.session_state.show_save_panel = False
                        st.session_state.selected_line = None
                        st.toast("已存入私人库 ✦")
                        st.rerun()
                with col_cancel:
                    if st.button("取消", key="save_line_cancel"):
                        st.session_state.show_save_panel = False
                        st.session_state.selected_line = None
                        st.rerun()

        # "我想写点什么"按钮和内嵌面板
        col_write, _ = st.columns([2, 3])
        with col_write:
            if st.button("我想写点什么", key=f"write_panel_btn_{st.session_state.mode}"):
                st.session_state.show_write_panel = not st.session_state.show_write_panel
                st.session_state.write_panel_mode = None

        if st.session_state.show_write_panel:
            with st.container():
                st.markdown(f"""
                <div style="padding:24px; margin:8px 0; border-radius:8px; 
                background:rgba(0,0,0,0.02); border:none;">
                """, unsafe_allow_html=True)

                col_p, col_a = st.columns(2)
                with col_p:
                    if st.button("写一个帖", key=f"panel_post_{st.session_state.mode}"):
                        st.session_state.write_panel_mode = "post"
                with col_a:
                    if st.button("写一块琥珀", key=f"panel_amber_{st.session_state.mode}"):
                        st.session_state.write_panel_mode = "amber"

                if st.session_state.write_panel_mode == "post":
                    user_points = get_user_points(st.session_state.username)
                    if user_points < 30:
                        st.markdown(
                            "<p style='color:#94a3b8; font-size:13px;'>积分不足（需要30积分）。</p>",
                            unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f"<p style='color:#888888; font-size:12px;'>写下此刻想说的话，随机落到陌生人信箱。消耗30积分（当前：{user_points}）</p>",
                            unsafe_allow_html=True)
                        with st.form(key=f"inline_post_form_{st.session_state.mode}", clear_on_submit=True):
                            post_text = st.text_area("", placeholder="此刻最想让某个陌生人听到的话……（最多100字）",
                                height=100, max_chars=100, label_visibility="collapsed")
                            if st.form_submit_button("放它漂走") and post_text.strip():
                                ok, msg = send_post(st.session_state.username, post_text.strip())
                                if ok:
                                    st.toast("帖已寄出 🕊️")
                                    st.session_state.show_write_panel = False
                                    st.session_state.write_panel_mode = None
                                    st.rerun()
                                else:
                                    st.warning(msg)

                elif st.session_state.write_panel_mode == "amber":
                    user_id_panel = st.session_state.username
                    today_count = check_daily_upload(user_id_panel)
                    quota = get_daily_quota(user_id_panel)
                    if today_count >= quota:
                        user_points = get_user_points(user_id_panel)
                        if user_points < 20:
                            st.markdown(
                                "<p style='color:#94a3b8; font-size:13px;'>今日额度已用完，积分也不足了。</p>",
                                unsafe_allow_html=True)
                        else:
                            st.markdown(
                                f"<p style='color:#888888; font-size:12px;'>今日额度已用完，再发一块消耗20积分（当前：{user_points}）</p>",
                                unsafe_allow_html=True)
                            with st.form(key=f"inline_amber_form_{st.session_state.mode}", clear_on_submit=True):
                                amber_text = st.text_area("", placeholder="今天最有重量的那句话……（最多100字）",
                                    height=100, max_chars=100, label_visibility="collapsed")
                                if st.form_submit_button("留下这块琥珀（-20积分）") and amber_text.strip():
                                    ok = submit_amber(user_id_panel, amber_text.strip(), user_id_panel, False, is_extra=True)
                                    if ok:
                                        st.toast("琥珀已留下 🪨")
                                        st.session_state.show_write_panel = False
                                        st.session_state.write_panel_mode = None
                                        st.rerun()
                                    else:
                                        st.warning("发送失败，请检查积分。")
                    else:
                        with st.form(key=f"inline_amber_form_{st.session_state.mode}", clear_on_submit=True):
                            amber_text = st.text_area("", placeholder="今天最有重量的那句话……（最多100字）",
                                height=100, max_chars=100, label_visibility="collapsed")
                            if st.form_submit_button("留下这块琥珀") and amber_text.strip():
                                ok = submit_amber(user_id_panel, amber_text.strip(), user_id_panel, False, is_extra=False)
                                if ok:
                                    st.toast("琥珀已留下 🪨")
                                    st.session_state.show_write_panel = False
                                    st.session_state.write_panel_mode = None
                                    st.rerun()
                                else:
                                    st.warning("发送失败。")

                st.markdown("</div>", unsafe_allow_html=True)

        # 输入框直接放在最后
        if prompt := st.chat_input("说说这块琥珀让你想到了什么…"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.last_user_prompt = prompt
            st.rerun()

# ─── inbox 模式 ───────────────────────────────────────

elif st.session_state.mode == "inbox":
    user_id = st.session_state.username
    if st.button("← 返回"):
        st.session_state.mode = "gallery"
        st.rerun()

    st.markdown(
        "<h3 style='font-weight:300; letter-spacing:3px; margin-bottom:24px;'>收件箱</h3>",
        unsafe_allow_html=True)

    check_post_refunds(user_id)

    client_db = get_db()
    posts_received = client_db.table("posts").select("id, content, created_at, is_replied, sender_id").eq("receiver_id", user_id).order("created_at", desc=True).execute()
    if posts_received.data:
        st.markdown(
            "<p style='color:#888888; font-size:13px; letter-spacing:1px; margin-bottom:12px;'>帖</p>",
            unsafe_allow_html=True)
        for post in posts_received.data:
            st.markdown(f"""
            <div style="padding:24px; margin-bottom:16px; border-radius:4px; background:rgba(0,0,0,0.03); border:none; box-shadow: 0 4px 20px rgba(0,0,0,0.03);">
                <p style="color:#2D2D2D; font-size:15px; line-height:1.8; margin:0;">
                    {post["content"]}
                </p>
                <p style="color:#94a3b8; font-size:11px; margin:8px 0 0 0;">
                    {str(post["created_at"])[:10]} · 来自陌生人
                </p>
            </div>
            """, unsafe_allow_html=True)
            if not post["is_replied"]:
                with st.expander("回信"):
                    with st.form(key=f"post_reply_{post['id']}", clear_on_submit=True):
                        reply_text = st.text_area("", placeholder="写下回信……", height=100,
                            label_visibility="collapsed")
                        if st.form_submit_button("寄出去"):
                            if reply_text.strip():
                                send_message(None, user_id, post["sender_id"], reply_text.strip())
                                client_db.table("posts").update({"is_replied": True}).eq("id", post["id"]).execute()
                                st.toast("回信已寄出", icon="🕊️")
                                st.rerun()
                            else:
                                st.warning("还没写什么内容。")
        st.markdown(
            "<hr style='border:0; border-top:1px solid rgba(0,0,0,0.06); margin:16px 0;'>",
            unsafe_allow_html=True)

    letters = get_inbox(user_id)
    if not letters:
        st.markdown("<p style='color:#94a3b8; font-size:14px;'>还没有人给你写信。</p>",
            unsafe_allow_html=True)
    else:
        for letter in letters:
            mark_read(letter["id"])
            amber_content = letter.get("amber_content") or ""
            amber_preview = amber_content[:40] + "……" if len(amber_content) > 40 else amber_content
            is_lit = letter.get("is_lit", False)
            is_own_amber = letter.get("amber_author_id") == user_id
            st.markdown(f"""
            <div style="padding:24px; margin-bottom:16px; border-radius:4px; background:rgba(0,0,0,0.03); border:none; box-shadow: 0 4px 20px rgba(0,0,0,0.03);">
                <p style="color:#94a3b8; font-size:12px; margin:0 0 8px 0;">
                    关于：{amber_preview}
                </p>
                <p style="color:#2D2D2D; font-size:15px; line-height:1.8; margin:0;">
                    {letter["content"]}
                </p>
                <p style="color:#94a3b8; font-size:11px; margin:8px 0 0 0;">
                    {str(letter["created_at"])[:10]}
                    {"　✦ 已点亮" if is_lit else ""}
                </p>
            </div>
            """, unsafe_allow_html=True)
            if is_own_amber and not is_lit:
                if st.button("点亮这封信", key=f"lit_{letter['id']}"):
                    light_up_comment(letter["id"], letter.get("sender_id"), letter["amber_id"])
                    st.toast("已点亮，对方获得10积分 ✦")
                    st.rerun()
            # 回信入口（收件人可以回信给发件人）
            sender = letter.get("sender_id")
            if sender and sender != user_id:
                is_free = can_reply_free(user_id, letter["amber_id"], sender)
                user_points = get_user_points(user_id)
                with st.expander("回信"):
                    if not is_free and user_points < 10:
                        st.markdown(
                            "<p style='color:#94a3b8; font-size:13px;'>续信需要10积分邮票，当前积分不足。</p>",
                            unsafe_allow_html=True)
                    else:
                        if not is_free:
                            st.markdown(
                                f"<p style='color:#888888; font-size:12px;'>续信需要消耗10积分邮票（当前积分：{user_points}）</p>",
                            unsafe_allow_html=True)
                        with st.form(key=f"reply_form_{letter['id']}", clear_on_submit=True):
                            reply_text = st.text_area("", placeholder="写下回信……", height=100,
                                label_visibility="collapsed")
                            label = "寄出去（-10积分）" if not is_free else "寄出去"
                            if st.form_submit_button(label):
                                if reply_text.strip():
                                    if not is_free:
                                        ok = deduct_stamp(user_id)
                                        if not ok:
                                            st.warning("积分不足，无法续信。")
                                            st.stop()
                                    send_message(letter["amber_id"], user_id, sender, reply_text.strip())
                                    st.toast("回信已寄出", icon="🕊️")
                                    st.rerun()
                                else:
                                    st.warning("还没写什么内容。")



# ─── write_amber 模式 ────────────────────────────────────

elif st.session_state.mode == "write_amber":
    user_id = st.session_state.username
    
    if st.button("← 返回首页", key="back_to_gallery"):
        st.session_state.mode = "gallery"
        st.rerun()
    
    st.markdown("""
    <div style="text-align:center; padding:48px 0 24px 0;">
        <h1 style="font-size:26px; font-weight:300; letter-spacing:8px;
                   color:#1a1a1a; margin:0;">写今天的琥珀</h1>
    </div>
    """, unsafe_allow_html=True)
    
    daily_q = get_daily_question()
    today_count = check_daily_upload(user_id)
    quota = get_daily_quota(user_id)

    st.markdown(f"""
    <div style="max-width:500px; margin:0 auto 24px auto; padding:8px 0; text-align:center;">
        <p style="font-family:'Songti SC', serif; color:#555; font-size:14px; margin:0; letter-spacing:1px;">{daily_q}</p>
    </div>
    """, unsafe_allow_html=True)

    if today_count >= quota:
        st.markdown(
            "<p style='text-align:center; color:#94a3b8; font-size:13px;'>"
            "今天的琥珀额度已用完。</p>", unsafe_allow_html=True)
    else:
        with st.form("upload_form", clear_on_submit=True):
            st.markdown("""
            <div style="padding:24px; margin-bottom:16px; border-radius:4px; background:rgba(0,0,0,0.03); border:none; box-shadow: 0 4px 20px rgba(0,0,0,0.03);">
                <p style="color:#2D2D2D; font-size:13px; margin:0; line-height:1.6;">
                    每天有两次机会，用心留下。
                </p>
            </div>
            """, unsafe_allow_html=True)
            amber_text = st.text_area("", placeholder="今天最有重量的那句话……（最多100字）",
                height=100, max_chars=100, label_visibility="collapsed")
            anon_choice = st.radio("署名", ["匿名", "留名"],
                horizontal=True, label_visibility="collapsed")
            author_name = "匿名"
            if anon_choice == "留名":
                author_name = st.text_input("你的名字", max_chars=20)
            if st.form_submit_button("留下这块琥珀") and amber_text.strip():
                is_extra = st.session_state.get("extra_amber", False)
                ok = submit_amber(user_id, amber_text.strip(), author_name, anon_choice == "匿名", is_extra=is_extra)
                if ok:
                    st.toast("琥珀已成功留下", icon="🪨")
                    st.session_state.mode = "gallery"
                    st.rerun()
                else:
                    st.warning("今天已经上传过了。")

# ─── my_ambers 模式 ──────────────────────────────────────

elif st.session_state.mode == "my_ambers":
    user_id = st.session_state.username
    
    if st.button("← 返回首页", key="back_from_my_ambers"):
        st.session_state.mode = "gallery"
        st.rerun()
    
    st.markdown("""
    <div style="text-align:center; padding:48px 0 24px 0;">
        <h1 style="font-size:26px; font-weight:300; letter-spacing:8px;
                   color:#1a1a1a; margin:0;">我的</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div style="background:rgba(0,0,0,0.02);border-radius:8px;padding:24px;margin-bottom:24px;border:none;">', unsafe_allow_html=True)
    user_id = st.session_state.username
    _info = get_user_info(user_id)
    _points = _info["points"]
    _subbed = _info["is_subscribed"]
    st.markdown(f"<p style='font-size:13px; color:#888888;'>积分：{_points}</p>", unsafe_allow_html=True)
    if _subbed:
        st.markdown(
            "<p style='font-size:12px; color:#888888; margin:0;'>订阅中 ✦</p>",
            unsafe_allow_html=True)
    if st.session_state.mode in ["amber_detail", "inbox"]:
        if st.button("← 首页", key="back_home"):
            st.session_state.mode = "gallery"
            st.session_state.messages = []
            st.session_state.entry_path = None
            st.session_state.opening_initialized = False
            st.session_state.from_amber_redirect = False
            st.rerun()
    unread = get_unread_count(user_id)
    
    inbox_label = f"收件箱  {unread} 条未读" if unread > 0 else "收件箱"
    if st.button(inbox_label, key="open_inbox"):
        st.session_state.mode = "inbox"
        st.rerun()
    
    if st.button("我的琥珀", key="my_ambers"):
        st.session_state.mode = "my_ambers"
        st.rerun()

    if st.button("发一个帖", key="write_post"):
        st.session_state.mode = "write_post"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 私人库入口
    if "show_saved_lines" not in st.session_state:
        st.session_state.show_saved_lines = False
    if "show_my_ambers" not in st.session_state:
        st.session_state.show_my_ambers = False

    st.markdown("""
<div style="margin:0 0 12px 0;">
    <p style="font-size:13px; letter-spacing:4px; color:#888888; margin:0;">私人库</p>
    <hr style="border:0; border-top:1px solid rgba(0,0,0,0.06); margin:8px 0 0 0;">
</div>
""", unsafe_allow_html=True)

    saved_label = "私人库 ✦" if not st.session_state.show_saved_lines else "私人库 ✦ ▲"
    if st.button(saved_label, key="toggle_saved_lines"):
        st.session_state.show_saved_lines = not st.session_state.show_saved_lines
        st.rerun()

    if st.session_state.show_saved_lines:
        saved = get_saved_lines(user_id)
        if not saved:
            st.markdown(
                "<p style='text-align:center; color:#94a3b8; font-size:13px; margin:16px 0;'>还没有存下任何句子。</p>",
                unsafe_allow_html=True)
        else:
            for row in saved:
                amber_content = row.get("amber_content")
                edited_text = row.get("edited_text") or row.get("original_text")
                line_id = row["id"]
                
                if amber_content:
                    st.markdown(f"""
                    <div style="padding:24px; margin-bottom:16px; border-radius:4px; background:rgba(0,0,0,0.03); border:none; box-shadow: 0 4px 20px rgba(0,0,0,0.03);">
                        <p style="color:#94a3b8; font-size:12px; line-height:1.7; margin:0 0 10px 0;
                                  border-left:2px solid rgba(0,0,0,0.1); padding-left:10px;">
                            {amber_content}
                        </p>
                        <p style="color:#2D2D2D; font-size:15px; line-height:1.9; margin:0;">
                            {edited_text}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="padding:24px; margin-bottom:16px; border-radius:4px; background:rgba(0,0,0,0.03); border:none; box-shadow: 0 4px 20px rgba(0,0,0,0.03);">
                        <p style="color:#2D2D2D; font-size:15px; line-height:1.9; margin:0;">
                            {edited_text}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("删除", key=f"delete_saved_{line_id}"):
                        delete_saved_line(line_id)
                        st.toast("已删除")
                        st.rerun()
                with col2:
                    if st.button("🖼 分享", key=f"share_{line_id}"):
                        st.session_state[f"show_card_{line_id}"] = not st.session_state.get(f"show_card_{line_id}", False)

                if st.session_state.get(f"show_card_{line_id}"):
                    from utils.share_card import  generate_share_card
                    template = st.radio(
                        "选择底图",
                        ["obsidian", "white", "cinema"],
                        format_func=lambda x: {"obsidian": "黑曜石", "white": "白", "cinema": "电影票"}[x],
                        key=f"tpl_{line_id}",
                        horizontal=True
                    )
                    amber_content = row.get("amber_content") or ""
                    card_bytes = generate_share_card(
                        user_sentence=edited_text,
                        amber_sentence=amber_content,
                        username=user_id,
                        template= template
                    )
                    st.image(card_bytes)
                    st.download_button(
                        "⬇ 保存图片",
                        card_bytes,
                        file_name="soul_echo_share.png",
                        mime="image/png",
                        key=f"dl_{line_id}"
                    )

    st.markdown("""
<div style="margin:32px 0 12px 0;">
    <p style="font-size:13px; letter-spacing:4px; color:#888888; margin:0;">我的琥珀</p>
    <hr style="border:0; border-top:1px solid rgba(0,0,0,0.06); margin:8px 0 0 0;">
</div>
""", unsafe_allow_html=True)

    amber_label = "我的琥珀" if not st.session_state.show_my_ambers else "我的琥珀 ▲"
    if st.button(amber_label, key="toggle_my_ambers"):
        st.session_state.show_my_ambers = not st.session_state.show_my_ambers
        st.rerun()

    if st.session_state.show_my_ambers:
        # 获取用户的所有琥珀，包括收到的信件数
        client = get_db()
        
        # 获取用户的所有琥珀
        ambers_result = client.table("ambers").select("id, content, created_at, weight, author_id").eq("author_id", user_id).order("created_at", desc=True).execute()
        rows = ambers_result.data
        
        # 获取每个琥珀的消息数量
        if rows:
            amber_ids = [row["id"] for row in rows]
            messages_result = client.table("messages").select("amber_id").in_("amber_id", amber_ids).eq("receiver_id", user_id).execute()
            
            # 创建消息计数字典
            message_counts = {}
            for msg in messages_result.data:
                amber_id = msg["amber_id"]
                if amber_id in message_counts:
                    message_counts[amber_id] += 1
                else:
                    message_counts[amber_id] = 1
            
            # 将消息计数添加到琥珀数据中
            for row in rows:
                row["message_count"] = message_counts.get(row["id"], 0)
        else:
            rows = []
        
        if not rows:
            st.markdown("<p style='text-align:center; color:#94a3b8; font-size:14px;'>你还没有留下过琥珀。</p>",
                unsafe_allow_html=True)
        else:
            for row in rows:
                amber_id = row["id"]
                content = row["content"]
                created_at = row["created_at"]
                weight = row["weight"]
                message_count = row["message_count"]
                
                st.markdown(f"""
                <div style="padding:24px; margin-bottom:16px; border-radius:4px; background:rgba(0,0,0,0.03); border:none; box-shadow: 0 4px 20px rgba(0,0,0,0.03);">
                    <p style="color:#2D2D2D; font-size:14px; line-height:1.85; margin:0 0 12px 0;">{content}</p>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div style="color:#888888; font-size:12px;">
                            {created_at} · 信件: {message_count}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 删除按钮
                if st.button(f"删除", key=f"delete_{amber_id}"):
                    # 使用事务删除相关记录
                    client = get_db()
                    try:
                        # 删除相关的消息
                        client.table("messages").delete().eq("amber_id", amber_id).execute()
                        # 删除相关的停留记录
                        client.table("user_affinity").delete().eq("amber_id", amber_id).execute()
                        # 删除相关的每日上传记录
                        client.table("daily_uploads").delete().eq("amber_id", amber_id).execute()
                        # 删除琥珀本身
                        client.table("ambers").delete().eq("id", amber_id).execute()
                        st.toast("琥珀已删除", icon="🗑️")
                        # 重新加载页面
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败: {e}")

# ─── write_post 模式 ─────────────────────────────────────

elif st.session_state.mode == "write_post":
    user_id = st.session_state.username
    if st.button("← 返回", key="back_from_post"):
        st.session_state.mode = "gallery"
        st.rerun()

    st.markdown("""
    <div style="text-align:center; padding:48px 0 24px 0;">
        <h1 style="font-size:26px; font-weight:300; letter-spacing:8px;
                   color:#1a1a1a; margin:0;">帖</h1>
    </div>
    """, unsafe_allow_html=True)

    user_points = get_user_points(user_id)
    st.markdown(f"""
    <div style="max-width:500px; margin:0 auto 24px auto; text-align:center;">
        <p style="color:#888888; font-size:13px; margin:0; line-height:1.8;">
            写下此刻想说的话，随机落到一个陌生人的信箱。消耗30积分。三天内无人回复，退还15积分。
            当前积分：{user_points}
        </p>
    </div>
    """, unsafe_allow_html=True)

    if user_points < 30:
        st.markdown(
            "<p style='text-align:center; color:#94a3b8; font-size:13px;'>积分不足，无法发送帖。</p>",
            unsafe_allow_html=True)
    else:
        with st.form("post_form", clear_on_submit=True):
            post_text = st.text_area("", placeholder="此刻最想让某个陌生人听到的话……（最多100字）",
                height=120, max_chars=100, label_visibility="collapsed")
            if st.form_submit_button("放它漂走") and post_text.strip():
                ok, msg = send_post(user_id, post_text.strip())
                if ok:
                    st.toast("帖已寄出 🕊️")
                    st.session_state.mode = "gallery"
                    st.rerun()
                else:
                    st.warning(msg)

# ─── AI 回复生成 ──────────────────────────────────────

if st.session_state.last_user_prompt:
    user_input = st.session_state.last_user_prompt

    is_parrot = False
    if st.session_state.messages:
        first_msg = st.session_state.messages[0]["content"]
        if len(user_input.strip()) > 10 and user_input.strip() in first_msg:
            is_parrot = True
            parrot_reply = "这是别人留下的碎片。比起这块已经凝固的琥珀，我更想听听，它唤醒了你记忆里的哪个具体画面？"
            with st.chat_message("assistant"):
                st.markdown(parrot_reply)
            st.session_state.messages.append({"role": "assistant", "content": parrot_reply})
            st.session_state.last_user_prompt = None

    if not is_parrot:
        with st.chat_message("assistant"):
            client = OpenAI(
                api_key=st.secrets["siliconflow"]["api_key"],
                base_url="https://api.siliconflow.cn/v1",
                timeout=60.0,
            )
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
                if m["role"] in ("user", "assistant")
            ]

            # 注入用户记忆
            memories = get_user_memories(st.session_state.username)
            soul_prompt = load_prompt("core/soul_observer.md").replace("{memories}", memories)

            stream = client.chat.completions.create(
                model=MASTER_MODEL,
                messages=[
                    {"role": "system", "content": soul_prompt},
                    *history,
                ],
                stream=True
            )
            response_content = st.write_stream(stream)
            st.session_state.messages.append(
                {"role": "assistant", "content": response_content}
            )

            # 每隔5轮对话，异步更新一次用户记忆
            turn_count = sum(1 for m in st.session_state.messages if m["role"] == "user")
            if turn_count > 0 and turn_count % 5 == 0:
                threading.Thread(target=_update_memories_from_conversation, args=(st.session_state.username, st.session_state.messages.copy()), daemon=True).start()

    st.session_state.last_user_prompt = None
