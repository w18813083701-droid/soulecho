import random
import os
import time
from supabase import create_client, Client
from datetime import date
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
    initial_sidebar_state="auto",
    menu_items=None  # 隐藏菜单
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stApp {
        background-color: #f4efe6;
    }

    .block-container {
        max-width: 600px !important;
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
    }

    .stButton > button {
        background: transparent;
        border: 1px solid rgba(0,0,0,0.15);
        color: #2d2d2d;
        border-radius: 6px;
        font-size: 13px;
        letter-spacing: 0.5px;
        padding: 6px 16px;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background: rgba(0,0,0,0.04);
        border-color: rgba(0,0,0,0.3);
    }

    .stChatMessage {
        background: transparent !important;
        border: none !important;
        padding: 8px 0 !important;
    }
    .stChatMessage p {
        font-size: 15px;
        line-height: 1.9;
        color: #1a1a1a;
        letter-spacing: 0.02em;
    }

    .stTextArea textarea, .stTextInput input {
        background: rgba(255,255,255,0.55) !important;
        border: 1px solid rgba(0,0,0,0.12) !important;
        border-radius: 8px !important;
        font-size: 14px;
        color: #1a1a1a;
    }

    .stChatFloatingInputContainer {
        background: rgba(244,239,230,0.96) !important;
        border-top: 1px solid rgba(0,0,0,0.06) !important;
        padding-bottom: 16px;
    }

    .stTabs [data-baseweb="tab"] {
        font-size: 13px;
        color: #64748b;
        letter-spacing: 0.5px;
    }
    .stTabs [aria-selected="true"] {
        color: #1a1a1a !important;
        border-bottom: 1px solid #1a1a1a !important;
        background: transparent !important;
    }

    [data-testid="stSidebar"] {
        background: #ede8df !important;
    }

    .amber-bubble {
        cursor: pointer;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        display: inline-block;
    }
    .amber-bubble:hover {
        transform: scale(1.02) rotate(0deg) !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }

    /* 把特定key的按钮变成卡片样式 */
    [data-testid="stButton"] button[kind="secondary"].amber-card-btn {
        width: 100%;
        text-align: left;
        white-space: normal;
        height: auto;
        padding: 20px 22px;
        border-radius: 14px;
        background: linear-gradient(135deg, rgba(210,180,140,0.18), rgba(255,248,235,0.55));
        border: 1px solid rgba(180,150,100,0.2);
        box-shadow: 2px 3px 12px rgba(0,0,0,0.05);
        font-size: 14px;
        line-height: 1.85;
        color: #2d2d2d;
        cursor: pointer;
    }

    /* 禁用过渡动画 */
    .element-container {
        animation: none !important;
        transition: none !important;
    }
    .stApp > header {
        transition: none !important;
    }

    /* 强制覆盖 Streamlit 运行时的页面发灰和动画 */
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    .stApp {
        transition: none !important;
        opacity: 1 !important;
        animation: none !important;
    }
    /* 隐藏右上角的 running 状态小人/标识 */
    [data-testid="stStatusWidget"] {
        visibility: hidden;
    }

    /* 隐藏所有可能的加载指示器 */
    div[data-testid="stStatusWidget"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"] {
        display: none !important;
    }

    /* 禁止任何元素产生过渡动画 */
    * {
        transition: none !important;
        animation: none !important;
        transform: none !important;
    }

    /* 禁用所有可能的动画类 */
    .animated, .fade-in, .fade-out, .slide-in, .slide-out {
        animation: none !important;
        transition: none !important;
    }

    /* 手机端强制显示侧边栏 */
    @media (max-width: 640px) {
        /* 让侧边栏始终可见，不隐藏 */
        [data-testid="stSidebar"] {
            position: relative !important;
            width: 200px !important;
            margin-left: 0 !important;
            transform: none !important;
            visibility: visible !important;
            display: block !important;
        }
        /* 调整主内容区域，避免被侧边栏覆盖 */
        .main .block-container {
            margin-left: 200px !important;
            padding-left: 1rem !important;
            max-width: calc(100% - 200px) !important;
        }
        /* 隐藏Streamlit默认的汉堡菜单按钮 */
        button[kind="headerNoPadding"] {
            display: none !important;
        }
    }
</style>""", unsafe_allow_html=True)

# ─── 数据库 ───────────────────────────────────────────

DB_PATH = "soul_echo.db"

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
        import json
        raw = result.choices[0].message.content.strip()
        data = json.loads(raw)
        for item in data.get("memories", []):
            save_memory(user_id, item["key"], item["content"])
    except Exception:
        pass  # 记忆更新失败不影响主流程

def init_db():
    client = get_db()
    
    # 检查 ambers 表是否有数据
    result = client.table("ambers").select("id", count="exact").execute()
    existing = result.count
    if existing == 0:
        seeds = [
            "我以前很想让别人注意到我变漂亮了，但是当自己穿着好看的衣服出门又感觉所有人都在注视着我、审判我。我为了自己心里能安静点，之后出门都戴起了口罩、穿上了最丑的衣服。",
            "我们所有人谁不是小孩藏在大人衣服里呢？我时常感觉外界在朝衣服里灌风，我的身体在硬抗。最开始，我还有可以脱下大人衣服的场合和人，可是到了后来，我却一个都找不到了。",
            "我总是熬夜，我不知道为什么。我一遍又一遍地刷着什么，好像在渴望遇到一个答案，可是我甚至都不知道自己在寻找的是什么。没有找到就不愿睡去，直到精疲力尽才无力地倒在枕头上，第二天又像木偶一样重复。",
            "我的人生总需要喜欢着某个人才会觉得这个世界不至于太荒芜。尽管我潜意识知道喜欢的人不太可能真的喜欢我，但似乎这种爱而不得的状态才让我有活着的实感。",
            "我听到同龄人过得不好，心里却感觉到一阵轻松。可是转头一想，我究竟怎么会变成这样？这个时代，怎么把我变成这样的人了？",
            "明明看不惯那些溜须拍马的人，但看着他们风生水起，心里还是会一阵刺痛。我最终发现，我不是学不会逢场作戏，我只是宁愿抱着这块又冷又硬的石头沉下去，也不想允许自己沾上一丁点那种令人作呕的腥味。",
            "我的口袋里留着公交卡和几张零钱，以防手机没电。我还喜欢散步，喜欢深度交流，喜欢逛菜市场，喜欢早睡早起。——只是现在的年轻人里，确实没几个我这样的了。",
            "一场瓢泼大雨落下，我却在彻夜间长大。后来我成为一个不再会让自己轻易着凉的合格的大人，可我却失去了做回天真的孩子的自由。",
            "我很想念我的妈妈，而她正在服侍快要离开这个世界的外婆。当死亡的阴影和生之羁绊同时挤进胸腔，我发现自己穷尽一生，也无法把存在的意义想得更明晰。",
            "经常被无意义感侵扰，觉得一切都很暗淡，但我依然不厌其烦地把自己填进各项事务里。真正的困难只剩下存在主义虚无了，世俗的标准早就困不住我。在这个层面上，我是被选中的，也是受诅咒的。",
            "总觉得我不属于当下的生活，像是一直活在他处。眼前的日常变成了一个硬壳，死死束缚着生长的方向。但我偶尔也会恐惧：如果真的敲碎它，所谓的真正的生活，真的存在吗？",
            "孤独已经是老朋友了，我早就学会了在自己的精神隔间里安然无恙。但偶尔在街上看到他人相拥，还是会被突然击中。我这双手……到底有多久没有触碰过另一个人的体温了？",
            "真正的轻松永远只能来自内在的自洽。那些所谓对自我审视的放弃，总会在某个毫无防备的夜里，像一根倒刺般突然扎进心里。毕竟，潜意识从不撒谎。",
            "我总是习惯钻进潜意识的怀抱里自我抱持，以为那就是最安全的堡垒。可是当真的渴望一双现实的手伸过来时，第一反应却总是刺耳的警报。这种对亲密极度渴望又极度恐惧的拉扯，我往往分不清究竟是在保护自己，还是在囚禁自己。",
            "当我回忆起她，怀念和怨恨是同时来的。感激她的岁月，也恨她把我当过时尚单品。有的东西，果然只能局限在纸上。",
            "我一直都很自信，未来的我会更自信一点吗？",
            "今天看一本书看哭了，忽然明白自己原来一直都有心理问题。但我不甘心。我不想就这么认命，被童年控制一生。",
            "我其实情感特别充沛，但这又是一个与他人如此遥远的时代。我渴望与他人心贴心畅谈，但似乎每个人都有自己的世界，而我的敏感和泛滥总像个笑话。",
            "我们还是不要做朋友了，我很悲伤我们始终还是不合适。不过我们还是度过了很美好的四年。你的婚礼我不必出现，而我的人生后半程也不需要你的参与了，祝你仍然有美满的人生。",
            "当她对我说：'没事呢，我在这呢！有什么话和我说。'结果电话那头的我，哭得更凶了。",
        ]
        for content in seeds:
            client.table("ambers").insert({
                "content": content,
                "author_id": "rim",
                "author_name": "rim",
                "is_anonymous": 0
            }).execute()

init_db()

# ─── 工具函数 ─────────────────────────────────────────

def get_ambers_for_wall(user_id, limit=12):
    client = get_db()
    
    # 获取所有琥珀
    ambers_result = client.table("ambers").select("id, content, author_id, author_name, is_anonymous, weight").execute()
    ambers = ambers_result.data
    
    # 获取用户的停留时间
    affinity_result = client.table("user_affinity").select("amber_id, dwell_seconds").eq("user_id", user_id).execute()
    affinity_dict = {item["amber_id"]: item["dwell_seconds"] for item in affinity_result.data}
    
    # 计算排序分数并排序
    for amber in ambers:
        dwell_seconds = affinity_dict.get(amber["id"], 0)
        amber["affinity"] = dwell_seconds
        amber["score"] = amber["weight"] + dwell_seconds * 0.1 + random.random() * 0.5
    
    ambers.sort(key=lambda x: x["score"], reverse=True)
    
    return ambers[:limit]

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

def check_daily_upload(user_id):
    if user_id == "rim":
        return False
    client = get_db()
    today = date.today().isoformat()
    result = client.table("daily_uploads").select("id").eq("user_id", user_id).eq("upload_date", today).execute()
    return len(result.data) > 0

def _open_amber(amber_id, content, author_id, ambers, user_id):
    dwell = time.time() - st.session_state.get("wall_start_time", time.time())
    record_dwell(user_id, amber_id, min(dwell, 120))
    st.session_state.mode = "amber_detail"
    st.session_state.current_amber_id = amber_id
    st.session_state.current_amber_content = content
    st.session_state.current_amber_author = author_id
    st.session_state.wall_ambers = [dict(r) for r in ambers]
    st.session_state.wall_amber_index = [r["id"] for r in ambers].index(amber_id)
    st.session_state.messages = []
    st.session_state.opening_initialized = False

def submit_amber(user_id, content, author_name, is_anonymous):
    client = get_db()
    today = date.today().isoformat()
    try:
        # 插入琥珀
        amber_result = client.table("ambers").insert({
            "content": content,
            "author_id": user_id,
            "author_name": author_name,
            "is_anonymous": 1 if is_anonymous else 0
        }).execute()
        amber_id = amber_result.data[0]["id"]
        
        # 插入每日上传记录
        client.table("daily_uploads").insert({
            "user_id": user_id,
            "upload_date": today,
            "amber_id": amber_id
        }).execute()
        
        # 上传成功后重新加载琥珀列表
        st.session_state.all_ambers = get_ambers_for_wall(user_id, limit=50)
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

def get_inbox(user_id):
    client = get_db()
    
    # 获取用户收到的所有消息
    messages_result = client.table("messages").select("id, content, created_at, is_read, amber_id").eq("receiver_id", user_id).order("created_at", desc=True).execute()
    messages = messages_result.data
    
    # 获取相关的琥珀内容
    amber_ids = [msg["amber_id"] for msg in messages]
    if amber_ids:
        ambers_result = client.table("ambers").select("id, content").in_("id", amber_ids).execute()
        amber_dict = {item["id"]: item["content"] for item in ambers_result.data}
        
        # 将琥珀内容添加到消息中
        for msg in messages:
            msg["amber_content"] = amber_dict.get(msg["amber_id"], "")
    
    return messages

def mark_read(message_id):
    client = get_db()
    client.table("messages").update({"is_read": 1}).eq("id", message_id).execute()

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

def get_daily_question():
    today = date.today().isoformat()
    client = get_db()
    result = client.table("daily_questions").select("question").eq("question_date", today).execute()
    if result.data:
        return result.data[0]["question"]
    try:
        client = OpenAI(
            api_key=st.secrets["siliconflow"]["api_key"],
            base_url=" `https://api.siliconflow.cn/v1` ",
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
        conn2 = get_db()
        conn2.execute(
            "INSERT OR IGNORE INTO daily_questions (question_date, question) VALUES (?,?)",
            (today, question)
        )
        conn2.commit()
        conn2.close()
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

if "wall_refresh_count" not in st.session_state:
    st.session_state.wall_refresh_count = 0
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

# ─── 登录/注册逻辑 ────────────────────────────────────

if "username" not in st.session_state:
    st.session_state.username = None

if st.session_state.username is None:
    st.markdown("""
    <div style="text-align:center; padding:60px 20px;">
        <h1 style="font-size:28px; font-weight:300; letter-spacing:8px;
                   color:#1a1a1a; margin:0 0 40px 0;">Soul Echo</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # 添加水平切换组件
    auth_mode = st.radio("", ["登录", "注册"], horizontal=True, label_visibility="collapsed")
    
    # 为禁用自动填充生成随机后缀
    if "auth_key_suffix" not in st.session_state:
        st.session_state.auth_key_suffix = str(random.randint(1000, 9999))
    key_suffix = st.session_state.auth_key_suffix
    
    # 根据选择显示不同表单
    if auth_mode == "登录":
        st.subheader("登录")
        login_username = st.text_input("昵称", key=f"login_username_{key_suffix}")
        login_password = st.text_input("密码", type="password", key=f"login_password_{key_suffix}")
        if st.button("登录", key="btn_login"):
            if login_username and login_password:
                # 清理用户名：去除前后空格并转为小写
                cleaned_username = login_username.strip().lower()
                client = get_db()
                result = client.table("users").select("*").eq("username", cleaned_username).eq("password", login_password).execute()
                user = result.data[0] if result.data else None
                if user:
                    st.session_state.username = user["username"]
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
                # 清理用户名：去除前后空格并转为小写
                cleaned_username = reg_username.strip().lower()
                client = get_db()
                try:
                    client.table("users").insert({
                        "username": cleaned_username,
                        "password": reg_password
                    }).execute()
                    st.session_state.username = cleaned_username
                    st.success("注册成功！")
                    st.rerun()
                except Exception:
                    st.error("这个昵称已经被使用了")
            else:
                st.warning("请输入昵称和密码")
    
    st.stop()

# 预热提示词缓存，避免进入聊天时出现 Running 提示
if "prompts_warmed" not in st.session_state:
    load_prompt("opening/amber.md")
    load_prompt("opening/direct_vent.md")
    load_prompt("opening/wall_refresh.md")
    load_prompt("system/daily_question.md")
    load_prompt("core/soul_observer.md")
    st.session_state.prompts_warmed = True

# ─── 侧边栏 ──────────────────────────────────────────

with st.sidebar:
    user_id = st.session_state.username
    if st.session_state.mode in ["chat", "amber_detail", "inbox"]:
        if st.button("← 首页", key="back_home"):
            st.session_state.mode = "gallery"
            st.session_state.messages = []
            st.session_state.entry_path = None
            st.session_state.opening_initialized = False
            st.session_state.from_amber_redirect = False
            st.rerun()
    # 使用缓存的未读消息数量，避免重复查询
    if "unread_count" not in st.session_state or st.session_state.get("last_unread_check") != user_id:
        st.session_state.unread_count = get_unread_count(user_id)
        st.session_state.last_unread_check = user_id
    unread = st.session_state.unread_count
    
    inbox_label = f"收件箱  {unread} 条未读" if unread > 0 else "收件箱"
    if st.button(inbox_label, key="open_inbox"):
        st.session_state.mode = "inbox"
        st.rerun()
    
    if st.button("我的琥珀", key="my_ambers"):
        st.session_state.mode = "my_ambers"
        st.rerun()
    
# ─── gallery 模式 ─────────────────────────────────────

if st.session_state.mode == "gallery":
    user_id = st.session_state.username

    # 缓存未读消息数量，避免重复查询
    if "unread_count" not in st.session_state or st.session_state.get("last_unread_check") != user_id:
        st.session_state.unread_count = get_unread_count(user_id)
        st.session_state.last_unread_check = user_id
    unread = st.session_state.unread_count
    
    # 标题和收件箱按钮布局
    col_title, col_inbox = st.columns([3, 1])
    with col_title:
        st.markdown("""
        <div style="padding:48px 0 24px 0;">
            <h1 style="font-size:26px; font-weight:300; letter-spacing:8px;
                       color:#1a1a1a; margin:0;">Soul Echo</h1>
        </div>
        """, unsafe_allow_html=True)
    with col_inbox:
        inbox_label = f"收件箱 📬 ({unread})" if unread > 0 else "收件箱 📬"
        if st.button(inbox_label, key="main_inbox_button"):
            st.session_state.mode = "inbox"
            st.rerun()

    daily_q = get_daily_question()
    already_uploaded = check_daily_upload(user_id)

    st.markdown(f"""
    <div style="max-width:500px; margin:0 auto 24px auto; padding:8px 0; text-align:center;">
        <p style="color:#b4a48a; font-size:13px; margin:0; letter-spacing:0.5px;">{daily_q}</p>
    </div>
    """, unsafe_allow_html=True)

    if already_uploaded:
        st.markdown(
            "<p style='text-align:center; color:#94a3b8; font-size:13px;'>"
            "今天的琥珀已经留下了。</p>", unsafe_allow_html=True)
    else:
        col_w, col_s = st.columns([2, 3])
        with col_w:
            if st.button("写今天的琥珀", key="open_upload"):
                st.session_state.mode = "write_amber"
                st.rerun()

    # 隐藏入口：刷够次数就在视线范围内出现
    wall_refresh = st.session_state.get("wall_refresh_count", 0)
    if wall_refresh >= 10:
        st.markdown(
            "<p style='text-align:center; color:#94a3b8; font-size:13px; margin-top:24px;'>"
            "也许此刻，你自己有更想说的话。</p>", unsafe_allow_html=True)
        if st.button("直接说出来", key="hidden_vent"):
            st.session_state.mode = "chat"
            st.session_state.entry_path = "direct_vent"
            st.session_state.messages = []
            st.session_state.opening_initialized = False
            st.session_state.from_amber_redirect = True
            st.rerun()

    st.markdown(
        "<hr style='border:0; border-top:1px solid rgba(0,0,0,0.06); margin:16px 0 28px 0;'>",
        unsafe_allow_html=True)

    # 初始化或获取琥珀列表
    if "all_ambers" not in st.session_state:
        # 第一次加载时从数据库获取较多琥珀
        st.session_state.all_ambers = get_ambers_for_wall(user_id, limit=50)
    
    # 从缓存的琥珀中随机挑选4个
    import random
    if st.session_state.all_ambers:
        ambers = random.sample(st.session_state.all_ambers, min(4, len(st.session_state.all_ambers)))
    else:
        ambers = []
    
    if "wall_start_time" not in st.session_state:
        st.session_state.wall_start_time = time.time()

    if not ambers:
        st.markdown("<p style='text-align:center; color:#94a3b8;'>墙上还没有琥珀。</p>",
            unsafe_allow_html=True)
    else:
        # 定义四块的宽度比和margin-top，打破对称
        layouts = [
            {"col": 0, "margin_top": "0px",  "rot": -1.5},
            {"col": 1, "margin_top": "32px", "rot": 1.0},
            {"col": 0, "margin_top": "16px", "rot": 1.8},
            {"col": 1, "margin_top": "-8px", "rot": -0.8},
        ]
        col_left, col_right = st.columns([1.05, 0.95])
        cols = [col_left, col_right]

        for i, row in enumerate(ambers[:4]):
            amber_id = row["id"]
            content = row["content"]
            # 根据 is_anonymous 判断显示名称
            if row["is_anonymous"] == 1:
                display_name = "匿名"
            elif row["author_id"] == st.session_state.username:
                display_name = st.session_state.username
            else:
                display_name = row["author_name"] or "匿名"
            
            # 悬念截断：找第一个标点停顿截断，最多25字
            import re
            match = re.search(r'[，。！？、；]', content[12:28])
            if match:
                cut = 12 + match.start() + 1
                preview = content[:cut] + "……"
            else:
                preview = content[:20] + "……"
            
            lay = layouts[i]
            
            # weight阈值决定皮肤
            weight = row.get("weight", 1.0) if hasattr(row, "get") else dict(row).get("weight", 1.0)
            if weight > 2.0:
                bg = "linear-gradient(135deg, rgba(210,170,90,0.22), rgba(255,240,200,0.6))"
                border = "1px solid rgba(180,140,60,0.3)"
            else:
                bg = "linear-gradient(135deg, rgba(210,180,140,0.15), rgba(255,248,235,0.5))"
                border = "1px solid rgba(180,150,100,0.18)"
            
            with cols[lay["col"]]:
                st.markdown(f"""
                <div style="margin-top:{lay['margin_top']}; margin-bottom:20px; 
                            padding:20px 22px; border-radius:14px; 
                            background:{bg}; border:{border}; 
                            transform:rotate({lay['rot']}deg); 
                            box-shadow:2px 3px 12px rgba(0,0,0,0.05);">
                    <p style="color:#2d2d2d; font-size:14px; line-height:1.85; margin:0 0 10px 0; text-align:center;">{preview}</p>
                    <p style="color:#b4a48a; font-size:12px; margin:0; text-align:right;">— {display_name}</p>
                </div>
                """, unsafe_allow_html=True)
                st.button("打开", key=f"open_{amber_id}",
                          on_click=lambda aid=amber_id, c=content, rid=row["author_id"]:
                              _open_amber(aid, c, rid, ambers, user_id))

    # 刷新按钮放中间
    wall_refresh = st.session_state.get("wall_refresh_count", 0)
    st.markdown("<div style='text-align:center; margin-top:24px;'>", unsafe_allow_html=True)
    if st.button("↺  换几块", key="refresh_wall"):
        st.session_state.wall_refresh_count = wall_refresh + 1
        st.session_state.wall_start_time = time.time()
        # 重新随机挑选琥珀，无需重新查询数据库
        import random
        if st.session_state.all_ambers:
            st.session_state.wall_ambers = random.sample(st.session_state.all_ambers, min(4, len(st.session_state.all_ambers)))
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
            record_dwell(user_id, amber_id, min(dwell, 300))
            st.session_state.mode = "gallery"
            st.rerun()
    with col_next:
        if len(wall_ambers) > 1 and st.button("下一块 →"):
            dwell = time.time() - st.session_state.get("amber_open_time", time.time())
            record_dwell(user_id, amber_id, min(dwell, 300))
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
                padding:16px 32px; border-radius:14px;
                background:rgba(0,0,0,0.03);
                border:1px solid rgba(0,0,0,0.07);">
        <p style="color:#1a1a1a; font-size:16px; line-height:1.9; margin:0;">
            {content}
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_chat, tab_letter = st.tabs(["和AI聊这块琥珀", "给ta写封信"])

    with tab_chat:
        if not st.session_state.opening_initialized:
            st.session_state.opening_initialized = True
            client_init = OpenAI(
                api_key=st.secrets["siliconflow"]["api_key"],
                base_url="https://api.siliconflow.cn/v1",
                timeout=60.0,
            )
            with st.chat_message("assistant"):
                stream = client_init.chat.completions.create(
                    model=FAST_OPENING_MODEL,  # 使用快速模型生成开场白
                    messages=[
                        {"role": "system", "content": load_prompt("opening/amber.md")},
                        {"role": "user", "content": f"琥珀文本：{content}"}
                    ],
                    stream=True
                )
                opening_text = st.write_stream(stream)
            st.session_state.initial_assistant_message = opening_text

        for msg in st.session_state.messages:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        
        # 添加空白占位，防止输入框遮挡聊天内容
        st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)

        if prompt := st.chat_input("说说这块琥珀让你想到了什么…"):
            if st.session_state.get("initial_assistant_message"):
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": st.session_state.initial_assistant_message
                })
                st.session_state.initial_assistant_message = None
            st.session_state.messages.append({"role": "user", "content": prompt})
            # 交互次数更新weight
            if st.session_state.mode == "amber_detail" and st.session_state.get("current_amber_id"):
                client = get_db()
                client.table("ambers").update({"weight": st.session_state.current_amber_weight + 0.1}).eq("id", st.session_state.current_amber_id).execute()
            st.session_state.last_user_prompt = prompt
            st.rerun()

    with tab_letter:
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
                submit_button = st.form_submit_button("寄出去")
                if submit_button:
                    if letter.strip():
                        send_message(amber_id, user_id, author_id, letter.strip())
                        st.toast("信件已稳妥寄出", icon="🕊️")
                    else:
                        st.warning("还没写什么内容。")

# ─── inbox 模式 ───────────────────────────────────────

elif st.session_state.mode == "inbox":
    user_id = st.session_state.username
    if st.button("← 返回"):
        st.session_state.mode = "gallery"
        st.rerun()

    st.markdown(
        "<h3 style='font-weight:300; letter-spacing:3px; margin-bottom:24px;'>收件箱</h3>",
        unsafe_allow_html=True)

    letters = get_inbox(user_id)
    if not letters:
        st.markdown("<p style='color:#94a3b8; font-size:14px;'>还没有人给你写信。</p>",
            unsafe_allow_html=True)
    else:
        for letter in letters:
            mark_read(letter["id"])
            amber_preview = letter["amber_content"][:40] + "……" \
                if len(letter["amber_content"]) > 40 else letter["amber_content"]
            st.markdown(f"""
            <div style="padding:18px 22px; margin-bottom:14px; border-radius:10px;
                        background:rgba(0,0,0,0.02); border:1px solid rgba(0,0,0,0.06);">
                <p style="color:#94a3b8; font-size:12px; margin:0 0 8px 0;">
                    关于：{amber_preview}
                </p>
                <p style="color:#1a1a1a; font-size:15px; line-height:1.8; margin:0;">
                    {letter["content"]}
                </p>
                <p style="color:#94a3b8; font-size:11px; margin:8px 0 0 0;">
                    {str(letter["created_at"])[:10]}
                </p>
            </div>
            """, unsafe_allow_html=True)

# ─── chat 模式（direct_vent）────────────────────────────

elif st.session_state.mode == "chat":
    st.markdown(
        "<p style='text-align:center; color:#94a3b8; font-size:13px; "
        "padding:32px 0 16px 0; letter-spacing:1px;'>—</p>",
        unsafe_allow_html=True)

    if not st.session_state.opening_initialized:
        st.session_state.opening_initialized = True
        context_note = ""
        if st.session_state.get("from_amber_redirect"):
            context_note = "（用户在琥珀墙刷新多次没找到共鸣，主动转过来了）"
            st.session_state.from_amber_redirect = False
            opening_prompt = load_prompt("opening/wall_refresh.md")
        else:
            opening_prompt = load_prompt("opening/direct_vent.md")
        client_init = OpenAI(
            api_key=st.secrets["siliconflow"]["api_key"],
            base_url="https://api.siliconflow.cn/v1",
            timeout=60.0,
        )
        with st.chat_message("assistant"):
            stream = client_init.chat.completions.create(
                model=FAST_OPENING_MODEL,  # 使用快速模型生成开场白
                messages=[
                    {"role": "system", "content": opening_prompt},
                    {"role": "user", "content": f"用户刚刚进入对话，什么都还没说。{context_note}"}
                ],
                stream=True
            )
            opening_text = st.write_stream(stream)
        st.session_state.initial_assistant_message = opening_text

    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if prompt := st.chat_input("说点什么..."):
        if st.session_state.get("initial_assistant_message"):
            st.session_state.messages.append({
                "role": "assistant",
                "content": st.session_state.initial_assistant_message
            })
            st.session_state.initial_assistant_message = None
        st.session_state.messages.append({"role": "user", "content": prompt})
        # 每次用户发消息，给当前琥珀的weight +0.1
        if st.session_state.mode == "amber_detail":
            client = get_db()
            client.table("ambers").update({"weight": st.session_state.current_amber_weight + 0.1}).eq("id", st.session_state.current_amber_id).execute()
        st.session_state.last_user_prompt = prompt
        st.rerun()

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
    already_uploaded = check_daily_upload(user_id)

    st.markdown(f"""
    <div style="max-width:500px; margin:0 auto 24px auto; padding:8px 0; text-align:center;">
        <p style="color:#b4a48a; font-size:13px; margin:0; letter-spacing:0.5px;">{daily_q}</p>
    </div>
    """, unsafe_allow_html=True)

    if already_uploaded:
        st.markdown(
            "<p style='text-align:center; color:#94a3b8; font-size:13px;'>"
            "今天的琥珀已经留下了。</p>", unsafe_allow_html=True)
    else:
        with st.form("upload_form", clear_on_submit=True):
            st.markdown("""
            <div style="padding:12px 16px; margin-bottom:16px; border-radius:8px;
                        background:rgba(180,150,100,0.1); border-left:3px solid rgba(180,150,100,0.4);">
                <p style="color:#8a7055; font-size:13px; margin:0; line-height:1.6;">
                    今天只有一次机会。
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
                ok = submit_amber(user_id, amber_text.strip(), author_name, anon_choice == "匿名")
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
                   color:#1a1a1a; margin:0;">我的琥珀</h1>
    </div>
    """, unsafe_allow_html=True)
    
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
            <div style="padding:20px 22px; margin-bottom:16px; border-radius:14px;
                        background:rgba(210,180,140,0.15); border:1px solid rgba(180,150,100,0.18);
                        box-shadow:2px 3px 12px rgba(0,0,0,0.05);">
                <p style="color:#2d2d2d; font-size:14px; line-height:1.85; margin:0 0 12px 0;">{content}</p>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="color:#b4a48a; font-size:12px;">
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
                _update_memories_from_conversation(
                    st.session_state.username,
                    st.session_state.messages
                )

    st.session_state.last_user_prompt = None
